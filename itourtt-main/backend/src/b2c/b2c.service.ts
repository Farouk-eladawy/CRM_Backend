import {
  Injectable,
  UnauthorizedException,
  NotFoundException,
  BadRequestException,
  Logger,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';
import * as bcrypt from 'bcryptjs';
import * as crypto from 'crypto';
import { PrismaService } from '../prisma/prisma.service.js';
import { EmailService } from '../email/email.service.js';
import { GoogleDriveService, isDriveFileId } from '../google-drive/google-drive.service.js';
import { B2CLoginDto, B2CChangePasswordDto, B2CAmendBookingDto } from './dto/b2c.dto.js';

// Evidence relations on the linked traffic job, exposed to the guest so they can
// follow up on no-show / delay / dispute. One row per submitter (driver/rep).
const EVIDENCE_SELECT = {
  select: { imageUrls: true, gpsMapLink: true, submittedBy: true, createdAt: true },
} as const;

// Stages shown to the guest, in chronological order.
const EVIDENCE_STAGES = [
  ['inPlaceEvidence', 'IN_PLACE'],
  ['inProgressEvidence', 'IN_PROGRESS'],
  ['completedEvidence', 'COMPLETED'],
  ['noShowEvidence', 'NO_SHOW'],
] as const;

@Injectable()
export class B2CService {
  private readonly logger = new Logger(B2CService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly jwtService: JwtService,
    private readonly configService: ConfigService,
    private readonly emailService: EmailService,
    private readonly googleDriveService: GoogleDriveService,
  ) {}

  async ensureB2CClientAccount(email: string, phone: string, name: string) {
    const existing = await this.prisma.user.findFirst({
      where: { email, role: 'B2C_CLIENT' as any },
    });
    if (existing) return { user: existing, isNew: false };

    const passwordHash = await bcrypt.hash(phone, 10);
    const user = await this.prisma.user.create({
      data: {
        email,
        name,
        passwordHash,
        role: 'B2C_CLIENT' as any,
        isActive: true,
      },
    });
    return { user, isNew: true, rawPassword: phone };
  }

  async login(dto: B2CLoginDto) {
    const user = await this.prisma.user.findFirst({
      where: { email: dto.email, role: 'B2C_CLIENT' as any, isActive: true },
    });
    if (!user) throw new UnauthorizedException('Invalid credentials');

    const valid = await bcrypt.compare(dto.phone, user.passwordHash ?? '');
    if (!valid) throw new UnauthorizedException('Invalid credentials');

    const payload = { sub: user.id, role: user.role, email: user.email };
    const secret = this.configService.get<string>('JWT_SECRET');
    const token = this.jwtService.sign(payload, { secret, expiresIn: '30d' });

    return {
      token,
      user: { id: user.id, name: user.name, email: user.email },
    };
  }

  async changePassword(clientId: string, dto: B2CChangePasswordDto) {
    const user = await this.prisma.user.findUnique({ where: { id: clientId } });
    if (!user) throw new NotFoundException('Account not found');

    const valid = await bcrypt.compare(dto.currentPassword, user.passwordHash ?? '');
    if (!valid) throw new BadRequestException('Current password is incorrect');

    const passwordHash = await bcrypt.hash(dto.newPassword, 10);
    await this.prisma.user.update({ where: { id: clientId }, data: { passwordHash } });
    return { success: true };
  }

  /**
   * Email a password-reset link to a guest. Mirrors the staff flow in
   * auth.service.ts but scoped to B2C_CLIENT users and links to the B2C site.
   * Always returns success to avoid leaking which emails exist.
   */
  async requestPasswordReset(email: string) {
    const user = await this.prisma.user.findFirst({
      where: { email, role: 'B2C_CLIENT' as any, isActive: true, deletedAt: null },
    });
    if (!user) return { success: true };

    const rawToken = crypto.randomBytes(32).toString('hex');
    const tokenHash = crypto.createHash('sha256').update(rawToken).digest('hex');
    const expiry = new Date(Date.now() + 30 * 60 * 1000); // 30 minutes

    await this.prisma.user.update({
      where: { id: user.id },
      data: { passwordResetToken: tokenHash, passwordResetExpiry: expiry },
    });

    const siteUrl = this.configService
      .get<string>('B2C_SITE_URL', 'https://transfera.ae')
      .replace(/\/+$/, '');
    const resetLink = `${siteUrl}/reset-password?token=${rawToken}&email=${encodeURIComponent(email)}`;

    const html = `
      <h2>Reset your password</h2>
      <p>Hi ${user.name},</p>
      <p>You requested a password reset. Click the button below to set a new password. This link expires in 30 minutes.</p>
      <p><a href="${resetLink}" style="background:#191919;color:#fff;padding:10px 20px;text-decoration:none;border-radius:6px;display:inline-block;">Reset Password</a></p>
      <p>If you didn't request this, you can safely ignore this email.</p>
    `;
    await (this.emailService as any)
      .send(email, 'Reset your password', html)
      .catch((err: Error) => this.logger.warn(`Failed to send B2C reset email: ${err.message}`));

    return { success: true };
  }

  async resetPassword(email: string, rawToken: string, newPassword: string) {
    if (!newPassword || newPassword.length < 8) {
      throw new BadRequestException('Password must be at least 8 characters');
    }

    const user = await this.prisma.user.findFirst({
      where: { email, role: 'B2C_CLIENT' as any },
    });
    if (!user || !user.passwordResetToken || !user.passwordResetExpiry) {
      throw new BadRequestException('Invalid or expired reset link');
    }
    if (new Date() > user.passwordResetExpiry) {
      throw new BadRequestException('Reset link has expired');
    }
    const tokenHash = crypto.createHash('sha256').update(rawToken).digest('hex');
    if (tokenHash !== user.passwordResetToken) {
      throw new BadRequestException('Invalid or expired reset link');
    }

    const passwordHash = await bcrypt.hash(newPassword, 10);
    await this.prisma.user.update({
      where: { id: user.id },
      data: { passwordHash, passwordResetToken: null, passwordResetExpiry: null },
    });
    return { success: true };
  }

  async getBookings(clientId: string) {
    return this.prisma.guestBooking.findMany({
      where: { b2cClientId: clientId },
      orderBy: { createdAt: 'desc' },
      include: {
        fromZone: { select: { id: true, name: true } },
        toZone: { select: { id: true, name: true } },
        originAirport: { select: { id: true, name: true } },
        destinationAirport: { select: { id: true, name: true } },
        hotel: { select: { id: true, name: true } },
        vehicleType: { select: { id: true, name: true } },
        trafficJob: {
          select: {
            id: true,
            internalRef: true,
            status: true,
            assignment: {
              select: {
                vehicle: { select: { plateNumber: true, carBrand: true, carModel: true } },
                driver: { select: { name: true, mobileNumber: true } },
                rep: { select: { name: true, mobileNumber: true } },
                // Supplier (non-"Own") source: the car is a supplier car type and
                // the driver is an external driver, so the relations above are null.
                externalDriverName: true,
                externalDriverPhone: true,
                supplierCarType: { select: { vehicleType: { select: { name: true } } } },
              },
            },
          },
        },
      },
    });
  }

  async getBooking(clientId: string, ref: string) {
    const booking = await this.prisma.guestBooking.findFirst({
      where: { bookingRef: ref, b2cClientId: clientId },
      include: {
        fromZone: { select: { id: true, name: true } },
        toZone: { select: { id: true, name: true } },
        originAirport: { select: { id: true, name: true } },
        destinationAirport: { select: { id: true, name: true } },
        hotel: { select: { id: true, name: true } },
        vehicleType: { select: { id: true, name: true } },
        // Invoice (if the booking has been paid) for the Payment tab download.
        invoice: {
          select: {
            id: true, invoiceNumber: true, total: true,
            currency: true, status: true, issuedAt: true,
          },
        },
        trafficJob: {
          select: {
            id: true,
            internalRef: true,
            status: true,
            assignment: {
              select: {
                vehicle: { select: { plateNumber: true, carBrand: true, carModel: true } },
                driver: { select: { name: true, mobileNumber: true } },
                rep: { select: { name: true, mobileNumber: true } },
                // Supplier (non-"Own") source: the car is a supplier car type and
                // the driver is an external driver, so the relations above are null.
                externalDriverName: true,
                externalDriverPhone: true,
                supplierCarType: { select: { vehicleType: { select: { name: true } } } },
              },
            },
            flight: { select: { flightNo: true, carrier: true, terminal: true } },
            inPlaceEvidence: EVIDENCE_SELECT,
            inProgressEvidence: EVIDENCE_SELECT,
            completedEvidence: EVIDENCE_SELECT,
            noShowEvidence: EVIDENCE_SELECT,
          },
        },
      },
    });
    if (!booking) throw new NotFoundException('Booking not found');

    return { ...booking, evidence: this.buildEvidence(ref, booking.trafficJob) };
  }

  // Flatten the per-stage evidence relations into a single chronological list,
  // rewriting each stored image (a Drive file id or a local /uploads path) into a
  // URL the guest can fetch via the ownership-scoped proxy below.
  private buildEvidence(ref: string, job: any) {
    if (!job) return [];
    const items: Array<{
      stage: string;
      by: 'DRIVER' | 'REP' | 'STAFF';
      gpsMapLink: string | null;
      createdAt: Date;
      images: string[];
    }> = [];

    for (const [relation, stage] of EVIDENCE_STAGES) {
      for (const ev of (job[relation] ?? []) as Array<{
        imageUrls: string[];
        gpsMapLink: string | null;
        submittedBy: string;
        createdAt: Date;
      }>) {
        // submittedBy is stored as "DRIVER-<name>" / "REP-<name>"; expose only the
        // role to the guest, never the staff member's name.
        const role = (ev.submittedBy ?? '').startsWith('REP')
          ? 'REP'
          : (ev.submittedBy ?? '').startsWith('DRIVER')
            ? 'DRIVER'
            : 'STAFF';
        items.push({
          stage,
          by: role,
          gpsMapLink: ev.gpsMapLink,
          createdAt: ev.createdAt,
          images: (ev.imageUrls ?? []).map((url) =>
            isDriveFileId(url)
              ? `/w-api/bookings/${encodeURIComponent(ref)}/evidence-file/${url}`
              : url,
          ),
        });
      }
    }

    return items.sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime());
  }

  // Stream a single evidence image to the guest. The file id MUST belong to the
  // evidence of a job the guest owns — otherwise this would be an open Drive proxy.
  async getEvidenceFileStream(clientId: string, ref: string, fileId: string) {
    if (!isDriveFileId(fileId)) throw new NotFoundException('File not found');

    const booking = await this.prisma.guestBooking.findFirst({
      where: { bookingRef: ref, b2cClientId: clientId },
      select: {
        trafficJob: {
          select: {
            inPlaceEvidence: { select: { imageUrls: true } },
            inProgressEvidence: { select: { imageUrls: true } },
            completedEvidence: { select: { imageUrls: true } },
            noShowEvidence: { select: { imageUrls: true } },
          },
        },
      },
    });

    const job: any = booking?.trafficJob;
    if (!job) throw new NotFoundException('File not found');

    const ownedIds = new Set<string>();
    for (const [relation] of EVIDENCE_STAGES) {
      for (const ev of (job[relation] ?? []) as Array<{ imageUrls: string[] }>) {
        for (const url of ev.imageUrls ?? []) ownedIds.add(url);
      }
    }
    if (!ownedIds.has(fileId)) throw new NotFoundException('File not found');

    const result = await this.googleDriveService.getFileStream(fileId);
    if (!result) throw new NotFoundException('File not found or Drive not configured');
    return result;
  }

  async amendBooking(clientId: string, ref: string, dto: B2CAmendBookingDto) {
    const booking = await this.prisma.guestBooking.findFirst({
      where: { bookingRef: ref, b2cClientId: clientId },
    });
    if (!booking) throw new NotFoundException('Booking not found');

    if (!['CONFIRMED', 'CONVERTED'].includes(booking.bookingStatus)) {
      throw new BadRequestException(`Cannot amend a booking with status ${booking.bookingStatus}`);
    }

    const jobDateTime = new Date(booking.jobDate);
    if (booking.pickupTime) {
      const pt = booking.pickupTime;
      jobDateTime.setHours(pt.getHours(), pt.getMinutes(), 0, 0);
    }
    const hoursUntilJob = (jobDateTime.getTime() - Date.now()) / 3_600_000;
    if (hoursUntilJob < 24) {
      throw new BadRequestException('Amendments must be made at least 24 hours before the job');
    }

    const updateData: Record<string, any> = { amendedAt: new Date() };
    if (dto.jobDate) updateData.jobDate = new Date(dto.jobDate);
    if (dto.pickupTime) {
      const dateStr = dto.jobDate ?? booking.jobDate.toISOString().split('T')[0];
      updateData.pickupTime = new Date(`${dateStr}T${dto.pickupTime}:00`);
    }
    if (dto.paxCount !== undefined) updateData.paxCount = dto.paxCount;

    const updated = await this.prisma.guestBooking.update({
      where: { id: booking.id },
      data: updateData,
      include: { fromZone: true, toZone: true, vehicleType: true, hotel: true },
    });

    if (booking.trafficJobId) {
      const jobUpdate: Record<string, any> = {};
      if (dto.jobDate) jobUpdate.jobDate = updateData.jobDate;
      if (dto.pickupTime) jobUpdate.pickUpTime = updateData.pickupTime;
      if (dto.paxCount !== undefined) {
        jobUpdate.paxCount = dto.paxCount;
        jobUpdate.adultCount = dto.paxCount;
      }
      if (Object.keys(jobUpdate).length > 0) {
        await this.prisma.trafficJob.update({
          where: { id: booking.trafficJobId },
          data: jobUpdate,
        });
      }
    }

    // Internal ops notification (additive — recipients configured in admin CMS).
    const changes: string[] = [];
    if (dto.jobDate) changes.push(`Date → ${dto.jobDate}`);
    if (dto.pickupTime) changes.push(`Pickup time → ${dto.pickupTime}`);
    if (dto.paxCount !== undefined) changes.push(`Pax → ${dto.paxCount}`);
    this.emailService
      .notifyOpsBookingEvent('amended', {
        bookingRef: updated.bookingRef,
        guestName: updated.guestName,
        guestEmail: updated.guestEmail,
        guestPhone: updated.guestPhone ?? undefined,
        serviceType: updated.serviceType,
        jobDate: updated.jobDate.toISOString().split('T')[0],
        pickupTime: updated.pickupTime
          ? updated.pickupTime.toISOString().slice(11, 16)
          : undefined,
        fromZone: updated.fromZone?.name,
        toZone: updated.toZone?.name,
        hotel: updated.hotel?.name,
        flightNo: updated.flightNo ?? undefined,
        paxCount: updated.paxCount,
        vehicleType: updated.vehicleType?.name,
        total: Number(updated.total),
        currency: updated.currency,
        paymentMethod: updated.paymentMethod,
        paymentStatus: updated.paymentStatus,
        changeSummary: changes.length ? `Amended: ${changes.join(', ')}` : 'Booking amended',
      })
      .catch((err) =>
        this.logger.error(`Failed to send ops amendment notification: ${err.message}`),
      );

    return updated;
  }

  async cancelBooking(clientId: string, ref: string) {
    const booking = await this.prisma.guestBooking.findFirst({
      where: { bookingRef: ref, b2cClientId: clientId },
    });
    if (!booking) throw new NotFoundException('Booking not found');

    if (!['CONFIRMED', 'CONVERTED'].includes(booking.bookingStatus)) {
      throw new BadRequestException(`Cannot cancel a booking with status ${booking.bookingStatus}`);
    }

    const jobDateTime = new Date(booking.jobDate);
    if (booking.pickupTime) {
      const pt = booking.pickupTime;
      jobDateTime.setHours(pt.getHours(), pt.getMinutes(), 0, 0);
    }
    const hoursUntilJob = (jobDateTime.getTime() - Date.now()) / 3_600_000;
    if (hoursUntilJob < 48) {
      throw new BadRequestException('Cancellations must be made at least 48 hours before the job');
    }

    const updated = await this.prisma.guestBooking.update({
      where: { id: booking.id },
      data: { bookingStatus: 'CANCELLED' as any },
      include: { fromZone: true, toZone: true, vehicleType: true, hotel: true },
    });

    if (booking.trafficJobId) {
      await this.prisma.trafficJob.update({
        where: { id: booking.trafficJobId },
        data: { status: 'CANCELLED' as any },
      }).catch(() => { /* job may already be non-cancellable */ });
    }

    // Internal ops notification (additive — recipients configured in admin CMS).
    this.emailService
      .notifyOpsBookingEvent('cancelled', {
        bookingRef: updated.bookingRef,
        guestName: updated.guestName,
        guestEmail: updated.guestEmail,
        guestPhone: updated.guestPhone ?? undefined,
        serviceType: updated.serviceType,
        jobDate: updated.jobDate.toISOString().split('T')[0],
        pickupTime: updated.pickupTime
          ? updated.pickupTime.toISOString().slice(11, 16)
          : undefined,
        fromZone: updated.fromZone?.name,
        toZone: updated.toZone?.name,
        hotel: updated.hotel?.name,
        flightNo: updated.flightNo ?? undefined,
        paxCount: updated.paxCount,
        vehicleType: updated.vehicleType?.name,
        total: Number(updated.total),
        currency: updated.currency,
        paymentMethod: updated.paymentMethod,
        paymentStatus: updated.paymentStatus,
      })
      .catch((err) =>
        this.logger.error(`Failed to send ops cancellation notification: ${err.message}`),
      );

    return { success: true };
  }

  async sendAssignmentNotification(bookingRef: string) {
    const booking = await this.prisma.guestBooking.findFirst({
      where: { bookingRef },
      include: {
        b2cClient: { select: { email: true, name: true } },
        trafficJob: {
          include: {
            assignment: {
              include: {
                vehicle: { select: { plateNumber: true, carBrand: true, carModel: true } },
                driver: { select: { name: true, mobileNumber: true } },
                rep: { select: { name: true, mobileNumber: true } },
                supplierCarType: { select: { vehicleType: { select: { name: true } } } },
              },
            },
          },
        },
      },
    }) as any;

    if (!booking?.b2cClient?.email || !booking.trafficJob?.assignment) return;

    const a = booking.trafficJob.assignment;
    const lines: string[] = [];
    if (a.vehicle) lines.push(`<li><strong>Vehicle:</strong> ${[a.vehicle.carBrand, a.vehicle.carModel].filter(Boolean).join(' ')} — ${a.vehicle.plateNumber}</li>`);
    else if (a.supplierCarType?.vehicleType?.name) lines.push(`<li><strong>Vehicle:</strong> ${a.supplierCarType.vehicleType.name}</li>`);
    if (a.driver) lines.push(`<li><strong>Driver:</strong> ${a.driver.name} — ${a.driver.mobileNumber}</li>`);
    else if (a.externalDriverName) lines.push(`<li><strong>Driver:</strong> ${a.externalDriverName}${a.externalDriverPhone ? ` — ${a.externalDriverPhone}` : ''}</li>`);
    if (a.rep) lines.push(`<li><strong>Rep:</strong> ${a.rep.name} — ${a.rep.mobileNumber}</li>`);

    if (lines.length === 0) return;

    const html = `
      <p>Dear ${booking.b2cClient.name},</p>
      <p>Your booking <strong>${bookingRef}</strong> has been assigned:</p>
      <ul>${lines.join('')}</ul>
      <p>You can view your booking at <a href="/w/account">My Account</a>.</p>
    `;

    await (this.emailService as any).send(
      booking.b2cClient.email,
      `Booking ${bookingRef} — Driver Assigned`,
      html,
    ).catch((err: Error) => this.logger.warn(`Failed to send assignment email: ${err.message}`));
  }
}
