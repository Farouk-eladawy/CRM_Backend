import {
  Injectable,
  NotFoundException,
  BadRequestException,
  ConflictException,
  ForbiddenException,
  Logger,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import { EmailService } from '../email/email.service.js';
import { PushNotificationsService } from '../push-notifications/push-notifications.service.js';
import { NotificationsService } from '../notifications/notifications.service.js';
import { WhatsappNotificationsService } from '../whatsapp-notifications/whatsapp-notifications.service.js';
import { B2CService } from '../b2c/b2c.service.js';
import { AssignJobDto } from './dto/assign-job.dto.js';
import { ReassignJobDto } from './dto/reassign-job.dto.js';
import type { ServiceType, JobStatus } from '../../generated/prisma/client.js';

const FORTY_EIGHT_HOURS_MS = 48 * 60 * 60 * 1000;

@Injectable()
export class DispatchService {
  private readonly logger = new Logger(DispatchService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly emailService: EmailService,
    private readonly pushService: PushNotificationsService,
    private readonly notificationsService: NotificationsService,
    private readonly whatsappService: WhatsappNotificationsService,
    private readonly b2cService: B2CService,
  ) {}

  // ─────────────────────────────────────────────
  // DAY VIEW
  // ─────────────────────────────────────────────

  async getDayView(date: string) {
    const jobDate = new Date(date);

    const baseInclude = {
      agent: { select: { id: true, legalName: true, tradeName: true, phone: true } },
      customer: { select: { id: true, legalName: true, tradeName: true, phone: true } },
      originAirport: { select: { id: true, name: true, code: true } },
      originZone: { select: { id: true, name: true } },
      originHotel: { select: { id: true, name: true, zone: { select: { id: true, name: true } } } },
      destinationAirport: { select: { id: true, name: true, code: true } },
      destinationZone: { select: { id: true, name: true } },
      destinationHotel: { select: { id: true, name: true, zone: { select: { id: true, name: true } } } },
      fromZone: { select: { id: true, name: true } },
      toZone: { select: { id: true, name: true } },
      requestedVehicleType: { select: { id: true, name: true, seatCapacity: true } },
      flight: { select: { id: true, flightNo: true, carrier: true, terminal: true, arrivalTime: true, departureTime: true } },
      jobServiceType: { select: { id: true, name: true } },
      assignment: {
        select: {
          id: true,
          vehicleId: true,
          driverId: true,
          repId: true,
          supplierId: true,
          supplierCarTypeId: true,
          driverStatus: true,
          repStatus: true,
          supplierStatus: true,
          externalDriverName: true,
          externalDriverPhone: true,
          remarks: true,
          supplierNotes: true,
          vehicle: { select: { id: true, plateNumber: true, vehicleType: { select: { id: true, name: true, seatCapacity: true } } } },
          driver: { select: { id: true, name: true, mobileNumber: true } },
          rep: { select: { id: true, name: true } },
          supplier: { select: { id: true, legalName: true, tradeName: true } },
          supplierCarType: { select: { id: true, vehicleType: { select: { id: true, name: true, seatCapacity: true } } } },
        },
      },
    };

    const baseWhere = {
      jobDate,
      deletedAt: null,
    };

    const [arrivals, departures, cityJobs] = await Promise.all([
      this.prisma.trafficJob.findMany({
        where: { ...baseWhere, serviceType: 'ARR' as ServiceType },
        include: baseInclude,
        orderBy: [
          { flight: { arrivalTime: 'asc' } },
          { createdAt: 'asc' },
        ],
      }),
      this.prisma.trafficJob.findMany({
        where: { ...baseWhere, serviceType: 'DEP' as ServiceType },
        include: baseInclude,
        orderBy: [
          { flight: { departureTime: 'asc' } },
          { createdAt: 'asc' },
        ],
      }),
      this.prisma.trafficJob.findMany({
        where: { ...baseWhere, serviceType: { notIn: ['ARR', 'DEP'] as ServiceType[] } },
        include: baseInclude,
        orderBy: { createdAt: 'asc' },
      }),
    ]);

    return { arrivals, departures, cityJobs };
  }

  // ─────────────────────────────────────────────
  // ASSIGN JOB
  // ─────────────────────────────────────────────

  async assignJob(dto: AssignJobDto, userId: string, userRole?: string, roleSlug?: string, userPermissions?: Set<string>) {
    // Permission-based field validation
    if (userPermissions) {
      const canVehicle = userPermissions.has('dispatch.assignment.assignVehicle');
      const canDriver = userPermissions.has('dispatch.assignment.assignDriver');
      const canRep = userPermissions.has('dispatch.assignment.assignRep');

      if ((dto.vehicleId || dto.supplierCarTypeId) && !canVehicle) {
        throw new ForbiddenException('You do not have permission to assign vehicles');
      }
      if (dto.driverId && !canDriver) {
        throw new ForbiddenException('You do not have permission to assign drivers');
      }
      if (dto.repId && !canRep) {
        throw new ForbiddenException('You do not have permission to assign reps');
      }
    }

    // Must provide at least vehicle (or supplier car type) or rep
    if (!dto.vehicleId && !dto.supplierCarTypeId && !dto.repId) {
      throw new BadRequestException('Either vehicleId, supplierCarTypeId, or repId must be provided');
    }

    // 1. Verify job exists and is eligible
    const job = await this.prisma.trafficJob.findFirst({
      where: { id: dto.trafficJobId, deletedAt: null },
      include: { assignment: true, flight: true, originAirport: true, originZone: true, originHotel: true, destinationAirport: true, destinationZone: true, destinationHotel: true },
    });

    if (!job) {
      throw new NotFoundException(
        `Traffic job with ID "${dto.trafficJobId}" not found`,
      );
    }

    // Dispatcher 48-hour lock (skip if job was explicitly unlocked)
    this.checkDispatcherTimelock(job.jobDate, userRole, roleSlug, job.dispatchUnlockedAt);

    if (job.status === ('CANCELLED' as JobStatus)) {
      throw new BadRequestException('Cannot assign a cancelled job');
    }

    if (job.assignment) {
      throw new ConflictException(
        'This job already has an assignment. Use reassign instead.',
      );
    }

    // 2. Verify vehicle exists and is active (only when vehicleId provided)
    if (dto.vehicleId) {
      const vehicle = await this.prisma.vehicle.findFirst({
        where: { id: dto.vehicleId, deletedAt: null, isActive: true },
        include: { vehicleType: true },
      });

      if (!vehicle) {
        throw new NotFoundException(
          `Vehicle with ID "${dto.vehicleId}" not found or inactive`,
        );
      }

      // 3. Pax count must not exceed vehicle capacity
      if (job.paxCount > vehicle.vehicleType.seatCapacity) {
        throw new BadRequestException(
          `Pax count (${job.paxCount}) exceeds vehicle capacity (${vehicle.vehicleType.seatCapacity})`,
        );
      }

      // 3b. Vehicle type mismatch check (requested vs assigned)
      if (
        job.requestedVehicleTypeId &&
        vehicle.vehicleTypeId !== job.requestedVehicleTypeId &&
        !dto.allowTypeMismatch
      ) {
        const requestedType = await this.prisma.vehicleType.findUnique({
          where: { id: job.requestedVehicleTypeId },
          select: { name: true },
        });
        throw new ConflictException(
          `Vehicle type mismatch: requested "${requestedType?.name || 'Unknown'}", got "${vehicle.vehicleType.name}"`,
        );
      }

      // 4. Check vehicle availability with time-aware + route-aware rules
      await this.validateVehicleAvailability(dto.vehicleId, job);
    }

    // 5. Validate driver with time-aware rules (skip for external/supplier drivers)
    if (dto.driverId) {
      const driver = await this.prisma.driver.findFirst({
        where: { id: dto.driverId, deletedAt: null, isActive: true },
      });
      if (!driver) {
        throw new NotFoundException(
          `Driver with ID "${dto.driverId}" not found or inactive`,
        );
      }
      await this.validateDriverAvailability(dto.driverId, job);
    }

    // 6. Validate rep
    if (dto.repId) {
      const rep = await this.prisma.rep.findFirst({
        where: { id: dto.repId, deletedAt: null, isActive: true },
      });
      if (!rep) {
        throw new NotFoundException(
          `Rep with ID "${dto.repId}" not found or inactive`,
        );
      }
      await this.validateRepAvailability(dto.repId, job);
    }

    // 5b. Validate supplier car type and resolve supplierId
    let resolvedSupplierId: string | null = dto.supplierId ?? null;
    if (dto.supplierCarTypeId) {
      const carType = await this.prisma.supplierCarType.findFirst({
        where: { id: dto.supplierCarTypeId },
        include: { vehicleType: true },
      });
      if (!carType) {
        throw new NotFoundException(`Supplier car type with ID "${dto.supplierCarTypeId}" not found`);
      }
      // Pax count must not exceed the supplier car's capacity (same rule as own vehicles).
      if (job.paxCount > carType.vehicleType.seatCapacity) {
        throw new BadRequestException(
          `Pax count (${job.paxCount}) exceeds vehicle capacity (${carType.vehicleType.seatCapacity})`,
        );
      }
      if (dto.supplierId && carType.supplierId !== dto.supplierId) {
        throw new BadRequestException('Supplier car type does not belong to the specified supplier');
      }
      resolvedSupplierId = carType.supplierId;
    }

    // Mutual exclusion: a new assignment's car is either OWN (vehicle) or SUPPLIER
    // (supplier car type), never both. A supplier car type wins and clears any
    // vehicle; choosing an own vehicle clears the supplier fields.
    const hasCarType = !!dto.supplierCarTypeId;
    const hasVehicle = !!dto.vehicleId;
    const createVehicleId = hasCarType ? null : (dto.vehicleId ?? null);
    const createSupplierCarTypeId = hasCarType ? dto.supplierCarTypeId! : null;
    const createSupplierId = hasCarType
      ? resolvedSupplierId
      : hasVehicle
        ? null
        : resolvedSupplierId;

    // 7. Create assignment and update job status in a transaction
    const assignment = await this.prisma.$transaction(async (tx) => {
      const created = await tx.trafficAssignment.create({
        data: {
          trafficJobId: dto.trafficJobId,
          vehicleId: createVehicleId,
          driverId: dto.driverId ?? null,
          repId: dto.repId ?? null,
          supplierId: createSupplierId,
          supplierCarTypeId: createSupplierCarTypeId,
          externalDriverName: dto.externalDriverName ?? null,
          externalDriverPhone: dto.externalDriverPhone ?? null,
          remarks: dto.remarks ?? null,
          assignedById: userId,
        },
        include: {
          vehicle: { include: { vehicleType: true } },
          driver: true,
          rep: true,
          supplier: { select: { id: true, legalName: true, tradeName: true } },
          supplierCarType: { include: { vehicleType: true } },
          trafficJob: {
            include: { guestBooking: { select: { bookingRef: true } } },
          },
        },
      });

      await tx.trafficJob.update({
        where: { id: dto.trafficJobId },
        data: { status: 'ASSIGNED' as JobStatus },
      });

      if (dto.repId) {
        await tx.repNotification.create({
          data: {
            repId: dto.repId,
            title: 'New Job Assigned',
            message: `${created.trafficJob.internalRef} - ${created.trafficJob.serviceType} on ${created.trafficJob.jobDate.toISOString().split('T')[0]}`,
            type: 'JOB_ASSIGNED',
            trafficJobId: dto.trafficJobId,
          },
        });
      }

      if (dto.driverId) {
        await tx.driverNotification.create({
          data: {
            driverId: dto.driverId,
            title: 'New Job Assigned',
            message: `${created.trafficJob.internalRef} - ${created.trafficJob.serviceType} on ${created.trafficJob.jobDate.toISOString().split('T')[0]}`,
            type: 'JOB_ASSIGNED',
            trafficJobId: dto.trafficJobId,
          },
        });
      }

      return created;
    });

    // Push notifications (fire-and-forget)
    if (assignment.driverId) {
      this.pushService.sendToDriver(
        assignment.driverId,
        'New Job Assigned',
        `${assignment.trafficJob.internalRef} - ${assignment.trafficJob.serviceType}`,
        { jobId: dto.trafficJobId, type: 'JOB_ASSIGNED' },
      ).catch(() => {});
    }
    if (assignment.repId) {
      this.pushService.sendToRep(
        assignment.repId,
        'New Job Assigned',
        `${assignment.trafficJob.internalRef} - ${assignment.trafficJob.serviceType}`,
        { jobId: dto.trafficJobId, type: 'JOB_ASSIGNED' },
      ).catch(() => {});
    }

    // Send the staff-assignment email only once BOTH a driver and a rep are
    // assigned. A brand-new assignment with both set qualifies immediately.
    if (assignment.driverId && assignment.repId && assignment.driver && assignment.rep) {
      this.sendStaffAssignmentEmail(
        assignment.trafficJob.id,
        assignment.driver,
        assignment.rep,
        assignment.vehicle,
      ).catch((err) =>
        this.logger.error(`Failed to send staff assignment email: ${err.message}`),
      );
    }

    // Send B2C client assignment notification (fire-and-forget)
    if (assignment.trafficJob?.guestBooking?.bookingRef) {
      this.b2cService
        .sendAssignmentNotification(assignment.trafficJob.guestBooking.bookingRef)
        .catch((err) => this.logger.error(`Failed to send B2C assignment notification: ${err.message}`));
    }

    // WhatsApp: trigger driver assigned (fire-and-forget)
    if (assignment.driverId) {
      this.whatsappService.triggerDriverAssigned(dto.trafficJobId).catch(() => {});
    }

    // Notify online users about the dispatch action (fire-and-forget)
    this.notificationsService.notifyDispatchAction(
      dto.trafficJobId,
      userId,
      'ASSIGNED',
      {
        vehiclePlate: assignment.vehicle?.plateNumber,
        driverName: assignment.driver?.name ?? undefined,
        repName: assignment.rep?.name ?? undefined,
      },
    ).catch((err) => this.logger.error(`Failed to send dispatch notification: ${err.message}`));

    // Non-blocking heads-up: vehicle/driver already booked elsewhere at this time.
    const warnings = await this.detectAssignmentConflicts(job, {
      vehicleId: createVehicleId,
      driverId: dto.driverId ?? null,
    });
    return warnings.length ? { ...assignment, warnings } : assignment;
  }

  private async sendStaffAssignmentEmail(
    trafficJobId: string,
    driver: { name: string; mobileNumber?: string | null },
    rep: { name: string; mobileNumber?: string | null },
    vehicle: { plateNumber: string; color?: string | null; vehicleType?: { name: string } | null } | null,
  ) {
    const guestBooking = await this.prisma.guestBooking.findFirst({
      where: { trafficJobId },
      include: {
        fromZone: { select: { name: true } },
        hotel: { select: { name: true } },
        originAirport: { select: { name: true } },
      },
    });

    if (!guestBooking) return;

    // Meeting point: arrival → the airport the guest lands at; departure → the
    // pickup/start point (hotel, else the origin zone).
    const meetingPoint =
      guestBooking.serviceType === 'ARR'
        ? guestBooking.originAirport?.name ?? guestBooking.fromZone?.name ?? undefined
        : guestBooking.hotel?.name ?? guestBooking.fromZone?.name ?? undefined;

    // HH:MM, matching the format used by the other guest emails.
    const pickupTime = guestBooking.pickupTime
      ? guestBooking.pickupTime.toISOString().slice(11, 16)
      : undefined;

    await this.emailService.sendStaffAssignment({
      bookingRef: guestBooking.bookingRef,
      guestName: guestBooking.guestName,
      guestEmail: guestBooking.guestEmail,
      serviceType: guestBooking.serviceType,
      meetingPoint,
      pickupTime,
      repName: rep.name,
      repPhone: rep.mobileNumber ?? undefined,
      driverName: driver.name,
      driverPhone: driver.mobileNumber ?? '',
      vehiclePlate: vehicle?.plateNumber ?? '',
      vehicleType: vehicle?.vehicleType?.name ?? '',
      vehicleColor: vehicle?.color ?? undefined,
    });
  }

  // ─────────────────────────────────────────────
  // REASSIGN JOB
  // ─────────────────────────────────────────────

  async reassignJob(assignmentId: string, dto: ReassignJobDto, userId: string, userRole?: string, roleSlug?: string, userPermissions?: Set<string>) {
    if (!dto.vehicleId && !dto.supplierCarTypeId && !dto.driverId && !dto.repId
        && dto.externalDriverName === undefined && dto.externalDriverPhone === undefined
        && dto.remarks === undefined) {
      throw new BadRequestException(
        'At least one field must be provided',
      );
    }

    // Permission-based field validation
    if (userPermissions) {
      const canVehicle = userPermissions.has('dispatch.assignment.assignVehicle');
      const canDriver = userPermissions.has('dispatch.assignment.assignDriver');
      const canRep = userPermissions.has('dispatch.assignment.assignRep');

      if (dto.vehicleId && !canVehicle) {
        throw new ForbiddenException('You do not have permission to assign vehicles');
      }
      if (dto.driverId && !canDriver) {
        throw new ForbiddenException('You do not have permission to assign drivers');
      }
      if (dto.repId && !canRep) {
        throw new ForbiddenException('You do not have permission to assign reps');
      }
      // A supplier car is a vehicle choice; an external driver is a driver choice.
      // Gate them the same way assignJob does (was missing on reassign).
      if (dto.supplierCarTypeId && !canVehicle) {
        throw new ForbiddenException('You do not have permission to assign vehicles');
      }
      if (
        (dto.externalDriverName !== undefined || dto.externalDriverPhone !== undefined) &&
        !canDriver
      ) {
        throw new ForbiddenException('You do not have permission to assign drivers');
      }
    }

    const existing = await this.prisma.trafficAssignment.findUnique({
      where: { id: assignmentId },
      include: {
        trafficJob: { include: { flight: true, originAirport: true, originZone: true, originHotel: true, destinationAirport: true, destinationZone: true, destinationHotel: true } },
        vehicle: { include: { vehicleType: true } },
      },
    });

    if (!existing) {
      throw new NotFoundException(
        `Assignment with ID "${assignmentId}" not found`,
      );
    }

    const job = existing.trafficJob;

    // Dispatcher 48-hour lock (skip if job was explicitly unlocked)
    this.checkDispatcherTimelock(job.jobDate, userRole, roleSlug, job.dispatchUnlockedAt);

    // Vehicle validation
    if (dto.vehicleId) {
      const vehicle = await this.prisma.vehicle.findFirst({
        where: { id: dto.vehicleId, deletedAt: null, isActive: true },
        include: { vehicleType: true },
      });

      if (!vehicle) {
        throw new NotFoundException(
          `Vehicle with ID "${dto.vehicleId}" not found or inactive`,
        );
      }

      if (job.paxCount > vehicle.vehicleType.seatCapacity) {
        throw new BadRequestException(
          `Pax count (${job.paxCount}) exceeds vehicle capacity (${vehicle.vehicleType.seatCapacity})`,
        );
      }

      // Vehicle type mismatch check (requested vs assigned)
      if (
        job.requestedVehicleTypeId &&
        vehicle.vehicleTypeId !== job.requestedVehicleTypeId &&
        !dto.allowTypeMismatch
      ) {
        const requestedType = await this.prisma.vehicleType.findUnique({
          where: { id: job.requestedVehicleTypeId },
          select: { name: true },
        });
        throw new ConflictException(
          `Vehicle type mismatch: requested "${requestedType?.name || 'Unknown'}", got "${vehicle.vehicleType.name}"`,
        );
      }

      await this.validateVehicleAvailability(dto.vehicleId, job, assignmentId);
    }

    // Driver validation with time-aware rules
    if (dto.driverId) {
      const driver = await this.prisma.driver.findFirst({
        where: { id: dto.driverId, deletedAt: null, isActive: true },
      });
      if (!driver) {
        throw new NotFoundException(
          `Driver with ID "${dto.driverId}" not found or inactive`,
        );
      }
      await this.validateDriverAvailability(dto.driverId, job, assignmentId);
    }

    // Rep validation
    if (dto.repId) {
      const rep = await this.prisma.rep.findFirst({
        where: { id: dto.repId, deletedAt: null, isActive: true },
      });
      if (!rep) {
        throw new NotFoundException(
          `Rep with ID "${dto.repId}" not found or inactive`,
        );
      }
      await this.validateRepAvailability(dto.repId, job, assignmentId);
    }

    // Validate supplier car type for reassign and resolve supplierId
    let reassignSupplierId: string | null | undefined = dto.supplierId;
    if (dto.supplierCarTypeId) {
      const carType = await this.prisma.supplierCarType.findFirst({
        where: { id: dto.supplierCarTypeId },
        include: { vehicleType: true },
      });
      if (!carType) {
        throw new NotFoundException(`Supplier car type with ID "${dto.supplierCarTypeId}" not found`);
      }
      // Pax count must not exceed the supplier car's capacity (same rule as own vehicles).
      if (job.paxCount > carType.vehicleType.seatCapacity) {
        throw new BadRequestException(
          `Pax count (${job.paxCount}) exceeds vehicle capacity (${carType.vehicleType.seatCapacity})`,
        );
      }
      reassignSupplierId = carType.supplierId;
    }

    const updateData: Record<string, unknown> = {};
    // Mutual exclusion: an assignment's car is either OWN (vehicle) or SUPPLIER
    // (supplier car type), never both. Whichever side is chosen clears the other,
    // so Car Source stays unambiguous (Supplier = supplierId set AND no own vehicle).
    if (dto.supplierCarTypeId) {
      // Switching to a supplier car type → clear own vehicle & own driver.
      updateData.supplierCarTypeId = dto.supplierCarTypeId;
      updateData.supplierId = reassignSupplierId ?? null;
      updateData.vehicleId = null;
      if (existing.driverId) {
        updateData.driverId = null;
        updateData.driverStatus = 'PENDING';
      }
    } else if (dto.vehicleId) {
      // Switching to an own vehicle → clear supplier car type, supplier & external driver.
      updateData.vehicleId = dto.vehicleId;
      updateData.supplierCarTypeId = null;
      updateData.supplierId = null;
      updateData.externalDriverName = null;
      updateData.externalDriverPhone = null;
    } else {
      // No car-source switch in this update — apply any explicit clears as sent.
      if (dto.vehicleId !== undefined) updateData.vehicleId = dto.vehicleId;
      if (dto.supplierCarTypeId !== undefined) {
        updateData.supplierCarTypeId = dto.supplierCarTypeId;
        updateData.supplierId = reassignSupplierId ?? null;
      }
      if (dto.supplierId !== undefined) updateData.supplierId = dto.supplierId;
    }
    if (dto.driverId !== undefined) {
      updateData.driverId = dto.driverId;
      if (dto.driverId !== existing.driverId) {
        updateData.driverStatus = 'PENDING';
      }
    }
    if (dto.repId !== undefined) {
      updateData.repId = dto.repId;
      if (dto.repId !== existing.repId) {
        updateData.repStatus = 'PENDING';
      }
    }
    if (dto.externalDriverName !== undefined) updateData.externalDriverName = dto.externalDriverName || null;
    if (dto.externalDriverPhone !== undefined) updateData.externalDriverPhone = dto.externalDriverPhone || null;
    if (dto.remarks !== undefined) updateData.remarks = dto.remarks || null;

    const updated = await this.prisma.$transaction(async (tx) => {
      const result = await tx.trafficAssignment.update({
        where: { id: assignmentId },
        data: updateData,
        include: {
          vehicle: { include: { vehicleType: true } },
          driver: true,
          rep: true,
          supplier: { select: { id: true, legalName: true, tradeName: true } },
          supplierCarType: { include: { vehicleType: true } },
          trafficJob: true,
        },
      });

      if (dto.repId && dto.repId !== existing.repId) {
        await tx.repNotification.create({
          data: {
            repId: dto.repId,
            title: 'New Job Assigned',
            message: `${result.trafficJob.internalRef} - ${result.trafficJob.serviceType} on ${result.trafficJob.jobDate.toISOString().split('T')[0]}`,
            type: 'JOB_ASSIGNED',
            trafficJobId: result.trafficJobId,
          },
        });
      }

      if (dto.driverId && dto.driverId !== existing.driverId) {
        await tx.driverNotification.create({
          data: {
            driverId: dto.driverId,
            title: 'New Job Assigned',
            message: `${result.trafficJob.internalRef} - ${result.trafficJob.serviceType} on ${result.trafficJob.jobDate.toISOString().split('T')[0]}`,
            type: 'JOB_ASSIGNED',
            trafficJobId: result.trafficJobId,
          },
        });
      }

      return result;
    });

    // Push notifications (fire-and-forget)
    if (dto.driverId && dto.driverId !== existing.driverId) {
      this.pushService.sendToDriver(
        dto.driverId,
        'New Job Assigned',
        `${updated.trafficJob.internalRef} - ${updated.trafficJob.serviceType}`,
        { jobId: updated.trafficJobId, type: 'JOB_ASSIGNED' },
      ).catch(() => {});
    }
    if (dto.repId && dto.repId !== existing.repId) {
      this.pushService.sendToRep(
        dto.repId,
        'New Job Assigned',
        `${updated.trafficJob.internalRef} - ${updated.trafficJob.serviceType}`,
        { jobId: updated.trafficJobId, type: 'JOB_ASSIGNED' },
      ).catch(() => {});
    }

    // WhatsApp: trigger driver assigned on reassignment (fire-and-forget)
    if (dto.driverId && dto.driverId !== existing.driverId) {
      this.whatsappService.triggerDriverAssigned(updated.trafficJobId).catch(() => {});
    }

    // Staff-assignment email: fire only on the transition to BOTH driver and
    // rep being assigned — i.e. when this reassignment completes the pair.
    // This means whoever is assigned second triggers it, and it won't re-fire
    // on later edits once the pair is already complete.
    const wasComplete = !!(existing.driverId && existing.repId);
    const isComplete = !!(updated.driverId && updated.repId);
    if (!wasComplete && isComplete && updated.driver && updated.rep) {
      this.sendStaffAssignmentEmail(
        updated.trafficJobId,
        updated.driver,
        updated.rep,
        updated.vehicle,
      ).catch((err) =>
        this.logger.error(`Failed to send staff assignment email: ${err.message}`),
      );
    }

    // Notify online users about the reassignment (fire-and-forget)
    this.notificationsService.notifyDispatchAction(
      updated.trafficJobId,
      userId,
      'REASSIGNED',
      {
        vehiclePlate: updated.vehicle?.plateNumber,
        driverName: updated.driver?.name ?? undefined,
        repName: updated.rep?.name ?? undefined,
      },
    ).catch((err) => this.logger.error(`Failed to send dispatch notification: ${err.message}`));

    // Non-blocking heads-up on the newly-assigned vehicle/driver (exclude self).
    const warnings = await this.detectAssignmentConflicts(job, {
      vehicleId: dto.vehicleId ?? null,
      driverId: dto.driverId ?? null,
      excludeAssignmentId: assignmentId,
    });
    return warnings.length ? { ...updated, warnings } : updated;
  }

  // ─────────────────────────────────────────────
  // UNASSIGN JOB
  // ─────────────────────────────────────────────

  async unassignJob(assignmentId: string, userId: string, userRole?: string, roleSlug?: string) {
    const assignment = await this.prisma.trafficAssignment.findUnique({
      where: { id: assignmentId },
      include: { trafficJob: true },
    });

    if (!assignment) {
      throw new NotFoundException(
        `Assignment with ID "${assignmentId}" not found`,
      );
    }

    // Dispatcher 48-hour lock (skip if job was explicitly unlocked)
    this.checkDispatcherTimelock(assignment.trafficJob.jobDate, userRole, roleSlug, assignment.trafficJob.dispatchUnlockedAt);

    await this.prisma.$transaction(async (tx) => {
      await tx.trafficAssignment.delete({
        where: { id: assignmentId },
      });

      await tx.trafficJob.update({
        where: { id: assignment.trafficJobId },
        data: { status: 'PENDING' as JobStatus },
      });
    });

    // Notify online users about the unassignment (fire-and-forget)
    this.notificationsService.notifyDispatchAction(
      assignment.trafficJobId,
      userId,
      'UNASSIGNED',
      {},
    ).catch((err) => this.logger.error(`Failed to send dispatch notification: ${err.message}`));

    return { message: 'Assignment removed successfully' };
  }

  // ─────────────────────────────────────────────
  // AVAILABLE RESOURCES
  // ─────────────────────────────────────────────

  async getAvailableVehicles(date: string, supplierId?: string, q?: string) {
    const jobDate = new Date(date);

    const busyAssignments = await this.prisma.trafficAssignment.findMany({
      where: {
        trafficJob: {
          jobDate,
          deletedAt: null,
          status: { notIn: ['CANCELLED', 'COMPLETED'] as JobStatus[] },
        },
      },
      select: { vehicleId: true },
    });

    const busyVehicleIds = new Set(
      busyAssignments.map((a) => a.vehicleId).filter((id): id is string => id !== null),
    );

    // Owned vehicles (no supplierId)
    const ownedVehicles = await this.prisma.vehicle.findMany({
      where: { deletedAt: null, isActive: true, supplierId: null },
      include: { vehicleType: true, supplier: { select: { id: true, legalName: true, tradeName: true } } },
      orderBy: [{ plateNumber: 'asc' }],
    });

    // Supplier car types — each becomes a virtual vehicle entry
    const carTypes = await this.prisma.supplierCarType.findMany({
      where: { supplier: { deletedAt: null, isActive: true } },
      include: {
        vehicleType: true,
        supplier: { select: { id: true, legalName: true, tradeName: true } },
      },
      orderBy: [{ supplier: { legalName: 'asc' } }],
    });

    const vehicleResults = ownedVehicles.map((v) => ({
      ...v,
      isCarType: false,
      isBusy: busyVehicleIds.has(v.id),
    }));

    const carTypeResults = carTypes.map((ct) => ({
      id: ct.id,
      plateNumber: ct.vehicleType.name,
      vehicleTypeId: ct.vehicleTypeId,
      vehicleType: ct.vehicleType,
      supplierId: ct.supplierId,
      supplier: ct.supplier,
      isCarType: true,
      isBusy: false,
      ownership: 'SUPPLIER' as const,
      color: null,
      carBrand: null,
      carModel: null,
      makeYear: null,
      luggageCapacity: null,
      isActive: true,
      createdAt: ct.createdAt,
      updatedAt: ct.createdAt,
      deletedAt: null,
    }));

    const all = [...vehicleResults, ...carTypeResults];
    if (!q) return all;
    const lower = q.toLowerCase();
    return all.filter(
      (v) =>
        v.plateNumber?.toLowerCase().includes(lower) ||
        v.vehicleType?.name?.toLowerCase().includes(lower) ||
        (v as any).supplier?.legalName?.toLowerCase().includes(lower),
    );
  }

  async getAvailableSuppliers() {
    const suppliers = await this.prisma.supplier.findMany({
      where: {
        deletedAt: null,
        isActive: true,
        OR: [
          { vehicles: { some: { deletedAt: null, isActive: true } } },
          { carTypes: { some: {} } },
        ],
      },
      select: {
        id: true,
        legalName: true,
        tradeName: true,
        _count: {
          select: {
            vehicles: {
              where: { deletedAt: null, isActive: true },
            },
            carTypes: true,
          },
        },
      },
      orderBy: { legalName: 'asc' },
    });

    return suppliers.map((s) => ({
      id: s.id,
      legalName: s.legalName,
      tradeName: s.tradeName,
      vehicleCount: s._count.vehicles,
      carTypeCount: s._count.carTypes,
    }));
  }

  /**
   * Returns all active drivers, optionally filtered by supplier.
   * No time-based restrictions — drivers can be freely assigned.
   */
  async getAvailableDrivers(date: string, jobId?: string, supplierId?: string, q?: string) {
    const supplierFilter = supplierId === 'owned'
      ? { supplierId: null }
      : supplierId
        ? { supplierId }
        : {};

    return this.prisma.driver.findMany({
      where: {
        deletedAt: null,
        isActive: true,
        ...supplierFilter,
        ...(q ? { name: { contains: q, mode: 'insensitive' as const } } : {}),
      },
      include: { supplier: { select: { id: true, legalName: true, tradeName: true } } },
      orderBy: { name: 'asc' },
      take: q ? 20 : undefined,
    });
  }

  /**
   * Flight-aware rep availability. Returns reps that can work the target job
   * based on same-flight sharing rules.
   * Returns empty for non-ARR/DEP jobs (rep assignment only for Arrival/Departure).
   */
  async getAvailableReps(date: string, jobId?: string, q?: string) {
    const jobDate = new Date(date);

    if (!jobId) {
      return this.prisma.rep.findMany({
        where: {
          deletedAt: null,
          isActive: true,
          ...(q ? { name: { contains: q, mode: 'insensitive' as const } } : {}),
        },
        orderBy: { name: 'asc' },
        take: q ? 20 : undefined,
      });
    }

    const targetJob = await this.prisma.trafficJob.findFirst({
      where: { id: jobId, deletedAt: null },
      include: { flight: true },
    });

    if (!targetJob) return [];

    const targetFlight = targetJob.flight;
    const targetTime = this.getJobReferenceTime(targetJob);

    // Get all active rep assignments on this date
    const busyAssignments = await this.prisma.trafficAssignment.findMany({
      where: {
        repId: { not: null },
        trafficJob: {
          jobDate,
          deletedAt: null,
          status: { notIn: ['CANCELLED', 'COMPLETED'] as JobStatus[] },
        },
      },
      include: {
        trafficJob: { include: { flight: true } },
      },
    });

    // Group by rep
    const repAssignments = new Map<string, typeof busyAssignments>();
    for (const a of busyAssignments) {
      if (!a.repId) continue;
      const list = repAssignments.get(a.repId) || [];
      list.push(a);
      repAssignments.set(a.repId, list);
    }

    const busyRepIds: string[] = [];
    for (const [repId, assignments] of repAssignments) {
      let blocked = false;
      for (const a of assignments) {
        const existingFlight = a.trafficJob.flight;
        const existingTime = this.getJobReferenceTime(a.trafficJob);

        // Same flight check: same flightNo AND same time → allowed
        if (
          targetFlight &&
          existingFlight &&
          targetFlight.flightNo === existingFlight.flightNo &&
          targetTime &&
          existingTime &&
          targetTime.getTime() === existingTime.getTime()
        ) {
          continue;
        }

        // Different flight: always allowed (no time gap restriction)
      }
      if (blocked) busyRepIds.push(repId);
    }

    return this.prisma.rep.findMany({
      where: {
        deletedAt: null,
        isActive: true,
        ...(busyRepIds.length > 0 && {
          id: { notIn: busyRepIds },
        }),
      },
      orderBy: { name: 'asc' },
    });
  }

  // ─────────────────────────────────────────────
  // PRIVATE HELPERS
  // ─────────────────────────────────────────────

  // ─────────────────────────────────────────────
  // UNLOCK / LOCK JOB (48-hour override)
  // ─────────────────────────────────────────────

  async unlockJob(jobId: string, userId: string) {
    const job = await this.prisma.trafficJob.findFirst({
      where: { id: jobId, deletedAt: null },
    });
    if (!job) {
      throw new NotFoundException(`Traffic job with ID "${jobId}" not found`);
    }
    return this.prisma.trafficJob.update({
      where: { id: jobId },
      data: {
        dispatchUnlockedAt: new Date(),
        dispatchUnlockedById: userId,
      },
    });
  }

  async lockJob(jobId: string) {
    const job = await this.prisma.trafficJob.findFirst({
      where: { id: jobId, deletedAt: null },
    });
    if (!job) {
      throw new NotFoundException(`Traffic job with ID "${jobId}" not found`);
    }
    return this.prisma.trafficJob.update({
      where: { id: jobId },
      data: {
        dispatchUnlockedAt: null,
        dispatchUnlockedById: null,
      },
    });
  }

  /**
   * Dispatchers cannot modify assignments after 48 hours from the service date,
   * unless the job has been explicitly unlocked by an authorized user.
   * Admins and Managers bypass this restriction.
   */
  private checkDispatcherTimelock(
    jobDate: Date,
    userRole?: string,
    roleSlug?: string,
    dispatchUnlockedAt?: Date | null,
  ) {
    const isDispatcher =
      userRole === 'DISPATCHER' || roleSlug === 'dispatcher';
    if (!isDispatcher) return;

    // Skip if job was explicitly unlocked
    if (dispatchUnlockedAt) return;

    const cutoff = new Date(jobDate.getTime() + FORTY_EIGHT_HOURS_MS);
    if (new Date() > cutoff) {
      throw new ForbiddenException(
        'Dispatchers cannot modify assignments more than 48 hours after the service date.',
      );
    }
  }

  /**
   * Get the reference time for a job.
   * ARR → arrivalTime, DEP → pickUpTime or departureTime, excursion/transfer → pickUpTime.
   */
  private getJobReferenceTime(
    job: { serviceType: string; pickUpTime?: Date | null; flight?: { arrivalTime?: Date | null; departureTime?: Date | null } | null },
  ): Date | null {
    if (job.serviceType === 'ARR' && job.flight?.arrivalTime) {
      return new Date(job.flight.arrivalTime);
    }
    if (job.serviceType === 'DEP') {
      if (job.pickUpTime) return new Date(job.pickUpTime);
      if (job.flight?.departureTime) return new Date(job.flight.departureTime);
    }
    // Excursion / transfer jobs use pickUpTime
    if (job.pickUpTime) return new Date(job.pickUpTime);
    return null;
  }

  // Vehicle availability — no time restrictions, free assignment allowed.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  private async validateVehicleAvailability(
    _vehicleId: string,
    _job: Record<string, unknown>,
    _excludeAssignmentId?: string,
  ) {
    return;
  }

  /**
   * Non-blocking conflict detection for vehicle/driver double-booking: returns a
   * warning per resource already assigned to another active job at the same
   * reference time (same-flight excepted). Vehicle/driver overlap is allowed
   * (a car can do ARR then DEP the same day) — dispatch just gets a heads-up.
   */
  private async detectAssignmentConflicts(
    job: {
      id: string;
      jobDate: Date;
      serviceType: string;
      pickUpTime?: Date | null;
      flight?: { flightNo?: string; arrivalTime?: Date | null; departureTime?: Date | null } | null;
    },
    opts: { vehicleId?: string | null; driverId?: string | null; excludeAssignmentId?: string },
  ): Promise<string[]> {
    const targetTime = this.getJobReferenceTime(job);
    if (!targetTime) return [];
    const targetFlightNo = job.flight?.flightNo;
    const warnings: string[] = [];

    const check = async (field: 'vehicleId' | 'driverId', id: string, label: string) => {
      const existing = await this.prisma.trafficAssignment.findMany({
        where: {
          [field]: id,
          ...(opts.excludeAssignmentId ? { id: { not: opts.excludeAssignmentId } } : {}),
          trafficJob: {
            jobDate: job.jobDate,
            deletedAt: null,
            status: { notIn: ['CANCELLED', 'COMPLETED'] as JobStatus[] },
          },
        },
        include: { trafficJob: { include: { flight: true } } },
      });
      for (const a of existing) {
        const t = this.getJobReferenceTime(a.trafficJob);
        if (!t || t.getTime() !== targetTime.getTime()) continue;
        const existingFlightNo = a.trafficJob.flight?.flightNo;
        if (targetFlightNo && existingFlightNo && targetFlightNo === existingFlightNo) continue;
        warnings.push(`${label} is already assigned to job ${a.trafficJob.internalRef} at the same time.`);
      }
    };

    if (opts.vehicleId) await check('vehicleId', opts.vehicleId, 'Vehicle');
    if (opts.driverId) await check('driverId', opts.driverId, 'Driver');
    return warnings;
  }

  // Driver availability — no time restrictions, free assignment allowed.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  private async validateDriverAvailability(
    _driverId: string,
    _job: Record<string, unknown>,
    _excludeAssignmentId?: string,
  ) {
    return;
  }

  /**
   * Validate rep availability with time-aware rules.
   *
   * ARR/DEP (flight jobs):
   *   - Same flightNo + same reference time → allowed (one rep, multiple pax on same flight).
   *   - Different flight at same time → conflict.
   *   - Different flight at different time → allowed.
   *
   * Excursion / transfer jobs (DAY_TOUR, ONE_WAY_TRANSFER, RETURN, …):
   *   - Same pickUpTime as any existing job → conflict.
   *   - Different pickUpTime → allowed.
   */
  private async validateRepAvailability(
    repId: string,
    job: { id: string; jobDate: Date; serviceType: string; pickUpTime?: Date | null; flight?: { flightNo?: string; arrivalTime?: Date | null; departureTime?: Date | null } | null },
    excludeAssignmentId?: string,
  ) {
    const existingAssignments = await this.prisma.trafficAssignment.findMany({
      where: {
        repId,
        ...(excludeAssignmentId ? { id: { not: excludeAssignmentId } } : {}),
        trafficJob: {
          jobDate: job.jobDate,
          deletedAt: null,
          status: { notIn: ['CANCELLED', 'COMPLETED'] as JobStatus[] },
        },
      },
      include: {
        trafficJob: { include: { flight: true } },
      },
    });

    if (existingAssignments.length === 0) return;

    const targetFlight = job.flight;
    const targetTime = this.getJobReferenceTime(job);

    // If target job has no reference time, no conflict possible
    if (!targetTime) return;

    for (const a of existingAssignments) {
      const existingFlight = a.trafficJob.flight;
      const existingTime = this.getJobReferenceTime(a.trafficJob);

      if (!existingTime) continue;
      if (targetTime.getTime() !== existingTime.getTime()) continue;

      // Same time — check same-flight exception (applies to ARR/DEP only)
      if (
        targetFlight?.flightNo &&
        existingFlight?.flightNo &&
        targetFlight.flightNo === existingFlight.flightNo
      ) {
        continue; // same flight, allowed
      }

      throw new ConflictException(
        `Rep is already assigned to job ${a.trafficJob.internalRef} at the same time.`,
      );
    }
  }
}
