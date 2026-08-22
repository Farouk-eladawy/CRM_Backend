import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import twilio from 'twilio';
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';
import * as fs from 'fs';
import * as path from 'path';
import { PrismaService } from '../prisma/prisma.service.js';
import { UpdateWhatsappSettingsDto } from './dto/update-whatsapp-settings.dto.js';
import { UpdateWhatsappTemplateDto } from './dto/update-whatsapp-template.dto.js';
import type { WhatsappTemplate } from '../../generated/prisma/client.js';
import { serviceTypeLabel } from '../common/utils/service-type.util.js';

const SETTINGS_DEFAULTS = {
  isEnabled: false,
  twilioAccountSid: null,
  twilioAuthToken: null,
  whatsappFrom: null,
  mediaUrl: null,
};

function maskToken(token: string | null | undefined): string | null {
  if (!token) return null;
  if (token.length <= 4) return '****';
  return '****' + token.slice(-4);
}

/** Job select clause used in all notification queries — only fields needed for message building */
const JOB_INCLUDE = {
  originAirport: { select: { name: true } },
  originHotel: { select: { name: true, zone: { select: { name: true } } } },
  originZone: { select: { name: true } },
  destinationAirport: { select: { name: true } },
  destinationHotel: { select: { name: true, zone: { select: { name: true } } } },
  destinationZone: { select: { name: true } },
  assignment: {
    select: {
      driver: { select: { name: true, mobileNumber: true } },
      rep: { select: { name: true, mobileNumber: true } },
    },
  },
} as const;

type JobWithIncludes = Awaited<ReturnType<PrismaService['trafficJob']['findFirst']>> & {
  originAirport?: { name: string } | null;
  originHotel?: { name: string } | null;
  originZone?: { name: string } | null;
  destinationAirport?: { name: string } | null;
  destinationHotel?: { name: string } | null;
  destinationZone?: { name: string } | null;
  assignment?: {
    driver?: { name: string; mobileNumber: string } | null;
    rep?: { name: string; mobileNumber: string } | null;
  } | null;
};

type RawSettings = Awaited<ReturnType<WhatsappNotificationsService['getRawSettings']>>;

@Injectable()
export class WhatsappNotificationsService {
  private readonly logger = new Logger(WhatsappNotificationsService.name);

  constructor(private readonly prisma: PrismaService) {}

  // ─── Settings ────────────────────────────────

  async getSettings() {
    const settings = await this.prisma.whatsappSettings.findFirst();
    if (!settings) return { ...SETTINGS_DEFAULTS, id: null };
    return { ...settings, twilioAuthToken: maskToken(settings.twilioAuthToken) };
  }

  async getRawSettings() {
    return this.prisma.whatsappSettings.findFirst();
  }

  async updateSettings(dto: UpdateWhatsappSettingsDto) {
    const existing = await this.prisma.whatsappSettings.findFirst();
    const data: Record<string, unknown> = {};
    if (dto.isEnabled !== undefined) data.isEnabled = dto.isEnabled;
    if (dto.twilioAccountSid !== undefined) data.twilioAccountSid = dto.twilioAccountSid;
    if (dto.twilioAuthToken !== undefined) data.twilioAuthToken = dto.twilioAuthToken;
    if (dto.whatsappFrom !== undefined) data.whatsappFrom = dto.whatsappFrom;
    if (dto.mediaUrl !== undefined) data.mediaUrl = dto.mediaUrl;

    if (existing) {
      const updated = await this.prisma.whatsappSettings.update({ where: { id: existing.id }, data });
      return { ...updated, twilioAuthToken: maskToken(updated.twilioAuthToken) };
    }

    const created = await this.prisma.whatsappSettings.create({
      data: {
        isEnabled: dto.isEnabled ?? SETTINGS_DEFAULTS.isEnabled,
        twilioAccountSid: dto.twilioAccountSid ?? SETTINGS_DEFAULTS.twilioAccountSid,
        twilioAuthToken: dto.twilioAuthToken ?? SETTINGS_DEFAULTS.twilioAuthToken,
        whatsappFrom: dto.whatsappFrom ?? SETTINGS_DEFAULTS.whatsappFrom,
        mediaUrl: dto.mediaUrl ?? SETTINGS_DEFAULTS.mediaUrl,
      },
    });
    return { ...created, twilioAuthToken: maskToken(created.twilioAuthToken) };
  }

  async updateMediaUrl(url: string) {
    const existing = await this.prisma.whatsappSettings.findFirst();
    if (existing) {
      return this.prisma.whatsappSettings.update({ where: { id: existing.id }, data: { mediaUrl: url } });
    }
    return this.prisma.whatsappSettings.create({ data: { mediaUrl: url } });
  }

