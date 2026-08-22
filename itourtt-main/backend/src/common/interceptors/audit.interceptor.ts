import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
  Logger,
} from '@nestjs/common';
import { Observable, from } from 'rxjs';
import { tap, switchMap } from 'rxjs/operators';
import { PrismaService } from '../../prisma/prisma.service.js';

/** Sensitive fields stripped from logged request bodies */
const SENSITIVE_KEYS = new Set([
  // Credentials / tokens
  'password',
  'passwordHash',
  'refreshToken',
  'accessToken',
  'token',
  'secret',
  'passwordResetToken',
  'twoFactorSecret',
  'twoFactorRecoveryCodes',
  // PII — kept out of the (exportable, 90-day) activity_logs table
  'taxId',
  'nationalId',
  'address',
  'phone',
  'mobile',
  'clientMobile',
  'phoneNumber',
  'whatsapp',
  'email',
  'iban',
  'bankName',
  'bankAccount',
  'accountNumber',
]);

/** Map URL segment → human-readable entity name */
const ENTITY_MAP: Record<string, string> = {
  users: 'User',
  agents: 'Agent',
  customers: 'Customer',
  suppliers: 'Supplier',
  drivers: 'Driver',
  reps: 'Rep',
  vehicles: 'Vehicle',
  locations: 'Location',
  'traffic-jobs': 'TrafficJob',
  dispatch: 'Dispatch',
  finance: 'Finance',
  invoices: 'Invoice',
  'job-locks': 'JobLock',
  permissions: 'Permission',
  settings: 'Settings',
  'vehicle-types': 'VehicleType',
  reports: 'Report',
  whatsapp: 'Whatsapp',
  'activity-logs': 'ActivityLog',
};

/** Map URL segment → Prisma model delegate, used to snapshot a record's state
 *  BEFORE an update/delete so the Activity Log can show an old → new diff. */
const MODEL_MAP: Record<string, string> = {
  users: 'user',
  agents: 'agent',
  customers: 'customer',
  suppliers: 'supplier',
  drivers: 'driver',
  reps: 'rep',
  vehicles: 'vehicle',
  'vehicle-types': 'vehicleType',
  'traffic-jobs': 'trafficJob',
  invoices: 'invoice',
};

/** UUID v4 regex */
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type AuditEntry = {
  userId: string;
  userName: string;
  action: string;
  entity: string;
  entityId: string | null;
  summary: string;
  details?: Record<string, unknown>;
  previousData?: Record<string, unknown>;
  ipAddress: string | null;
};

const FLUSH_INTERVAL_MS = 5_000;
const FLUSH_BATCH_SIZE = 200;

@Injectable()
export class AuditInterceptor implements NestInterceptor {
  private readonly logger = new Logger('AuditLog');
  private queue: AuditEntry[] = [];
  private flushTimer: NodeJS.Timeout | null = null;

  constructor(private readonly prisma: PrismaService) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const request = context.switchToHttp().getRequest();
    const { method, url, body, ip } = request;
    const user = request.user;

