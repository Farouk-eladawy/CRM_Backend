import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';

type LockTab = 'dispatcher' | 'driver' | 'rep' | 'supplier' | 'edit' | 'b2c' | 'online';

const PAGE_SIZE = 50;

@Injectable()
export class JobLocksService {
  constructor(private readonly prisma: PrismaService) {}

  async findJobs(
    tab: LockTab,
    dateFrom: string,
    dateTo: string,
    search?: string,
    page = 1,
    limit = PAGE_SIZE,
  ) {
    const from = new Date(dateFrom);
    const to = new Date(dateTo);
    const skip = (page - 1) * limit;

    const baseWhere: Record<string, unknown> = {
      jobDate: { gte: from, lte: to },
      deletedAt: null,
    };

    if (search) {
      baseWhere.internalRef = { contains: search, mode: 'insensitive' };
    }

    // Tab-specific filters
    if (tab === 'driver') {
      baseWhere.assignment = { is: { driverId: { not: null } } };
    } else if (tab === 'rep') {
      baseWhere.assignment = { is: { repId: { not: null } } };
    } else if (tab === 'supplier') {
      baseWhere.assignment = {
        is: { vehicle: { supplierId: { not: null } } },
      };
    } else if (tab === 'b2c') {
      baseWhere.bookingChannel = 'B2C';
    } else if (tab === 'online') {
      baseWhere.bookingChannel = 'ONLINE';
    }

    const select = {
      id: true,
      internalRef: true,
      jobDate: true,
      serviceType: true,
      status: true,
      clientName: true,
      dispatchUnlockedAt: true,
      driverUnlockedAt: true,
      repUnlockedAt: true,
      supplierUnlockedAt: true,
      editUnlockedAt: true,
      agent: { select: { legalName: true } },
      customer: { select: { legalName: true } },
      fromZone: { select: { name: true } },
      toZone: { select: { name: true } },
      assignment: {
        select: {
          driver: { select: { id: true, name: true } },
          rep: { select: { id: true, name: true } },
          vehicle: {
            select: {
              id: true,
              plateNumber: true,
              supplier: { select: { id: true, legalName: true } },
            },
          },
        },
      },
    };

    const [jobs, total] = await Promise.all([
      this.prisma.trafficJob.findMany({
        where: baseWhere,
        orderBy: { jobDate: 'desc' },
        skip,
        take: limit,
        select,
      }),
      this.prisma.trafficJob.count({ where: baseWhere }),
    ]);

    const unlockField = this.getUnlockField(tab);
    const data = jobs.map((job) => ({
      ...job,
      isUnlocked: !!(job as any)[unlockField],
    }));

    return { data, total, page, limit };
  }

  async unlockJob(tab: LockTab, jobId: string, userId: string) {
    const job = await this.prisma.trafficJob.findFirst({
      where: { id: jobId, deletedAt: null },
    });
    if (!job) throw new NotFoundException(`Traffic job with ID "${jobId}" not found`);

    const data = this.getUnlockData(tab, userId);
    return this.prisma.trafficJob.update({
      where: { id: jobId },
      data,
      select: { id: true, internalRef: true },
    });
  }

  async lockJob(tab: LockTab, jobId: string) {
    const job = await this.prisma.trafficJob.findFirst({
      where: { id: jobId, deletedAt: null },
    });
    if (!job) throw new NotFoundException(`Traffic job with ID "${jobId}" not found`);

    const data = this.getLockData(tab);
    return this.prisma.trafficJob.update({
      where: { id: jobId },
      data,
      select: { id: true, internalRef: true },
    });
  }

  private getUnlockField(tab: LockTab): string {
    const map: Record<LockTab, string> = {
      dispatcher: 'dispatchUnlockedAt',
      driver: 'driverUnlockedAt',
      rep: 'repUnlockedAt',
      supplier: 'supplierUnlockedAt',
      edit: 'editUnlockedAt',
      b2c: 'dispatchUnlockedAt',
      online: 'editUnlockedAt',
    };
    return map[tab];
  }

  private getUnlockData(tab: LockTab, userId: string): Record<string, unknown> {
    const now = new Date();
    const map: Record<LockTab, Record<string, unknown>> = {
      dispatcher: { dispatchUnlockedAt: now, dispatchUnlockedById: userId },
      driver: { driverUnlockedAt: now, driverUnlockedById: userId },
      rep: { repUnlockedAt: now, repUnlockedById: userId },
      supplier: { supplierUnlockedAt: now, supplierUnlockedById: userId },
      edit: { editUnlockedAt: now, editUnlockedById: userId },
      b2c: { dispatchUnlockedAt: now, dispatchUnlockedById: userId },
      online: { editUnlockedAt: now, editUnlockedById: userId },
    };
    return map[tab];
  }

  private getLockData(tab: LockTab): Record<string, unknown> {
    const map: Record<LockTab, Record<string, unknown>> = {
      dispatcher: { dispatchUnlockedAt: null, dispatchUnlockedById: null },
      driver: { driverUnlockedAt: null, driverUnlockedById: null },
      rep: { repUnlockedAt: null, repUnlockedById: null },
      supplier: { supplierUnlockedAt: null, supplierUnlockedById: null },
      edit: { editUnlockedAt: null, editUnlockedById: null },
      b2c: { dispatchUnlockedAt: null, dispatchUnlockedById: null },
      online: { editUnlockedAt: null, editUnlockedById: null },
    };
    return map[tab];
  }
}