  // ─── Templates ───────────────────────────────

  async getTemplates() {
    return this.prisma.whatsappTemplate.findMany({ orderBy: { createdAt: 'asc' } });
  }

  async updateTemplate(id: string, dto: UpdateWhatsappTemplateDto) {
    const data: Record<string, unknown> = {};
    if (dto.name !== undefined) data.name = dto.name;
    if (dto.isEnabled !== undefined) data.isEnabled = dto.isEnabled;
    if (dto.templateBody !== undefined) data.templateBody = dto.templateBody;
    if (dto.daysBefore !== undefined) data.daysBefore = dto.daysBefore;
    if (dto.sendHour !== undefined) data.sendHour = dto.sendHour;
    if (dto.sendMinute !== undefined) data.sendMinute = dto.sendMinute;
    return this.prisma.whatsappTemplate.update({ where: { id }, data });
  }

  // ─── Logs ────────────────────────────────────

  async getLogs(page: number, limit: number) {
    const skip = (page - 1) * limit;
    const [logs, total] = await Promise.all([
      this.prisma.whatsappNotificationLog.findMany({
        skip,
        take: limit,
        orderBy: { sentAt: 'desc' },
        include: { trafficJob: { select: { internalRef: true } } },
      }),
      this.prisma.whatsappNotificationLog.count(),
    ]);
    return { logs, total, page, limit };
  }

  // ─── Test message ─────────────────────────────

  async sendTestMessage(phone: string) {
    const settings = await this.getRawSettings();
    if (!settings?.twilioAccountSid || !settings?.twilioAuthToken || !settings?.whatsappFrom) {
      throw new Error('Twilio credentials not configured');
    }
    const client = twilio(settings.twilioAccountSid, settings.twilioAuthToken);
    const msgOptions: Record<string, unknown> = {
      body: 'This is a test message from iTour TT WhatsApp Notifications.',
      from: `whatsapp:${settings.whatsappFrom}`,
      to: `whatsapp:${phone}`,
    };
    if (settings.mediaUrl) msgOptions.mediaUrl = [settings.mediaUrl];
    const message = await client.messages.create(msgOptions as any);
    return { messageSid: message.sid, status: message.status };
  }

  // ─── Public triggers ─────────────────────────

  /** Called after a job is created. Fire-and-forget safe. */
  async triggerJobCreated(jobId: string): Promise<void> {
    try {
      const [settings, template] = await Promise.all([
        this.getRawSettings(),
        this.prisma.whatsappTemplate.findFirst({ where: { triggerType: 'JOB_CREATED', isEnabled: true } }),
      ]);
      if (!this.credentialsOk(settings) || !template) return;

      const job = await this.prisma.trafficJob.findFirst({
        where: { id: jobId, clientMobile: { not: null }, deletedAt: null },
        include: JOB_INCLUDE,
      });
      if (!job) return;

      const dateStr = job.jobDate.toISOString().split('T')[0];
      await this.sendWhatsappForJob(template, job as JobWithIncludes, settings!, dateStr);
    } catch (err) {
      this.logger.error(`triggerJobCreated error for ${jobId}: ${err}`);
    }
  }

  /** Called after a driver is assigned to a job. Fire-and-forget safe. */
  async triggerDriverAssigned(jobId: string): Promise<void> {
    try {
      const [settings, template] = await Promise.all([
        this.getRawSettings(),
        this.prisma.whatsappTemplate.findFirst({ where: { triggerType: 'DRIVER_ASSIGNED', isEnabled: true } }),
      ]);
      if (!this.credentialsOk(settings) || !template) return;

      const job = await this.prisma.trafficJob.findFirst({
        where: { id: jobId, clientMobile: { not: null }, deletedAt: null },
        include: JOB_INCLUDE,
      });
      if (!job) return;

      const dateStr = job.jobDate.toISOString().split('T')[0];
      await this.sendWhatsappForJob(template, job as JobWithIncludes, settings!, dateStr);
    } catch (err) {
      this.logger.error(`triggerDriverAssigned error for ${jobId}: ${err}`);
    }
  }

  // ─── Cron: SCHEDULED templates ───────────────

