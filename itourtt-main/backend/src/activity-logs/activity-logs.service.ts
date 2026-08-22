import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';
import * as XLSX from 'xlsx';
import { PrismaService } from '../prisma/prisma.service.js';
import { QueryActivityLogDto } from './dto/query-activity-log.dto.js';
import {
  windowLabel,
  entityModel,
  humanizeField,
  formatValue,
  fieldModel,
  isUuid,
  isHiddenField,
  MODEL_DISPLAY,
} from './activity-log-format.js';

type Dict = Record<string, unknown>;

const RETENTION_DAYS = 90;

@Injectable()
export class ActivityLogsService {
  private readonly logger = new Logger(ActivityLogsService.name);

  constructor(private readonly prisma: PrismaService) {}

  /** Purge activity logs older than 90 days — runs every Sunday at 03:00 Cairo time */
  @Cron('0 3 * * 0', { timeZone: 'Africa/Cairo' })
  async purgeOldActivityLogs() {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - RETENTION_DAYS);
    const { count } = await this.prisma.activityLog.deleteMany({
      where: { createdAt: { lt: cutoff } },
    });
    if (count > 0) {
      this.logger.log(
        `Purged ${count} activity log entries older than ${RETENTION_DAYS} days`,
      );
    }
  }

  async findAll(query: QueryActivityLogDto) {
    const page = query.page ?? 1;
    const limit = query.limit ?? 20;
    const skip = (page - 1) * limit;

    const where: any = {};

    if (query.userId) {
      where.userId = query.userId;
    }
    if (query.entity) {
      where.entity = query.entity;
    }
    if (query.action) {
      where.action = query.action;
    }
    if (query.dateFrom || query.dateTo) {
      where.createdAt = {};
      if (query.dateFrom) {
        where.createdAt.gte = new Date(query.dateFrom);
      }
      if (query.dateTo) {
        const to = new Date(query.dateTo);
        to.setHours(23, 59, 59, 999);
        where.createdAt.lte = to;
      }
    }
    if (query.search) {
      where.summary = { contains: query.search, mode: 'insensitive' };
    }

    const [logs, total] = await Promise.all([
      this.prisma.activityLog.findMany({
        where,
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
        select: {
          id: true,
          userId: true,
          userName: true,
          action: true,
          entity: true,
          entityId: true,
          summary: true,
          ipAddress: true,
          createdAt: true,
          // Prefer the user's actual name over the stored email for display.
          user: { select: { name: true } },
        },
      }),
      this.prisma.activityLog.count({ where }),
    ]);

    return {
      data: logs.map(({ user, ...l }) => ({
        ...l,
        userName: user?.name || l.userName,
      })),
      meta: { total, page, limit, totalPages: Math.ceil(total / limit) },
    };
  }

  async findOne(id: string) {
    const log = await this.prisma.activityLog.findUnique({
      where: { id },
      include: { user: { select: { name: true } } },
    });
    if (!log) throw new NotFoundException('Activity log not found');

    const after = (log.details ?? null) as Dict | null;
    const before = (log.previousData ?? null) as Dict | null;

    // Resolve UUID references in either snapshot — plus the log's own record id
    // (e.g. a TrafficJob's internal ref) — to readable names.
    const recordModel = entityModel(log.entity);
    const extraRefs =
      recordModel && isUuid(log.entityId)
        ? [{ model: recordModel, id: log.entityId }]
        : [];
    const lookups = await this.resolveRefs([after, before], extraRefs);
    const fmt = (key: string, value: unknown) =>
      formatValue(key, value, lookups);

    const entityRef =
      recordModel && isUuid(log.entityId)
        ? lookups[`${recordModel}:${log.entityId}`]
        : undefined;

    let createdFields: { label: string; value: string }[] | undefined;
    let deletedFields: { label: string; value: string }[] | undefined;
    let changes:
      | { label: string; oldValue: string; newValue: string }[]
      | undefined;

    if (log.action === 'CREATE' && after) {
      createdFields = this.toFieldList(after, fmt);
    } else if (log.action === 'DELETE' && before) {
      deletedFields = this.toFieldList(before, fmt);
    } else if (log.action === 'UPDATE' && after) {
      // Diff submitted (new) values against the captured before-snapshot.
      changes = Object.entries(after)
        .filter(([key]) => !isHiddenField(key))
        .filter(([key, newVal]) => {
          const oldVal = before ? before[key] : undefined;
          return (
            JSON.stringify(oldVal ?? null) !== JSON.stringify(newVal ?? null)
          );
        })
        .map(([key, newVal]) => ({
          label: humanizeField(key),
          oldValue: before ? fmt(key, before[key]) : '—',
          newValue: fmt(key, newVal),
        }));
    }

    const { user, ...rest } = log;
    return {
      ...rest,
      userName: user?.name || log.userName,
      window: windowLabel(log.entity),
      entityRef,
      createdFields,
      deletedFields,
      changes,
    };
  }

  /** Turn a flat record into a list of {label, value}, skipping noise fields. */
  private toFieldList(obj: Dict, fmt: (k: string, v: unknown) => string) {
    return Object.entries(obj)
      .filter(([key]) => !isHiddenField(key))
      .map(([key, value]) => ({
        label: humanizeField(key),
        value: fmt(key, value),
      }));
  }

  /** Batch-resolve UUID-valued fields across the given snapshots into a
   *  `${model}:${uuid}` → display-name map. */
  private async resolveRefs(
    sources: (Dict | null)[],
    extra: { model: string; id: string }[] = [],
  ): Promise<Record<string, string>> {
    const idsByModel = new Map<string, Set<string>>();
    const add = (model: string, id: string) => {
      if (!idsByModel.has(model)) idsByModel.set(model, new Set());
      idsByModel.get(model)!.add(id);
    };
    for (const src of sources) {
      if (!src) continue;
      for (const [key, value] of Object.entries(src)) {
        const model = fieldModel(key);
        if (model && isUuid(value)) add(model, value);
      }
    }
    for (const { model, id } of extra) add(model, id);

    const lookups: Record<string, string> = {};
    await Promise.all(
      [...idsByModel.entries()].map(async ([model, ids]) => {
        const cfg = MODEL_DISPLAY[model];
        const delegate = (
          this.prisma as unknown as Record<
            string,
            { findMany?: (args: unknown) => Promise<unknown> } | undefined
          >
        )[model];
        if (!cfg || !delegate?.findMany) return;
        try {
          const rows = (await delegate.findMany({
            where: { id: { in: [...ids] } },
            select: { id: true, ...cfg.select },
          })) as Record<string, string | null | undefined>[];
          for (const row of rows) {
            if (row.id) lookups[`${model}:${row.id}`] = cfg.format(row);
          }
        } catch {
          // leave unresolved — formatValue falls back to the raw UUID
        }
      }),
    );
    return lookups;
  }

  async exportToExcel(query: QueryActivityLogDto): Promise<Buffer> {
    // Fetch all matching records (no pagination for export)
    const where: any = {};
    if (query.userId) where.userId = query.userId;
    if (query.entity) where.entity = query.entity;
    if (query.action) where.action = query.action;
    if (query.dateFrom || query.dateTo) {
      where.createdAt = {};
      if (query.dateFrom) where.createdAt.gte = new Date(query.dateFrom);
      if (query.dateTo) {
        const to = new Date(query.dateTo);
        to.setHours(23, 59, 59, 999);
        where.createdAt.lte = to;
      }
    }
    if (query.search) {
      where.summary = { contains: query.search, mode: 'insensitive' };
    }

    const logs = await this.prisma.activityLog.findMany({
      where,
      orderBy: { createdAt: 'desc' },
      take: 10000,
      include: { user: { select: { name: true } } },
    });

    const rows = logs.map((l) => ({
      'Date & Time': l.createdAt.toISOString().replace('T', ' ').slice(0, 19),
      User: l.user?.name || l.userName,
      Action: l.action,
      Window: windowLabel(l.entity),
      Record: l.entityId || '',
      Summary: l.summary,
      'IP Address': l.ipAddress || '',
    }));

    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Activity Log');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  /** Get distinct entity names for filter dropdown */
  async getDistinctEntities(): Promise<string[]> {
    const result = await this.prisma.activityLog.findMany({
      distinct: ['entity'],
      select: { entity: true },
      orderBy: { entity: 'asc' },
    });
    return result.map((r) => r.entity);
  }
}
