import { Injectable, Logger, Inject, forwardRef } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as nodemailer from 'nodemailer';
import type { Transporter } from 'nodemailer';
import { resolve4 } from 'dns';
import { promisify } from 'util';
import { PrismaService } from '../prisma/prisma.service.js';

const resolve4Async = promisify(resolve4);

import { serviceTypeLabel } from '../common/utils/service-type.util.js';
import {
  bookingConfirmationTemplate,
  paymentReceiptTemplate,
  onlinePaymentFailedTemplate,
  bookingCancellationTemplate,
  staffAssignmentTemplate,
  jobUpdateNotificationTemplate,
  type EmailBranding,
} from './templates/index.js';

export interface BookingEmailData {
  bookingRef: string;
  guestName: string;
  guestEmail: string;
  serviceType: string;
  jobDate: string;
  pickupTime?: string;
  fromZone: string;
  toZone: string;
  hotel?: string;
  flightNo?: string;
  paxCount: number;
  vehicleType: string;
  total: number;
  currency: string;
  paymentMethod: string;
}

export interface PaymentReceiptData {
  bookingRef: string;
  guestName: string;
  guestEmail: string;
  amount: number;
  currency: string;
  gateway: string;
  transactionId: string;
  paidAt: string;
}

export interface PaymentFailedData {
  bookingRef: string;
  guestName: string;
  guestEmail: string;
  amount: number;
  currency: string;
}

export interface StaffAssignmentData {
  bookingRef: string;
  guestName: string;
  guestEmail: string;
  serviceType: string;
  /** Arrival → the airport the guest lands at; Departure → the pickup/start point. */
  meetingPoint?: string;
  /** Formatted pickup time (HH:MM). */
  pickupTime?: string;
  repName: string;
  repPhone?: string;
  driverName: string;
  driverPhone: string;
  vehiclePlate: string;
  vehicleType: string;
  vehicleColor?: string;
}

/** Internal ops alert when a B2C booking is created, amended, or cancelled. */
export interface OpsBookingNotificationData {
  bookingRef: string;
  guestName: string;
  guestEmail: string;
  guestPhone?: string;
  serviceType: string;
  jobDate: string;
  pickupTime?: string;
  fromZone?: string;
  toZone?: string;
  hotel?: string;
  flightNo?: string;
  paxCount: number;
  vehicleType?: string;
  total: number;
  currency: string;
  paymentMethod: string;
  paymentStatus?: string;
  notes?: string;
  /** For amendments: human-readable summary of what changed. */
  changeSummary?: string;
}

/** Internal finance alert when a B2C booking is paid. */
export interface FinancePaymentNotificationData {
  bookingRef: string;
  guestName: string;
  guestEmail: string;
  amount: number;
  currency: string;
  gateway: string;
  transactionId: string;
  paidAt: string;
  paymentMethod?: string;
}

export interface JobUpdateEmailData {
  internalRef: string;
  bookingChannel: string;
  bookingStatus: string;
  jobStatus: string;
  agentName?: string;
  agentRef?: string;
  customerName?: string;
  serviceType: string;
  jobDate: string;
  pickUpTime?: string;
  adultCount: number;
  childCount: number;
  paxCount: number;
  clientName?: string;
  clientMobile?: string;
  originLocation?: string;
  destinationLocation?: string;
  flightNo?: string;
  notes?: string;
  updatedBy: string;
  updatedAt: string;
  changedFields: string[];
}

@Injectable()
export class EmailService {
  private readonly logger = new Logger(EmailService.name);
  private transporter: Transporter | null = null;
  private fromAddress: string;
  private dbInitialized = false;

  constructor(
    private readonly config: ConfigService,
    private readonly prisma: PrismaService,
  ) {
    this.fromAddress = this.config.get<string>('SMTP_FROM', 'noreply@itour.local');

    const host = this.config.get<string>('SMTP_HOST');
    if (host) {
      this.logger.log(`SMTP_HOST env set to ${host} — will resolve IPv4 on first send`);
    } else {
      this.logger.warn('SMTP_HOST not configured via env — will check DB settings on first send');
    }
  }

