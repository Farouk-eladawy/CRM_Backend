import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PrismaService } from '../prisma/prisma.service.js';
import { EmailService, type JobUpdateEmailData } from '../email/email.service.js';
import { serviceTypeLabel } from '../common/utils/service-type.util.js';

@Injectable()
export class NotificationsService {
  private readonly logger = new Logger(NotificationsService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly emailService: EmailService,
    private readonly config: ConfigService,
  ) {}

  /**
   * Create in-app + email notifications for all users with traffic-jobs permission.
   * Fire-and-forget — caller should `.catch()` to avoid blocking.
   */
  async notifyJobUpdate(
    jobId: string,
    updatedByUserId: string,
    changedFields: string[],
  ): Promise<void> {
    // 1. Load the full job
    const job = await this.prisma.trafficJob.findUnique({
      where: { id: jobId },
      include: {
        agent: { select: { legalName: true } },
        customer: { select: { legalName: true } },
        originAirport: { select: { name: true } },
        originZone: { select: { name: true } },
        originHotel: { select: { name: true } },
        destinationAirport: { select: { name: true } },
        destinationZone: { select: { name: true } },
        destinationHotel: { select: { name: true } },
        flight: true,
      },
    });

    if (!job) return;

    // Get the updater's name
    const updater = await this.prisma.user.findUnique({
      where: { id: updatedByUserId },
      select: { name: true },
    });

    // 2. Find all active users with 'traffic-jobs' permission, excluding the updater
    const recipients = await this.prisma.user.findMany({
      where: {
        isActive: true,
        deletedAt: null,
        id: { not: updatedByUserId },
        OR: [
          // Users with granular role that has traffic-jobs permission
          {
            roleRef: {
              permissions: {
                some: { permissionKey: 'traffic-jobs' },
              },
            },
          },
          // Admin users (legacy enum) always have access
          { role: 'ADMIN' },
        ],
      },
      select: { id: true, email: true },
    });

    if (recipients.length === 0) return;

    const title = `Job Updated: ${job.internalRef}`;
    const message = `${job.bookingStatus} - ${job.internalRef} - ${job.agentRef || 'N/A'} - Updated by ${updater?.name || 'System'}`;

    // 3. Bulk create in-app notifications
    await this.prisma.userNotification.createMany({
      data: recipients.map((r) => ({
        userId: r.id,
        title,
        message,
        type: 'JOB_UPDATED' as const,
        trafficJobId: jobId,
        metadata: { changedFields },
      })),
    });

    this.logger.log(`Created ${recipients.length} in-app notifications for job ${job.internalRef}`);

    // 4. Build email data
    const originLocation =
      job.originAirport?.name || job.originZone?.name || job.originHotel?.name || '';
    const destinationLocation =
      job.destinationAirport?.name || job.destinationZone?.name || job.destinationHotel?.name || '';

    const now = new Date();
    const cairoTime = now.toLocaleString('en-GB', { timeZone: 'Africa/Cairo' });

    const emailData: JobUpdateEmailData = {
      internalRef: job.internalRef,
      bookingChannel: job.bookingChannel,
      bookingStatus: job.bookingStatus,
      jobStatus: job.status,
      agentName: job.agent?.legalName,
      agentRef: job.agentRef ?? undefined,
      customerName: job.customer?.legalName,
      serviceType: job.serviceType,
      jobDate: job.jobDate.toISOString().split('T')[0],
      pickUpTime: job.pickUpTime
        ? job.pickUpTime.toLocaleString('en-GB', { timeZone: 'Africa/Cairo' })
        : undefined,
      adultCount: job.adultCount,
      childCount: job.childCount,
      paxCount: job.paxCount,
      clientName: job.clientName ?? undefined,
      clientMobile: job.clientMobile ?? undefined,
      originLocation: originLocation || undefined,
      destinationLocation: destinationLocation || undefined,
      flightNo: job.flight?.flightNo ?? undefined,
      notes: job.notes ?? undefined,
      updatedBy: updater?.name || 'System',
      updatedAt: cairoTime,
      changedFields,
    };

    // 5. Email goes to the single system-notification mailbox configured in
    //    System Parameters > Company. Admins/traffic users are NOT emailed
    //    individually anymore — they still get the in-app notification above.
    const companySettings = await this.prisma.companySettings.findFirst();
    const systemEmail = companySettings?.systemNotificationEmail?.trim();

    if (!systemEmail) {
      this.logger.log(
        `No system notification email configured — skipping email for job ${job.internalRef}`,
      );
      return;
    }

    // 6. Send email (fire-and-forget, errors logged internally)
    await this.emailService.sendJobUpdateNotification([systemEmail], emailData);

    this.logger.log(`Sent system notification email for job ${job.internalRef} to ${systemEmail}`);
  }