  @Cron(CronExpression.EVERY_MINUTE)
  async handleCron() {
    try {
      const settings = await this.getRawSettings();
      if (!this.credentialsOk(settings)) return;

      const scheduledTemplates = await this.prisma.whatsappTemplate.findMany({
        where: { triggerType: 'SCHEDULED', isEnabled: true },
      });
      if (scheduledTemplates.length === 0) return;

      const cairoNow = new Date(new Date().toLocaleString('en-US', { timeZone: 'Africa/Cairo' }));
      const cairoHour = cairoNow.getHours();
      const cairoMinute = cairoNow.getMinutes();

      for (const template of scheduledTemplates) {
        if (template.sendHour === null || template.sendHour !== cairoHour) continue;
        if ((template.sendMinute ?? 0) !== cairoMinute) continue;

        const daysB = template.daysBefore ?? 1;
        const targetDate = new Date(cairoNow);
        targetDate.setDate(targetDate.getDate() + daysB);
        const targetDateStr = targetDate.toISOString().split('T')[0];

        const jobs = await this.prisma.trafficJob.findMany({
          where: {
            jobDate: new Date(targetDateStr),
            clientMobile: { not: null },
            status: { in: ['PENDING', 'ASSIGNED', 'IN_PROGRESS'] },
            deletedAt: null,
          },
          include: JOB_INCLUDE,
        });

        this.logger.log(`WhatsApp SCHEDULED [${template.name}]: ${jobs.length} job(s) for ${targetDateStr}`);
        for (const job of jobs) {
          await this.sendWhatsappForJob(template, job as JobWithIncludes, settings!, targetDateStr);
        }
      }
    } catch (err) {
      this.logger.error('WhatsApp cron error', err);
    }
  }

  // ─── Private helpers ─────────────────────────

  private credentialsOk(settings: RawSettings | null): boolean {
    return !!(
      settings?.isEnabled &&
      settings.twilioAccountSid &&
      settings.twilioAuthToken &&
      settings.whatsappFrom
    );
  }

  private buildMessageBody(templateBody: string, job: JobWithIncludes, dateStr: string): string {
    const origin =
      (job as any).originAirport?.name ??
      (job as any).originHotel?.name ??
      (job as any).originZone?.name ??
      'N/A';
    const destination =
      (job as any).destinationAirport?.name ??
      (job as any).destinationHotel?.name ??
      (job as any).destinationZone?.name ??
      'N/A';
    const pickupTime = job?.pickUpTime
      ? new Date(job.pickUpTime as any).toLocaleTimeString('en-US', {
          timeZone: 'Africa/Cairo',
          hour: '2-digit',
          minute: '2-digit',
        })
      : 'TBD';

    return templateBody
      .replace(/\{\{clientName\}\}/g, (job as any).clientName ?? 'Guest')
      .replace(/\{\{serviceDate\}\}/g, dateStr)
      .replace(/\{\{pickupTime\}\}/g, pickupTime)
      .replace(/\{\{origin\}\}/g, origin)
      .replace(/\{\{destination\}\}/g, destination)
      .replace(/\{\{serviceType\}\}/g, serviceTypeLabel((job as any).serviceType))
      .replace(/\{\{internalRef\}\}/g, (job as any).internalRef ?? '')
      .replace(/\{\{agentRef\}\}/g, (job as any).agentRef ?? 'N/A')
      .replace(/\{\{repName\}\}/g, (job as any).assignment?.rep?.name ?? 'N/A')
      .replace(/\{\{repNumber\}\}/g, (job as any).assignment?.rep?.mobileNumber ?? 'N/A')
      .replace(/\{\{driverName\}\}/g, (job as any).assignment?.driver?.name ?? 'N/A')
      .replace(/\{\{driverNumber\}\}/g, (job as any).assignment?.driver?.mobileNumber ?? 'N/A')
      .replace(/\{\{paxCount\}\}/g, String((job as any).paxCount ?? 0))
      .replace(/\{\{clientSign\}\}/g, (job as any).printSign ? '(attached below)' : 'N/A');
  }