    if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      return next.handle();
    }

    // Skip auth endpoints (login, refresh) and activity-log reads
    const path = url.split('?')[0];
    if (path.includes('/auth/')) {
      return next.handle();
    }

    const userId = user?.id || user?.sub;
    const userName = user?.email || 'anonymous';

    // Unauthenticated requests are never logged — skip the before-snapshot too.
    if (!userId) return next.handle();

    // For updates/deletes, snapshot the record's current state BEFORE the
    // handler mutates it, so the log can render an old → new comparison.
    return from(this.captureBefore(method, path)).pipe(
      switchMap((before) =>
        next.handle().pipe(
          tap(() => {
            this.enqueue(method, path, userId, userName, body, ip, before);
          }),
        ),
      ),
    );
  }

  /** Fetch the existing record for an UPDATE/DELETE so we can diff old → new.
   *  Only runs for top-level mapped entities addressed by a UUID (not
   *  sub-resources, where the addressed id is the parent, not the target). */
  private async captureBefore(
    method: string,
    path: string,
  ): Promise<Record<string, unknown> | null> {
    if (method !== 'PUT' && method !== 'PATCH' && method !== 'DELETE')
      return null;

    const segments = path
      .replace(/^\/api\//, '')
      .split('/')
      .filter(Boolean);

    const model = MODEL_MAP[segments[0]];
    const id = segments[1];
    // Require a direct /<entity>/<uuid> target with no sub-resource.
    if (
      !model ||
      !id ||
      !UUID_RE.test(id) ||
      (segments[2] && !UUID_RE.test(segments[2]))
    ) {
      return null;
    }

    try {
      const delegate = (
        this.prisma as unknown as Record<
          string,
          { findUnique?: (args: unknown) => Promise<unknown> } | undefined
        >
      )[model];
      if (!delegate?.findUnique) return null;
      const record = await delegate.findUnique({ where: { id } });
      // Round-trip through JSON so Date/Decimal become plain serializable values.
      return record
        ? this.sanitizeBody(
            JSON.parse(JSON.stringify(record)) as Record<string, unknown>,
          )
        : null;
    } catch {
      return null;
    }
  }

  private enqueue(
    method: string,
    path: string,
    userId: string | undefined,
    userName: string,
    body: any,
    ip: string,
    before?: Record<string, unknown> | null,
  ) {
    if (!userId) return;

    const action = this.methodToAction(method);
    const { entity, entityId } = this.parseEntityFromPath(path);
    const summary = `${action} ${entity}${entityId ? ` (${entityId.slice(0, 8)}…)` : ''}`;
    const sanitized = this.sanitizeBody(body);

    this.queue.push({
      userId,
      userName,
      action,
      entity,
      entityId,
      summary,
      details:
        sanitized && Object.keys(sanitized).length > 0 ? sanitized : undefined,
      previousData:
        before && Object.keys(before).length > 0 ? before : undefined,
      ipAddress: ip || null,
    });

    // Flush immediately if batch is full
    if (this.queue.length >= FLUSH_BATCH_SIZE) {
      this.flush();
      return;
    }

    // Schedule a flush if not already scheduled
    if (!this.flushTimer) {
      this.flushTimer = setTimeout(() => this.flush(), FLUSH_INTERVAL_MS);
    }
  }

  private flush() {
    if (this.flushTimer) {
      clearTimeout(this.flushTimer);
      this.flushTimer = null;
    }
    if (this.queue.length === 0) return;

    const batch = this.queue.splice(0, FLUSH_BATCH_SIZE);
    this.prisma.activityLog
      .createMany({ data: batch as any })
      .catch((err) =>
        this.logger.warn(`Failed to flush audit logs: ${err.message}`),
      );
  }

  private methodToAction(method: string): string {
    switch (method) {
      case 'POST':
        return 'CREATE';
      case 'PUT':
      case 'PATCH':
        return 'UPDATE';
      case 'DELETE':
        return 'DELETE';
      default:
        return method;
    }
  }

  private parseEntityFromPath(path: string): {
    entity: string;
    entityId: string | null;
  } {
    // path: /api/agents/uuid or /api/agents/uuid/price-list
    const segments = path
      .replace(/^\/api\//, '')
      .split('/')
      .filter(Boolean);

    let entity = segments[0] || 'Unknown';
    let entityId: string | null = null;

    // Map first segment to friendly name
    entity = ENTITY_MAP[entity] || entity;

    // Look for UUID in second segment
    if (segments[1] && UUID_RE.test(segments[1])) {
      entityId = segments[1];
    }

    // If there's a sub-resource (e.g. /agents/uuid/price-list), append it
    if (segments[2] && !UUID_RE.test(segments[2])) {
      const subEntity = segments[2]
        .split('-')
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join('');
      entity = `${entity}.${subEntity}`;
    }

    return { entity, entityId };
  }

  private sanitizeBody(body: any): any {
    if (!body || typeof body !== 'object') return null;
    const clean: Record<string, any> = {};
    for (const [key, value] of Object.entries(body)) {
      if (SENSITIVE_KEYS.has(key)) {
        clean[key] = '***';
      } else {
        clean[key] = value;
      }
    }
    return clean;
  }
}