  /** Lazily load SMTP config from DB if env vars aren't set. */
  private async ensureTransporter(): Promise<void> {
    if (this.transporter || this.dbInitialized) return;

    // Check env vars first (takes priority)
    const envHost = this.config.get<string>('SMTP_HOST');
    if (envHost) {
      const resolvedHost = await this.resolveToIPv4(envHost);
      this.transporter = nodemailer.createTransport({
        host: resolvedHost,
        port: this.config.get<number>('SMTP_PORT', 587),
        secure: this.config.get<boolean>('SMTP_SECURE', false),
        tls: { servername: envHost },
        auth: {
          user: this.config.get<string>('SMTP_USER'),
          pass: this.config.get<string>('SMTP_PASS'),
        },
      });
      this.dbInitialized = true;
      this.logger.log(`Email transporter from env: ${envHost} → ${resolvedHost}`);
      return;
    }

    try {
      const settings = await this.prisma.emailSettings.findFirst();
      if (settings?.smtpHost) {
        const resolvedHost = await this.resolveToIPv4(settings.smtpHost);
        this.transporter = nodemailer.createTransport({
          host: resolvedHost,
          port: settings.smtpPort,
          secure: settings.smtpSecure,
          tls: { servername: settings.smtpHost },
          auth: {
            user: settings.smtpUser ?? undefined,
            pass: settings.smtpPass ?? undefined,
          },
        });
        this.fromAddress = settings.fromAddress;
        this.logger.log(`Email transporter configured from DB: ${settings.smtpHost} → ${resolvedHost}`);
      }
    } catch (err) {
      this.logger.error(`Failed to load email settings from DB: ${(err as Error).message}`);
    } finally {
      this.dbInitialized = true;
    }
  }

  /** Resolve hostname to IPv4 to avoid ENETUNREACH on IPv6-only pods. */
  private async resolveToIPv4(hostname: string): Promise<string> {
    try {
      const addrs = await resolve4Async(hostname);
      return addrs[0] ?? hostname;
    } catch {
      return hostname;
    }
  }

  /** Force reload transporter from DB (called after settings update). */
  reloadTransporter(): void {
    this.transporter = null;
    this.dbInitialized = false;
  }

  /**
   * Build B2C (Transfera) branding for guest-facing emails from the website
   * settings configured in the admin area. Falls back to sensible defaults so
   * emails keep sending if settings are missing. The logo must be a raster
   * (PNG/JPG) image — email clients don't render SVG — so an SVG `siteLogoUrl`
   * is ignored in favour of the bundled email-safe logo.
   */
  private async getGuestBranding(): Promise<EmailBranding> {
    const base = this.config
      .get<string>('PUBLIC_BACKEND_URL', 'https://fulvago.itourtt.cloud')
      .replace(/\/+$/, '');
    const siteUrl = this.config
      .get<string>('PUBLIC_SITE_URL', 'https://transfera.ae')
      .replace(/\/+$/, '');
    // Email-safe fallback logo (yellow Transfera mark on dark header).
    const fallbackLogo = `${base}/uploads/1780470940148-Transfera-Logo-Yellow-w-v1.jpg`;

    const branding: EmailBranding = {
      siteName: 'Transfera',
      contactEmail: 'support@itour.local',
      headerBg: '#191919',
      logoUrl: fallbackLogo,
      termsUrl: `${siteUrl}/terms-and-conditions`,
      loginUrl: `${siteUrl}/login`,
    };

    try {
      const ws = await this.prisma.websiteSettings.findFirst();
      if (ws?.siteName) branding.siteName = ws.siteName;
      if (ws?.contactEmail) branding.contactEmail = ws.contactEmail;
      // Use the admin-configured logo only when it's a raster image.
      if (ws?.siteLogoUrl && /\.(png|jpe?g|gif|webp)$/i.test(ws.siteLogoUrl)) {
        branding.logoUrl = ws.siteLogoUrl.startsWith('http')
          ? ws.siteLogoUrl
          : `${base}${ws.siteLogoUrl}`;
      }
    } catch (err) {
      this.logger.warn(`Could not load website settings for email branding: ${(err as Error).message}`);
    }

    return branding;
  }

