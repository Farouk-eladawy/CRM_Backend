import {
  Injectable,
  NotFoundException,
  ForbiddenException,
  BadRequestException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';

const FORTY_EIGHT_HOURS_MS = 48 * 60 * 60 * 1000;

@Injectable()
export class SupplierPortalService {
  constructor(private readonly prisma: PrismaService) {}

  private readonly jobInclude = {
    fromZone: true,
    toZone: true,
    originHotel: { select: { name: true } },
    destinationHotel: { select: { name: true } },
    originZone: { select: { name: true } },
    destinationZone: { select: { name: true } },
    originAirport: { select: { code: true } },
    destinationAirport: { select: { code: true } },
    flight: true,
    agent: { select: { legalName: true } },
    customer: { select: { legalName: true } },
    assignment: {
      include: {
        vehicle: { include: { vehicleType: true } },
        driver: { select: { name: true, mobileNumber: true } },
        rep: { select: { name: true, mobileNumber: true } },
      },
    },
  };

  async resolveSupplierId(userId: string): Promise<string> {
    const supplier = await this.prisma.supplier.findFirst({
      where: { userId, deletedAt: null },
    });
    if (!supplier) {
      throw new ForbiddenException('No supplier profile linked to this account');
    }
    return supplier.id;
  }

  async getMyJobs(userId: string, date?: string) {
    const supplierId = await this.resolveSupplierId(userId);
    const jobDate = date ? new Date(date) : new Date();
    if (!date) {
      jobDate.setHours(0, 0, 0, 0);
    }

    const assignments = await this.prisma.trafficAssignment.findMany({
      where: {
        OR: [
          { vehicle: { supplierId } },
          { supplierId },
        ],
        trafficJob: {
          jobDate,
          deletedAt: null,
        },
      },
      include: {
        trafficJob: {
          include: this.jobInclude,
        },
      },
      orderBy: { createdAt: 'asc' },
    });

    return {
      date: jobDate.toISOString().split('T')[0],
      supplierId,
      jobs: assignments.map((a) => ({
        ...a.trafficJob,
        supplierStatus: a.supplierStatus,
        supplierNotes: a.supplierNotes,
      })),
    };
  }

  async completeJob(userId: string, jobId: string, notes?: string) {
    const supplierId = await this.resolveSupplierId(userId);

    const assignment = await this.prisma.trafficAssignment.findFirst({
      where: {
        trafficJobId: jobId,
        OR: [
          { vehicle: { supplierId } },
          { supplierId },
        ],
      },
      include: {
        trafficJob: true,
      },
    });

    if (!assignment) {
      throw new NotFoundException('Job not found or not assigned to your vehicles');
    }

    this.checkSupplierTimelock(assignment.trafficJob);

    if (assignment.supplierStatus === 'COMPLETED') {
      throw new BadRequestException('Job is already marked as completed');
    }

    const updated = await this.prisma.trafficAssignment.update({
      where: { id: assignment.id },
      data: {
        supplierStatus: 'COMPLETED',
        supplierNotes: notes ?? null,
      },
      include: {
        trafficJob: {
          include: this.jobInclude,
        },
      },
    });

    return {
      ...updated.trafficJob,
      supplierStatus: updated.supplierStatus,
      supplierNotes: updated.supplierNotes,
    };
  }

  async getProfile(userId: string) {
    const supplier = await this.prisma.supplier.findFirst({
      where: { userId, deletedAt: null },
      include: {
        vehicles: {
          where: { deletedAt: null },
          include: { vehicleType: true },
        },
      },
    });

    if (!supplier) {
      throw new ForbiddenException('No supplier profile linked to this account');
    }

    return supplier;
  }

  private checkSupplierTimelock(job: { jobDate: Date; supplierUnlockedAt?: Date | null }) {
    if (job.supplierUnlockedAt) return;
    const cutoff = new Date(job.jobDate.getTime() + FORTY_EIGHT_HOURS_MS);
    if (new Date() > cutoff) {
      throw new ForbiddenException(
        'Suppliers cannot update job status more than 48 hours after the service date.',
      );
    }
  }

  async findJobDetail(userId: string, jobId: string) {
    const supplierId = await this.resolveSupplierId(userId);
    const job = await this.prisma.trafficJob.findFirst({
      where: { id: jobId, assignment: { vehicle: { supplierId } }, deletedAt: null },
      include: {
        agent: true,
        customer: true,
        originAirport: true,
        originZone: true,
        originHotel: { include: { zone: true } },
        destinationAirport: true,
        destinationZone: true,
        destinationHotel: { include: { zone: true } },
        fromZone: true,
        toZone: true,
        requestedVehicleType: true,
        flight: true,
        createdBy: { select: { id: true, name: true } },
        assignment: {
          include: {
            vehicle: { include: { vehicleType: true, supplier: { select: { id: true, legalName: true, tradeName: true } } } },
            driver: true,
            rep: true,
          },
        },
        noShowEvidence: true,
      },
    });
    if (!job) throw new NotFoundException('Job not found or not assigned to your vehicles');
    return job;
  }
}
