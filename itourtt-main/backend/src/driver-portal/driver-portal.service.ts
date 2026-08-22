import {
  Injectable,
  Logger,
  NotFoundException,
  ForbiddenException,
  BadRequestException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import { resolveDriverGeofenceTarget, isWithinGeofence, haversineDistance } from '../common/geofence.util.js';
import { checkNoShowWindow } from '../common/utils/no-show-window.util.js';
import { NoShowDisputeService } from './no-show-dispute.service.js';
import { JobCompletionService } from '../common/services/job-completion.service.js';

type DriverJobStatus = 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';

const DRIVER_ALLOWED_STATUSES: DriverJobStatus[] = ['IN_PROGRESS', 'COMPLETED', 'CANCELLED'];
const DRIVER_TERMINAL_STATUSES = ['COMPLETED', 'CANCELLED', 'NO_SHOW'];

const DRIVER_VALID_TRANSITIONS: Record<string, string[]> = {
  PENDING: ['IN_PROGRESS', 'CANCELLED'],
  IN_PROGRESS: ['COMPLETED', 'CANCELLED'],
  COMPLETED: [],
  CANCELLED: [],
  NO_SHOW: [],
};

const FORTY_EIGHT_HOURS_MS = 48 * 60 * 60 * 1000;

@Injectable()
export class DriverPortalService {
  private readonly logger = new Logger(DriverPortalService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly noShowDisputeService: NoShowDisputeService,
    private readonly jobCompletion: JobCompletionService,
  ) {}

  // Minimal fields for list cards — no agent/customer details
  private readonly jobSummaryInclude = {
    originAirport: { select: { name: true } },
    originZone: { select: { name: true } },
    originHotel: { select: { name: true, zone: { select: { name: true } } } },
    destinationAirport: { select: { name: true } },
    destinationZone: { select: { name: true } },
    destinationHotel: { select: { name: true, zone: { select: { name: true } } } },
    fromZone: { select: { name: true } },
    toZone: { select: { name: true } },
    flight: { select: { flightNo: true, arrivalTime: true, departureTime: true } },
    assignment: {
      include: {
        vehicle: { select: { plateNumber: true, vehicleType: { select: { name: true } } } },
        rep: { select: { name: true, mobileNumber: true } },
      },
    },
  };

  // Full include for detail views and mutation responses
  private readonly jobInclude = {
    originAirport: true,
    originZone: true,
    originHotel: { include: { zone: true } },
    destinationAirport: true,
    destinationZone: true,
    destinationHotel: { include: { zone: true } },
    fromZone: true,
    toZone: true,
    flight: true,
    agent: { select: { legalName: true } },
    customer: { select: { legalName: true } },
    assignment: {
      include: {
        vehicle: { include: { vehicleType: true } },
        rep: { select: { name: true, mobileNumber: true } },
        supplier: { select: { tradeName: true, legalName: true } },
      },
      // externalDriverName and externalDriverPhone are scalar fields — always included
    },
  };

  async resolveDriverId(userId: string): Promise<string> {
    const driver = await this.prisma.driver.findFirst({
      where: { userId, deletedAt: null },
    });
    if (!driver) {
      throw new ForbiddenException('No driver profile linked to this account');
    }
    return driver.id;
  }

  async getMyJobs(userId: string, date?: string) {
    const driverId = await this.resolveDriverId(userId);
    const jobDate = date ? new Date(date) : new Date();
    if (!date) {
      jobDate.setHours(0, 0, 0, 0);
    }

    const assignments = await this.prisma.trafficAssignment.findMany({
      where: {
        driverId,
        trafficJob: {
          jobDate,
          deletedAt: null,
        },
      },
      include: {
        trafficJob: {
          include: this.jobSummaryInclude,
        },
      },
      orderBy: { createdAt: 'asc' },
    });

    const resolveTime = (job: any): number => {
      const t = job.serviceType === 'ARR'
        ? (job.flight?.arrivalTime ?? null)
        : (job.pickUpTime ?? null);
      return t ? new Date(t).getTime() : Number.MAX_SAFE_INTEGER;
    };

    const jobs = assignments
      .map((a) => ({ ...a.trafficJob, driverStatus: a.driverStatus }))
      .sort((a, b) => resolveTime(a) - resolveTime(b));

    return {
      date: jobDate.toISOString().split('T')[0],
      driverId,
      jobs,
    };
  }

  async getJobHistory(userId: string, dateFrom: string, dateTo: string) {
    const driverId = await this.resolveDriverId(userId);
    const from = new Date(dateFrom);
    const to = new Date(dateTo);

    const assignments = await this.prisma.trafficAssignment.findMany({
      where: {
        driverId,
        driverStatus: { in: DRIVER_TERMINAL_STATUSES as any },
        trafficJob: {
          jobDate: { gte: from, lte: to },
          deletedAt: null,
        },
      },
      include: {
        trafficJob: {
          include: {
            ...this.jobSummaryInclude,
            driverFees: {
              where: { driverId },
              select: { amount: true, currency: true },
            },
          },
        },
      },
      orderBy: { createdAt: 'asc' },
    });

    return {
      dateFrom,
      dateTo,
      driverId,
      jobs: assignments.map((a) => ({
        ...a.trafficJob,
        driverStatus: a.driverStatus,
        feeEarned: a.trafficJob.driverFees[0]
          ? Number(a.trafficJob.driverFees[0].amount)
          : null,
      })),
    };
  }

  async updateJobStatus(
    userId: string,
    jobId: string,
    status: DriverJobStatus,
    latitude: number | null,
    longitude: number | null,
  ) {
    const driverId = await this.resolveDriverId(userId);

    if (!DRIVER_ALLOWED_STATUSES.includes(status)) {
      throw new BadRequestException(
        `Invalid status. Allowed: ${DRIVER_ALLOWED_STATUSES.join(', ')}`,
      );
    }

    const assignment = await this.prisma.trafficAssignment.findFirst({
      where: {
        driverId,
        trafficJobId: jobId,
      },
      include: {
        trafficJob: {
          include: {
            originAirport: true,
            originZone: true,
            originHotel: { include: { zone: true } },
            flight: true,
          },
        },
      },
    });

    if (!assignment) {
      throw new NotFoundException('Job not found or not assigned to you');
    }

    this.checkDriverTimelock(assignment.trafficJob);
    this.checkDriverGeofence(assignment.trafficJob, latitude, longitude);

    const currentStatus = assignment.driverStatus;
    const allowed = DRIVER_VALID_TRANSITIONS[currentStatus] || [];
    if (!allowed.includes(status)) {
      throw new BadRequestException(
        `Cannot change driver status from "${currentStatus}" to "${status}"`,
      );
    }

    // Time guard: cannot start IN_PROGRESS before job time
    if (status === 'IN_PROGRESS') {
      const flight = (assignment.trafficJob as any).flight;
      const jobTime =
        assignment.trafficJob.serviceType === 'ARR'
          ? (flight?.arrivalTime ?? null)
          : (assignment.trafficJob.pickUpTime ?? null);
      if (jobTime) {
        const now = new Date();
        if (now < new Date(jobTime)) {
          const timeStr = new Date(jobTime).toLocaleTimeString('en-GB', {
            timeZone: 'Africa/Cairo',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
          });
          throw new BadRequestException(
            `Cannot start job before the scheduled time (${timeStr})`,
          );
        }
      }
    }

    const gpsMapLink =
      latitude != null && longitude != null
        ? `https://www.google.com/maps?q=${latitude},${longitude}`
        : null;

    return this.prisma.$transaction(async (tx) => {
      const updated = await tx.trafficAssignment.update({
        where: { id: assignment.id },
        data: { driverStatus: status as any },
        include: {
          trafficJob: {
            include: this.jobInclude,
          },
        },
      });

      await tx.statusChangeLog.create({
        data: {
          assignmentId: assignment.id,
          changedBy: 'DRIVER',
          changedById: driverId,
          previousStatus: currentStatus as any,
          newStatus: status as any,
          gpsLatitude: latitude,
          gpsLongitude: longitude,
          gpsMapLink,
        },
      });

      // This endpoint can reach COMPLETED (IN_PROGRESS → COMPLETED), so the
      // overall job status has to be rolled up here too — not only in
      // submitCompleted.
      await this.jobCompletion.reconcileJobStatus(tx, jobId);

      const job = await tx.trafficJob.findUniqueOrThrow({
        where: { id: jobId },
        include: this.jobInclude,
      });

      return {
        ...job,
        driverStatus: updated.driverStatus,
      };
    });
  }

  async submitInProgress(
    userId: string,
    jobId: string,
    imageUrls: string[],
    latitude: number | null,
    longitude: number | null,
  ) {
    const driver = await this.prisma.driver.findFirst({
      where: { userId, deletedAt: null },
      include: { user: { select: { name: true } } },
    });
    if (!driver) throw new ForbiddenException('No driver profile linked to this account');
    const driverId = driver.id;
    const submittedByLabel = `DRIVER-${driver.user?.name ?? 'Unknown'}`;

    const assignment = await this.prisma.trafficAssignment.findFirst({
      where: { driverId, trafficJobId: jobId },
      include: {
        trafficJob: {
          include: {
            originAirport: true,
            originZone: true,
            originHotel: { include: { zone: true } },
            flight: true,
          },
        },
      },
    });

    if (!assignment) throw new NotFoundException('Job not found or not assigned to you');

    this.checkDriverTimelock(assignment.trafficJob);
    this.checkDriverGeofence(assignment.trafficJob, latitude, longitude);

    const currentStatus = assignment.driverStatus;
    if (currentStatus !== 'PENDING' && currentStatus !== 'IN_PROGRESS') {
      throw new BadRequestException(
        `Cannot submit in-progress evidence: current status is "${currentStatus}"`,
      );
    }

    // Time guard: cannot start before job time
    const flight = (assignment.trafficJob as any).flight;
    const jobTime =
      assignment.trafficJob.serviceType === 'ARR'
        ? (flight?.arrivalTime ?? null)
        : (assignment.trafficJob.pickUpTime ?? null);
    if (currentStatus === 'PENDING' && jobTime && new Date() < new Date(jobTime)) {
      const timeStr = new Date(jobTime).toLocaleTimeString('en-GB', {
        timeZone: 'Africa/Cairo',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      });
      throw new BadRequestException(
        `Cannot start job before the scheduled time (${timeStr})`,
      );
    }

    const gpsMapLink =
      latitude != null && longitude != null
        ? `https://www.google.com/maps?q=${latitude},${longitude}`
        : null;
    const alreadyStarted = currentStatus === 'IN_PROGRESS';

    return this.prisma.$transaction(async (tx) => {
      const updated = await tx.trafficAssignment.update({
        where: { id: assignment.id },
        data: alreadyStarted ? {} : { driverStatus: 'IN_PROGRESS' as any },
        include: { trafficJob: { include: this.jobInclude } },
      });

      await tx.inProgressEvidence.create({
        data: {
          trafficJobId: jobId,
          imageUrls,
          gpsLatitude: latitude,
          gpsLongitude: longitude,
          gpsMapLink,
          submittedBy: submittedByLabel,
          submittedById: driverId,
        },
      });

      if (!alreadyStarted) {
        await tx.statusChangeLog.create({
          data: {
            assignmentId: assignment.id,
            changedBy: 'DRIVER',
            changedById: driverId,
            previousStatus: currentStatus as any,
            newStatus: 'IN_PROGRESS' as any,
            gpsLatitude: latitude,
            gpsLongitude: longitude,
            gpsMapLink,
          },
        });
      }

      return {
        ...updated.trafficJob,
        driverStatus: updated.driverStatus,
      };
    });
  }

  async submitCompleted(
    userId: string,
    jobId: string,
    imageUrls: string[],
    latitude: number | null,
    longitude: number | null,
  ) {
    const driver = await this.prisma.driver.findFirst({
      where: { userId, deletedAt: null },
      include: { user: { select: { name: true } } },
    });
    if (!driver) throw new ForbiddenException('No driver profile linked to this account');
    const driverId = driver.id;
    const submittedByLabel = `DRIVER-${driver.user?.name ?? 'Unknown'}`;

    const assignment = await this.prisma.trafficAssignment.findFirst({
      where: { driverId, trafficJobId: jobId },
      include: {
        trafficJob: {
          include: {
            originAirport: true,
            originZone: true,
            originHotel: { include: { zone: true } },
            flight: true,
          },
        },
      },
    });

    if (!assignment) throw new NotFoundException('Job not found or not assigned to you');

    this.checkDriverTimelock(assignment.trafficJob);
    this.checkDriverGeofence(assignment.trafficJob, latitude, longitude);

    const currentStatus = assignment.driverStatus;
    if (DRIVER_TERMINAL_STATUSES.includes(currentStatus)) {
      throw new BadRequestException(`Driver status is already terminal: "${currentStatus}"`);
    }
    if (currentStatus !== 'IN_PROGRESS') {
      throw new BadRequestException(`Cannot complete job: must be In Progress first`);
    }

    // Time guard: at least 15 minutes after job time
    const flight = (assignment.trafficJob as any).flight;
    const jobTime =
      assignment.trafficJob.serviceType === 'ARR'
        ? (flight?.arrivalTime ?? null)
        : (assignment.trafficJob.pickUpTime ?? null);
    if (jobTime) {
      const now = new Date();
      const minCompleteAt = new Date(new Date(jobTime).getTime() + 15 * 60 * 1000);
      if (now < minCompleteAt) {
        const timeStr = minCompleteAt.toLocaleTimeString('en-GB', {
          timeZone: 'Africa/Cairo',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
        });
        throw new BadRequestException(
          `Cannot mark job as completed before ${timeStr} (minimum 15 minutes after job time)`,
        );
      }
    }

    // Collection guard
    if (assignment.trafficJob.collectionRequired && !assignment.trafficJob.collectionCollected) {
      throw new BadRequestException('Collection must be marked as collected before completing the job');
    }

    const gpsMapLink =
      latitude != null && longitude != null
        ? `https://www.google.com/maps?q=${latitude},${longitude}`
        : null;

    return this.prisma.$transaction(async (tx) => {
      const updated = await tx.trafficAssignment.update({
        where: { id: assignment.id },
        data: { driverStatus: 'COMPLETED' as any },
        include: { trafficJob: { include: this.jobInclude } },
      });

      await tx.completedEvidence.create({
        data: {
          trafficJobId: jobId,
          imageUrls,
          gpsLatitude: latitude,
          gpsLongitude: longitude,
          gpsMapLink,
          submittedBy: submittedByLabel,
          submittedById: driverId,
        },
      });

      await tx.statusChangeLog.create({
        data: {
          assignmentId: assignment.id,
          changedBy: 'DRIVER',
          changedById: driverId,
          previousStatus: currentStatus as any,
          newStatus: 'COMPLETED' as any,
          gpsLatitude: latitude,
          gpsLongitude: longitude,
          gpsMapLink,
        },
      });

      // Roll the overall job status up from the two portal legs and materialise
      // the driver / rep fees that completion unlocks. Also closes the rep leg
      // on DEP jobs, where the rep has no work left once the car has run.
      await this.jobCompletion.reconcileJobStatus(tx, jobId);

      const job = await tx.trafficJob.findUniqueOrThrow({
        where: { id: jobId },
        include: this.jobInclude,
      });

      return { ...job, driverStatus: updated.driverStatus };
    });
  }

  async markCollected(userId: string, jobId: string, collected: boolean) {
    const driverId = await this.resolveDriverId(userId);

    const assignment = await this.prisma.trafficAssignment.findFirst({
      where: { driverId, trafficJobId: jobId },
      include: { trafficJob: true },
    });

    if (!assignment) {
      throw new NotFoundException('Job not found or not assigned to you');
    }

    if (!assignment.trafficJob.collectionRequired) {
      throw new BadRequestException('This job does not require collection');
    }

    this.checkDriverTimelock(assignment.trafficJob);

    return this.prisma.trafficJob.update({
      where: { id: jobId },
      data: {
        collectionCollected: collected,
        collectionCollectedAt: collected ? new Date() : null,
      },
      include: this.jobInclude,
    });
  }

  async submitNoShow(
    userId: string,
    jobId: string,
    imageUrls: string[],
    latitude: number | null,
    longitude: number | null,
  ) {
    const driver = await this.prisma.driver.findFirst({
      where: { userId, deletedAt: null },
      include: { user: { select: { name: true } } },
    });
    if (!driver) throw new ForbiddenException('No driver profile linked to this account');
    const driverId = driver.id;
    const submittedByLabel = `DRIVER-${driver.user?.name ?? 'Unknown'}`;

    const assignment = await this.prisma.trafficAssignment.findFirst({
      where: {
        driverId,
        trafficJobId: jobId,
      },
      include: {
        trafficJob: {
          include: {
            flight: true,
            originAirport: true,
            originZone: true,
            originHotel: { include: { zone: true } },
          },
        },
      },
    });

    if (!assignment) {
      throw new NotFoundException('Job not found or not assigned to you');
    }

    this.checkDriverTimelock(assignment.trafficJob);
    this.checkDriverGeofence(assignment.trafficJob, latitude, longitude);

    const currentStatus = assignment.driverStatus;
    if (DRIVER_TERMINAL_STATUSES.includes(currentStatus)) {
      throw new BadRequestException(
        `Driver status is already terminal: "${currentStatus}"`,
      );
    }

    if (currentStatus !== 'PENDING' && currentStatus !== 'IN_PROGRESS') {
      throw new BadRequestException(
        `Cannot change driver status from "${currentStatus}"`,
      );
    }

    checkNoShowWindow(assignment.trafficJob);

    const gpsMapLink =
      latitude != null && longitude != null
        ? `https://www.google.com/maps?q=${latitude},${longitude}`
        : null;

    return this.prisma.$transaction(async (tx) => {
      const updated = await tx.trafficAssignment.update({
        where: { id: assignment.id },
        data: { driverStatus: 'NO_SHOW' as any },
        include: {
          trafficJob: {
            include: this.jobInclude,
          },
        },
      });

      // Update the traffic job status itself to NO_SHOW
      await tx.trafficJob.update({
        where: { id: jobId },
        data: { status: 'NO_SHOW' as any },
      });

      await tx.noShowEvidence.create({
        data: {
          trafficJobId: jobId,
          imageUrls,
          gpsLatitude: latitude,
          gpsLongitude: longitude,
          gpsMapLink,
          submittedBy: submittedByLabel,
          submittedById: driverId,
        },
      });

      await tx.statusChangeLog.create({
        data: {
          assignmentId: assignment.id,
          changedBy: 'DRIVER',
          changedById: driverId,
          previousStatus: currentStatus as any,
          newStatus: 'NO_SHOW' as any,
          gpsLatitude: latitude,
          gpsLongitude: longitude,
          gpsMapLink,
        },
      });

      return {
        ...updated.trafficJob,
        driverStatus: updated.driverStatus,
      };
    }).then((result) => {
      // Fire-and-forget: generate PDF evidence report and email agent dispute address
      this.noShowDisputeService.generateAndSendDisputeReport(jobId).catch(() => {
        // Errors already logged inside the service
      });
      return result;
    });
  }

  async getNotifications(userId: string) {
    const driverId = await this.resolveDriverId(userId);

    const notifications = await this.prisma.driverNotification.findMany({
      where: { driverId },
      orderBy: { createdAt: 'desc' },
      take: 50,
      include: {
        trafficJob: {
          select: {
            internalRef: true,
            serviceType: true,
            jobDate: true,
          },
        },
      },
    });

    const unreadCount = await this.prisma.driverNotification.count({
      where: { driverId, isRead: false },
    });

    return { notifications, unreadCount };
  }

  async markNotificationRead(userId: string, notificationId: string) {
    const driverId = await this.resolveDriverId(userId);

    const notification = await this.prisma.driverNotification.findFirst({
      where: { id: notificationId, driverId },
    });

    if (!notification) {
      throw new NotFoundException('Notification not found');
    }

    return this.prisma.driverNotification.update({
      where: { id: notificationId },
      data: { isRead: true },
    });
  }

  async markAllRead(userId: string) {
    const driverId = await this.resolveDriverId(userId);

    await this.prisma.driverNotification.updateMany({
      where: { driverId, isRead: false },
      data: { isRead: true },
    });

    return { success: true };
  }

  async getProfile(userId: string) {
    const driver = await this.prisma.driver.findFirst({
      where: { userId, deletedAt: null },
      include: {
        driverVehicles: {
          where: { unassignedAt: null },
          include: {
            vehicle: { include: { vehicleType: true } },
          },
        },
      },
    });

    if (!driver) {
      throw new ForbiddenException('No driver profile linked to this account');
    }

    return driver;
  }

  private checkDriverTimelock(job: { jobDate: Date; driverUnlockedAt?: Date | null }) {
    if (job.driverUnlockedAt) return;
    const cutoff = new Date(job.jobDate.getTime() + FORTY_EIGHT_HOURS_MS);
    if (new Date() > cutoff) {
      throw new ForbiddenException(
        'Drivers cannot update job status more than 48 hours after the service date.',
      );
    }
  }

  private checkDriverGeofence(job: any, latitude: number | null, longitude: number | null) {
    if (latitude == null || longitude == null) {
      // No GPS captured for this submission — nothing to validate.
      return;
    }
    const target = resolveDriverGeofenceTarget(job);
    if (!target) {
      // No coordinates configured for this job's location — skip check
      return;
    }
    if (!isWithinGeofence(latitude, longitude, target.lat, target.lng, 2000)) {
      // Outside 2km — log for audit but do not block the driver
      const dist = Math.round(haversineDistance(latitude, longitude, target.lat, target.lng));
      this.logger.warn(
        `Driver geofence miss on job ${job.id}: driver at (${latitude},${longitude}) is ${dist}m from target (${target.lat},${target.lng})`,
      );
    }
  }

  async findJobDetail(userId: string, jobId: string) {
    const driverId = await this.resolveDriverId(userId);
    const job = await this.prisma.trafficJob.findFirst({
      where: { id: jobId, assignment: { driverId }, deletedAt: null },
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
    if (!job) throw new NotFoundException('Job not found or not assigned to you');
    return job;
  }

  async getJobStampMeta(jobId: string) {
    const job = await this.prisma.trafficJob.findUnique({
      where: { id: jobId },
      select: {
        status: true,
        assignment: {
          select: {
            driverStatus: true,
            driver: { select: { name: true } },
          },
        },
      },
    });
    const ds = job?.assignment?.driverStatus;
    return {
      rep: null,
      driver: job?.assignment?.driver?.name ?? null,
      status: job?.status ?? null,
      portalStatus: ds ? `Driver: ${ds.replace(/_/g, ' ')}` : null,
    };
  }
}