  async sendBookingConfirmation(data: BookingEmailData): Promise<void> {
    const html = bookingConfirmationTemplate(data, await this.getGuestBranding());
    await this.send(data.guestEmail, `Booking Confirmed - ${data.bookingRef}`, html);
  }

  async sendPaymentReceipt(
    data: PaymentReceiptData,
    attachments?: Array<{ filename: string; content: Buffer }>,
  ): Promise<void> {
    const html = paymentReceiptTemplate(data, await this.getGuestBranding());
    await this.send(data.guestEmail, `Payment Receipt - ${data.bookingRef}`, html, attachments);
  }

  async sendOnlinePaymentFailed(data: PaymentFailedData): Promise<void> {
    const html = onlinePaymentFailedTemplate(data, await this.getGuestBranding());
    await this.send(
      data.guestEmail,
      `Payment Not Completed - Pay on Arrival - ${data.bookingRef}`,
      html,
    );
  }

  async sendBookingCancellation(data: BookingEmailData): Promise<void> {
    const html = bookingCancellationTemplate(data, await this.getGuestBranding());
    await this.send(data.guestEmail, `Booking Cancelled - ${data.bookingRef}`, html);
  }

  /**
   * Read an admin-configured, comma/semicolon/whitespace-separated recipient
   * list from website settings. Returns [] when unset, so callers no-op cleanly.
   */
  private async getNotificationRecipients(
    field: 'opsNotificationEmails' | 'financeNotificationEmails',
  ): Promise<string[]> {
    try {
      const ws = await this.prisma.websiteSettings.findFirst();
      const raw = (ws as Record<string, unknown> | null)?.[field] as
        | string
        | null
        | undefined;
      if (!raw) return [];
      return raw
        .split(/[,;\s]+/)
        .map((s) => s.trim())
        .filter(Boolean);
    } catch (err) {
      this.logger.error(
        `Failed to read notification recipients (${field}): ${(err as Error).message}`,
      );
      return [];
    }
  }