  /**
   * Notify all online (booking) users when a dispatcher performs an action.
   * Fire-and-forget — caller should `.catch()` to avoid blocking.
   */
  async notifyDispatchAction(
    jobId: string,
    actorUserId: string,
    action: 'ASSIGNED' | 'REASSIGNED' | 'UNASSIGNED',
    details: {
      vehiclePlate?: string;
      driverName?: string;
      repName?: string;
    },
  ): Promise<void> {
    const job = await this.prisma.trafficJob.findUnique({
      where: { id: jobId },
      select: { internalRef: true, serviceType: true, jobDate: true },
    });
    if (!job) return;

    const actor = await this.prisma.user.findUnique({
      where: { id: actorUserId },
      select: { name: true },
    });

    // Notify all active users with traffic-jobs permission, excluding the actor
    const recipients = await this.prisma.user.findMany({
      where: {
        isActive: true,
        deletedAt: null,
        id: { not: actorUserId },
        OR: [
          {
            roleRef: {
              permissions: { some: { permissionKey: 'traffic-jobs' } },
            },
          },
          { role: 'ADMIN' },
        ],
      },
      select: { id: true },
    });

    if (recipients.length === 0) return;

    const actionLabel = action === 'ASSIGNED' ? 'Assigned' : action === 'REASSIGNED' ? 'Reassigned' : 'Unassigned';
    const title = `Dispatch – Job ${actionLabel}: ${job.internalRef}`;

    const parts: string[] = [];
    if (details.vehiclePlate) parts.push(`Vehicle: ${details.vehiclePlate}`);
    if (details.driverName)   parts.push(`Driver: ${details.driverName}`);
    if (details.repName)       parts.push(`Rep: ${details.repName}`);
    const detailStr = parts.length ? ` — ${parts.join(' / ')}` : '';
    const message = `${serviceTypeLabel(job.serviceType)} on ${job.jobDate.toISOString().split('T')[0]}${detailStr} (by ${actor?.name || 'Dispatcher'})`;

    await this.prisma.userNotification.createMany({
      data: recipients.map((r) => ({
        userId: r.id,
        title,
        message,
        type: 'JOB_ASSIGNED' as const,
        trafficJobId: jobId,
        metadata: { action, ...details },
      })),
    });

    this.logger.log(`Dispatch ${action} notification sent to ${recipients.length} users for job ${job.internalRef}`);
  }

  /**
   * List notifications for a user (latest 50) with unread count.
   */
  async getUserNotifications(userId: string) {
    const [notifications, unreadCount] = await Promise.all([
      this.prisma.userNotification.findMany({
        where: { userId },
        orderBy: { createdAt: 'desc' },
        take: 50,
        include: {
          trafficJob: {
            select: { internalRef: true, bookingStatus: true, status: true },
          },
        },
      }),
      this.prisma.userNotification.count({
        where: { userId, isRead: false },
      }),
    ]);

    return { notifications, unreadCount };
  }

  /**
   * Mark a single notification as read.
   */
  async markAsRead(userId: string, notificationId: string) {
    return this.prisma.userNotification.updateMany({
      where: { id: notificationId, userId },
      data: { isRead: true },
    });
  }

  /**
   * Mark all notifications as read for a user.
   */
  async markAllAsRead(userId: string) {
    return this.prisma.userNotification.updateMany({
      where: { userId, isRead: false },
      data: { isRead: true },
    });
  }
}