  private async sendWhatsappForJob(
    template: WhatsappTemplate,
    job: JobWithIncludes,
    settings: NonNullable<RawSettings>,
    dateStr: string,
  ): Promise<void> {
    const phone = (job as any).clientMobile as string;

    // Dedup: skip if already SENT for this job + phone + template
    const existing = await this.prisma.whatsappNotificationLog.findFirst({
      where: { trafficJobId: job!.id, recipientPhone: phone, templateId: template.id, status: 'SENT' },
    });
    if (existing) return;

    const body = this.buildMessageBody(template.templateBody, job, dateStr);
    const client = twilio(settings.twilioAccountSid!, settings.twilioAuthToken!);

    let signUrl: string | null = null;
    if ((job as any).printSign && (job as any).clientName) {
      try {
        signUrl = await this.generateJobSignPdf({ id: job!.id, clientName: (job as any).clientName });
      } catch {
        // no sign
      }
    }

    const mediaUrls: string[] = [];
    if (settings.mediaUrl) mediaUrls.push(settings.mediaUrl);
    if (signUrl) mediaUrls.push(signUrl);

    try {
      const message = await client.messages.create({
        body,
        from: `whatsapp:${settings.whatsappFrom}`,
        to: `whatsapp:${phone}`,
        ...(mediaUrls.length > 0 && { mediaUrl: mediaUrls }),
      } as any);

      await this.prisma.whatsappNotificationLog.upsert({
        where: {
          trafficJobId_recipientPhone_templateId: {
            trafficJobId: job!.id,
            recipientPhone: phone,
            templateId: template.id,
          },
        },
        update: { messageSid: message.sid, status: 'SENT', errorMessage: null, sentAt: new Date() },
        create: {
          trafficJobId: job!.id,
          recipientPhone: phone,
          templateId: template.id,
          templateName: template.name,
          messageSid: message.sid,
          status: 'SENT',
        },
      });
      this.logger.log(`WhatsApp [${template.name}] → ${phone} (job: ${(job as any).internalRef})`);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      this.logger.error(`WhatsApp [${template.name}] FAILED for ${phone}: ${errorMessage}`);
      await this.prisma.whatsappNotificationLog.upsert({
        where: {
          trafficJobId_recipientPhone_templateId: {
            trafficJobId: job!.id,
            recipientPhone: phone,
            templateId: template.id,
          },
        },
        update: { status: 'FAILED', errorMessage, sentAt: new Date() },
        create: {
          trafficJobId: job!.id,
          recipientPhone: phone,
          templateId: template.id,
          templateName: template.name,
          status: 'FAILED',
          errorMessage,
        },
      });
    }
  }

  // ─── Sign PDF (preserved) ────────────────────

  async generateJobSignPdf(job: { id: string; clientName: string | null }): Promise<string | null> {
    const clientName = job.clientName;
    if (!clientName) return null;

    const signsDir = path.join(process.cwd(), 'uploads', 'whatsapp', 'signs');
    if (!fs.existsSync(signsDir)) fs.mkdirSync(signsDir, { recursive: true });

    const companySettings = await this.prisma.companySettings.findFirst();
    const logoUrl = companySettings?.logoUrl;

    const pdfDoc = await PDFDocument.create();
    let logoImage: Awaited<ReturnType<typeof pdfDoc.embedJpg>> | null = null;

    if (logoUrl) {
      try {
        const logoPath = path.join(process.cwd(), logoUrl.replace(/^\//, ''));
        const logoBytes = fs.readFileSync(logoPath);
        logoImage = logoUrl.toLowerCase().endsWith('.png')
          ? await pdfDoc.embedPng(logoBytes)
          : await pdfDoc.embedJpg(logoBytes);
      } catch { /* no logo */ }
    }

    const helveticaBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
    const helvetica = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const pageWidth = 842, pageHeight = 595, margin = 30;
    const page = pdfDoc.addPage([pageWidth, pageHeight]);

    page.drawRectangle({
      x: margin, y: margin,
      width: pageWidth - 2 * margin, height: pageHeight - 2 * margin,
      borderColor: rgb(0, 0, 0), borderWidth: 2,
    });

    let currentY = pageHeight - margin - 20;

    if (logoImage) {
      const logoDims = logoImage.scale(1);
      const scale = (pageWidth * 0.9) / logoDims.width;
      const logoW = logoDims.width * scale, logoH = logoDims.height * scale;
      currentY -= logoH;
      page.drawImage(logoImage, { x: (pageWidth - logoW) / 2, y: currentY, width: logoW, height: logoH });
      currentY -= 25;
    } else {
      currentY -= 60;
    }

    page.drawText('Mr/Mrs', { x: margin + 30, y: currentY, size: 18, font: helvetica, color: rgb(0.3, 0.3, 0.3) });
    currentY -= 30;

    let fontSize = 72;
    const maxTextWidth = pageWidth - 2 * margin - 60;
    let textWidth = helveticaBold.widthOfTextAtSize(clientName, fontSize);
    while (textWidth > maxTextWidth && fontSize > 24) {
      fontSize -= 2;
      textWidth = helveticaBold.widthOfTextAtSize(clientName, fontSize);
    }
    const textX = (pageWidth - textWidth) / 2;
    const remainingHeight = currentY - margin;
    const textY = margin + remainingHeight / 2 - fontSize / 3;
    page.drawText(clientName, { x: textX, y: textY, size: fontSize, font: helveticaBold, color: rgb(0, 0, 0) });

    const pdfBytes = await pdfDoc.save();
    const filename = `sign-${job.id}.pdf`;
    fs.writeFileSync(path.join(signsDir, filename), Buffer.from(pdfBytes));
    return `/uploads/whatsapp/signs/${filename}`;
  }
}