  private esc(v?: string | number | null): string {
    return String(v ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /**
   * Notify the operations team that a B2C booking was created / amended /
   * cancelled. Recipients come from website settings (opsNotificationEmails);
   * no-op when unconfigured. This is additive — guest-facing emails still send.
   */
  async notifyOpsBookingEvent(
    kind: 'new' | 'amended' | 'cancelled',
    data: OpsBookingNotificationData,
  ): Promise<void> {
    const recipients = await this.getNotificationRecipients('opsNotificationEmails');
    if (recipients.length === 0) return;

    const label =
      kind === 'new' ? 'NEW BOOKING' : kind === 'amended' ? 'AMENDED' : 'CANCELLED';
    const accent =
      kind === 'new' ? '#16a34a' : kind === 'amended' ? '#d97706' : '#dc2626';
    const subject = `[${label}] B2C Booking ${data.bookingRef} — ${data.guestName}`;
    const row = (k: string, v?: string | number | null) =>
      v === undefined || v === null || v === ''
        ? ''
        : `<tr><td style="padding:4px 12px 4px 0;color:#666;">${this.esc(k)}</td><td style="padding:4px 0;font-weight:600;color:#111;">${this.esc(v)}</td></tr>`;

    const html = `
      <div style="font-family:Arial,sans-serif;padding:20px;color:#333;max-width:640px;">
        <div style="background:${accent};color:#fff;padding:10px 16px;border-radius:6px 6px 0 0;font-weight:700;">
          ${label} — ${this.esc(data.bookingRef)}
        </div>
        <div style="border:1px solid #eee;border-top:none;padding:16px;border-radius:0 0 6px 6px;">
          ${data.changeSummary ? `<p style="margin:0 0 12px;padding:8px 12px;background:#fff7ed;border-left:3px solid ${accent};">${this.esc(data.changeSummary)}</p>` : ''}
          <table style="border-collapse:collapse;font-size:14px;width:100%;">
            ${row('Guest', data.guestName)}
            ${row('Email', data.guestEmail)}
            ${row('Phone', data.guestPhone)}
            ${row('Service', serviceTypeLabel(data.serviceType))}
            ${row('Date', data.jobDate)}
            ${row('Pickup time', data.pickupTime)}
            ${row('From', data.fromZone)}
            ${row('To', data.toZone)}
            ${row('Hotel', data.hotel)}
            ${row('Flight', data.flightNo)}
            ${row('Pax', data.paxCount)}
            ${row('Vehicle', data.vehicleType)}
            ${row('Total', `${data.currency} ${Number(data.total).toFixed(2)}`)}
            ${row('Payment method', data.paymentMethod)}
            ${row('Payment status', data.paymentStatus)}
            ${row('Notes', data.notes)}
          </table>
        </div>
        <p style="color:#999;font-size:12px;margin-top:12px;">Automated operations notification · iTour Transport &amp; Traffic</p>
      </div>
    `;

    for (const to of recipients) {
      await this.send(to, subject, html);
    }
  }

  /**
   * Notify the finance team that a B2C booking has been paid. Recipients come
   * from website settings (financeNotificationEmails); no-op when unconfigured.
   */
  async notifyFinancePayment(data: FinancePaymentNotificationData): Promise<void> {
    const recipients = await this.getNotificationRecipients('financeNotificationEmails');
    if (recipients.length === 0) return;

    const subject = `[PAID] ${data.currency} ${Number(data.amount).toFixed(2)} — Booking ${data.bookingRef}`;
    const row = (k: string, v?: string | number | null) =>
      v === undefined || v === null || v === ''
        ? ''
        : `<tr><td style="padding:4px 12px 4px 0;color:#666;">${this.esc(k)}</td><td style="padding:4px 0;font-weight:600;color:#111;">${this.esc(v)}</td></tr>`;

    const html = `
      <div style="font-family:Arial,sans-serif;padding:20px;color:#333;max-width:640px;">
        <div style="background:#16a34a;color:#fff;padding:10px 16px;border-radius:6px 6px 0 0;font-weight:700;">
          PAYMENT RECEIVED — ${this.esc(data.bookingRef)}
        </div>
        <div style="border:1px solid #eee;border-top:none;padding:16px;border-radius:0 0 6px 6px;">
          <table style="border-collapse:collapse;font-size:14px;width:100%;">
            ${row('Amount', `${data.currency} ${Number(data.amount).toFixed(2)}`)}
            ${row('Gateway', data.gateway)}
            ${row('Payment method', data.paymentMethod)}
            ${row('Transaction ID', data.transactionId)}
            ${row('Paid at', data.paidAt)}
            ${row('Guest', data.guestName)}
            ${row('Email', data.guestEmail)}
          </table>
        </div>
        <p style="color:#999;font-size:12px;margin-top:12px;">Automated finance notification · iTour Transport &amp; Traffic</p>
      </div>
    `;

    for (const to of recipients) {
      await this.send(to, subject, html);
    }
  }

  async sendStaffAssignment(data: StaffAssignmentData): Promise<void> {
    const html = staffAssignmentTemplate(data, await this.getGuestBranding());
    await this.send(data.guestEmail, `Staff Assigned - ${data.bookingRef}`, html);
  }

  async sendJobUpdateNotification(recipients: string[], data: JobUpdateEmailData): Promise<void> {
    const html = jobUpdateNotificationTemplate(data);
    const subject = `${data.bookingStatus} - ${data.internalRef} - ${data.agentRef || 'N/A'} - ${data.updatedAt}`;
    for (const to of recipients) {
      await this.send(to, subject, html);
    }
  }

  /** Notify the team of a new B2C contact-form submission. */
  async sendContactNotification(
    to: string,
    data: {
      name: string;
      email: string;
      phone?: string | null;
      subject?: string | null;
      message: string;
      createdAt: Date;
    },
  ): Promise<void> {
    const esc = (v?: string | null) =>
      (v ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    const subject = `New contact message${data.subject ? `: ${esc(data.subject)}` : ''} — from ${esc(data.name)}`;
    const html = `
      <div style="font-family:Arial,sans-serif;padding:20px;color:#333;">
        <h2 style="margin:0 0 16px;">New contact message</h2>
        <p><strong>Name:</strong> ${esc(data.name)}</p>
        <p><strong>Email:</strong> <a href="mailto:${esc(data.email)}">${esc(data.email)}</a></p>
        <p><strong>Phone:</strong> ${esc(data.phone) || '—'}</p>
        <p><strong>Subject:</strong> ${esc(data.subject) || '—'}</p>
        <p><strong>Message:</strong></p>
        <p style="white-space:pre-wrap;border-left:3px solid #eee;padding-left:12px;">${esc(data.message)}</p>
        <hr style="border:none;border-top:1px solid #eee;margin:20px 0;" />
        <p style="color:#999;font-size:12px;">Received ${data.createdAt.toISOString()} · reply directly to ${esc(data.email)}</p>
      </div>
    `;
    await this.send(to, subject, html);
  }

  async sendDisputeReport(
    to: string,
    subject: string,
    body: string,
    pdfBuffer: Buffer,
    filename: string,
    cc: string[] = [],
  ): Promise<void> {
    await this.ensureTransporter();
    const html = `
      <div style="font-family:Arial,sans-serif;padding:20px;color:#333;">
        <p>${body.replace(/\n/g, '<br/>')}</p>
        <hr style="border:none;border-top:1px solid #eee;margin:20px 0;" />
        <p style="color:#999;font-size:12px;">iTour Transport &amp; Traffic</p>
      </div>
    `;

    if (!this.transporter) {
      this.logger.log(
        `[Email Mock] Dispute report to: ${to}${cc.length ? ` | CC: ${cc.join(', ')}` : ''} | Subject: ${subject} | Attachment: ${filename}`,
      );
      return;
    }

    try {
      await this.transporter.sendMail({
        from: this.fromAddress,
        to,
        ...(cc.length ? { cc: cc.join(', ') } : {}),
        subject,
        html,
        attachments: [
          {
            filename,
            content: pdfBuffer,
            contentType: 'application/pdf',
          },
        ],
      });
      this.logger.log(`Dispute report email sent to ${to}: ${subject}`);
    } catch (error) {
      this.logger.error(`Failed to send dispute report to ${to}: ${(error as Error).message}`);
    }
  }

  async sendTestEmail(to: string): Promise<void> {
    await this.ensureTransporter();

    if (!this.transporter) {
      throw new Error('SMTP is not configured. Save your email settings first.');
    }

    const html = `
      <div style="font-family:Arial,sans-serif;padding:20px;">
        <h2 style="color:#333;">iTour TT — Test Email</h2>
        <p>This is a test email to verify your SMTP configuration.</p>
        <p>If you received this email, your settings are working correctly.</p>
        <hr style="border:none;border-top:1px solid #eee;margin:20px 0;" />
        <p style="color:#999;font-size:12px;">Sent at ${new Date().toLocaleString('en-GB', { timeZone: 'Africa/Cairo' })} (Cairo time)</p>
      </div>
    `;

    // Intentionally NOT wrapped in try/catch — let errors propagate so the
    // caller receives the real SMTP failure reason instead of a false success.
    await this.transporter.sendMail({
      from: this.fromAddress,
      to,
      subject: 'iTour TT — SMTP Test',
      html,
    });
    this.logger.log(`Test email sent to ${to}`);
  }

  private async send(
    to: string,
    subject: string,
    html: string,
    attachments?: Array<{ filename: string; content: Buffer }>,
  ): Promise<void> {
    await this.ensureTransporter();
    if (!this.transporter) {
      this.logger.log(`[Email Mock] To: ${to} | Subject: ${subject}`);
      return;
    }

    try {
      await this.transporter.sendMail({
        from: this.fromAddress,
        to,
        subject,
        html,
        ...(attachments && attachments.length > 0 ? { attachments } : {}),
      });
      this.logger.log(`Email sent to ${to}: ${subject}`);
    } catch (error) {
      this.logger.error(`Failed to send email to ${to}: ${(error as Error).message}`);
    }
  }
}
