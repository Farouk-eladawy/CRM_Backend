import { Injectable, Logger } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import { EmailService } from '../email/email.service.js';
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class NoShowDisputeService {
  private readonly logger = new Logger(NoShowDisputeService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly emailService: EmailService,
  ) {}

  /** Called after driver submits no-show. Runs async — never throws to the caller. */
  async generateAndSendDisputeReport(jobId: string): Promise<void> {
    try {
      await this._run(jobId);
    } catch (err) {
      this.logger.error(
        `Failed to generate/send no-show dispute report for job ${jobId}: ${(err as Error).message}`,
        (err as Error).stack,
      );
    }
  }

  // ─────────────────────────────────────────────────────────────
  // PRIVATE IMPLEMENTATION
  // ─────────────────────────────────────────────────────────────

  private async _run(jobId: string): Promise<void> {
    const [job, emailConfig] = await Promise.all([
      this.prisma.trafficJob.findUnique({
        where: { id: jobId },
        include: {
          agent: {
            select: {
              legalName: true,
              tradeName: true,
              disputeEmail: true,
            },
          },
          fromZone: { select: { name: true } },
          toZone: { select: { name: true } },
          originAirport: { select: { name: true, code: true } },
          destinationAirport: { select: { name: true, code: true } },
          originHotel: { select: { name: true } },
          destinationHotel: { select: { name: true } },
          flight: { select: { flightNo: true, carrier: true } },
          assignment: {
            include: {
              vehicle: {
                include: { vehicleType: { select: { name: true } } },
              },
              driver: { select: { name: true } },
              rep: { select: { name: true } },
            },
          },
          noShowEvidence: { orderBy: { createdAt: 'asc' } },
          inPlaceEvidence: { orderBy: { createdAt: 'asc' } },
          completedEvidence: { orderBy: { createdAt: 'asc' } },
        },
      }),
      this.prisma.emailSettings.findFirst(),
    ]);

    if (!job) {
      this.logger.warn(`No-show dispute: job ${jobId} not found`);
      return;
    }

    const agentRef = job.agentRef ?? job.internalRef;
    const agentName = job.agent?.legalName ?? 'Unknown Agent';
    const jobStatus = String(job.status);
    const jobDateStr = job.jobDate
      ? new Date(job.jobDate).toISOString().split('T')[0]
      : '-';

    // Resolve TO — config override takes priority, fallback to agent dispute email
    const toAddress = emailConfig?.disputeTo || job.agent?.disputeEmail;
    if (!toAddress) {
      this.logger.log(
        `No-show dispute: no TO address for job ${jobId} (no config override and agent has no dispute email) — skipping`,
      );
      return;
    }

    // Build CC list from config (filter out empty strings)
    const cc = [emailConfig?.disputeCc1, emailConfig?.disputeCc2, emailConfig?.disputeCc3]
      .filter((e): e is string => Boolean(e));

    // Token map for subject/body templates
    const tokens: Record<string, string> = {
      AgentRef: agentRef,
      AgentReference: agentRef,
      AgentName: agentName,
      JobStatus: jobStatus,
      InternalRef: job.internalRef,
      JobDate: jobDateStr,
      ServiceType: job.serviceType ?? '-',
      Route: this.buildRoute(job),
      DriverName: job.assignment?.driver?.name ?? '-',
      RepName: job.assignment?.rep?.name ?? '-',
      ClientName: job.clientName ?? '-',
      PaxCount: String(job.paxCount ?? '-'),
    };

    const resolve = (template: string): string =>
      template.replace(/\{(\w+)\}/g, (_, key: string) => tokens[key] ?? `{${key}}`);

    const subject = resolve(
      emailConfig?.disputeSubject || '{AgentRef} - {JobStatus}',
    );
    const body = resolve(
      emailConfig?.disputeBody ||
        'Dear Partner,\n\nPlease see attached evidence for {AgentRef} as the job {JobStatus}.\n\nRegards,\niTour Transport & Traffic',
    );

    const pdfBuffer = await this.buildPdf(job, agentRef, agentName);

    const safeName = (s: string) => s.replace(/[^a-zA-Z0-9_\-]/g, '_');
    const filename = `${safeName(agentRef)}_${safeName(agentName)}_${safeName(job.internalRef)}_${jobDateStr}.pdf`;

    await this.emailService.sendDisputeReport(toAddress, subject, body, pdfBuffer, filename, cc);

    this.logger.log(
      `No-show dispute report sent to ${toAddress}${cc.length ? ` (CC: ${cc.join(', ')})` : ''} for job ${job.internalRef}`,
    );
  }

  // ─────────────────────────────────────────────────────────────
  // PDF BUILDER
  // ─────────────────────────────────────────────────────────────

  private async buildPdf(job: any, agentRef: string, agentName: string): Promise<Buffer> {
    const pdfDoc = await PDFDocument.create();
    const fontBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
    const fontRegular = await pdfDoc.embedFont(StandardFonts.Helvetica);

    const pageWidth = 595;
    const pageHeight = 842;
    const margin = 40;
    const contentWidth = pageWidth - 2 * margin;

    // ── COVER PAGE ────────────────────────────────────────────
    const page = pdfDoc.addPage([pageWidth, pageHeight]);
    let y = pageHeight - margin;

    const drawText = (
      p: typeof page,
      text: string,
      x: number,
      cy: number,
      size: number,
      bold = false,
      color = rgb(0, 0, 0),
    ) => {
      p.drawText(this.sanitize(text), {
        x,
        y: cy,
        size,
        font: bold ? fontBold : fontRegular,
        color,
      });
    };

    // Title
    drawText(page, 'NO-SHOW EVIDENCE REPORT', margin, y, 18, true, rgb(0.8, 0.1, 0.1));
    y -= 30;

    // Divider
    page.drawLine({
      start: { x: margin, y },
      end: { x: pageWidth - margin, y },
      thickness: 1,
      color: rgb(0.7, 0.7, 0.7),
    });
    y -= 18;

    // Job details table
    const details: [string, string][] = [
      ['Agent Reference', agentRef],
      ['Agent Name', agentName],
      ['Job Reference', job.internalRef],
      ['Job Status', job.status],
      ['Service Type', job.serviceType ?? '-'],
      ['Job Date', job.jobDate ? new Date(job.jobDate).toISOString().split('T')[0] : '-'],
      ['Route', this.buildRoute(job)],
      ['Pax Count', String(job.paxCount ?? '-')],
      ['Flight', job.flight ? `${job.flight.carrier ?? ''} ${job.flight.flightNo ?? ''}`.trim() : '-'],
      ['Vehicle', job.assignment?.vehicle?.vehicleType?.name ?? '-'],
      ['Plate', job.assignment?.vehicle?.plateNumber ?? '-'],
      ['Driver', job.assignment?.driver?.name ?? '-'],
      ['Rep', job.assignment?.rep?.name ?? '-'],
      ['Client Name', job.clientName ?? '-'],
    ];

    for (const [label, value] of details) {
      if (y < margin + 20) break; // safety
      drawText(page, `${label}:`, margin, y, 10, true);
      drawText(page, value, margin + 130, y, 10);
      y -= 16;
    }

    y -= 10;
    page.drawLine({
      start: { x: margin, y },
      end: { x: pageWidth - margin, y },
      thickness: 0.5,
      color: rgb(0.8, 0.8, 0.8),
    });
    y -= 16;

    // Summary of evidence counts
    const driverNoShow = job.noShowEvidence.filter((e: any) =>
      e.submittedBy?.toLowerCase().includes('driver'),
    );
    const repNoShow = job.noShowEvidence.filter((e: any) =>
      !e.submittedBy?.toLowerCase().includes('driver'),
    );

    drawText(page, 'Evidence Summary', margin, y, 12, true);
    y -= 18;
    drawText(page, `Driver No-Show Evidence: ${driverNoShow.length} submission(s)`, margin, y, 10);
    y -= 14;
    drawText(page, `Rep No-Show Evidence: ${repNoShow.length} submission(s)`, margin, y, 10);
    y -= 14;
    drawText(page, `Rep In-Place Evidence: ${job.inPlaceEvidence.length} submission(s)`, margin, y, 10);
    y -= 14;
    drawText(page, `Rep Completed Evidence: ${job.completedEvidence.length} submission(s)`, margin, y, 10);
    y -= 14;

    const generatedAt = new Date().toLocaleString('en-GB', { timeZone: 'Africa/Cairo' });
    drawText(page, `Generated: ${generatedAt} (Cairo Time)`, margin, margin + 10, 8, false, rgb(0.5, 0.5, 0.5));

    // ── EVIDENCE PAGES ────────────────────────────────────────

    const sections: Array<{ title: string; entries: any[] }> = [
      { title: 'DRIVER NO-SHOW EVIDENCE', entries: driverNoShow },
      { title: 'REP NO-SHOW EVIDENCE', entries: repNoShow },
      { title: 'REP IN-PLACE EVIDENCE', entries: job.inPlaceEvidence },
      { title: 'REP COMPLETED EVIDENCE', entries: job.completedEvidence },
    ];

    for (const section of sections) {
      if (section.entries.length === 0) continue;

      for (const entry of section.entries) {
        const imagesOnPage = await this.embedImages(pdfDoc, entry.imageUrls ?? []);

        const evidencePage = pdfDoc.addPage([pageWidth, pageHeight]);
        let ey = pageHeight - margin;

        drawText(evidencePage, section.title, margin, ey, 14, true, rgb(0.1, 0.2, 0.6));
        ey -= 24;

        drawText(evidencePage, `Submitted by: ${entry.submittedBy ?? '-'}`, margin, ey, 10, true);
        ey -= 15;
        const gpsText =
          entry.gpsLatitude != null && entry.gpsLongitude != null
            ? `${entry.gpsLatitude}, ${entry.gpsLongitude}`
            : 'Not captured';
        drawText(evidencePage, `GPS: ${gpsText}`, margin, ey, 9);
        ey -= 13;
        drawText(evidencePage, `Map: ${entry.gpsMapLink ?? '-'}`, margin, ey, 9, false, rgb(0, 0.3, 0.7));
        ey -= 13;
        drawText(
          evidencePage,
          `Time: ${new Date(entry.createdAt).toLocaleString('en-GB', { timeZone: 'Africa/Cairo' })}`,
          margin,
          ey,
          9,
        );
        ey -= 20;

        evidencePage.drawLine({
          start: { x: margin, y: ey },
          end: { x: pageWidth - margin, y: ey },
          thickness: 0.5,
          color: rgb(0.8, 0.8, 0.8),
        });
        ey -= 16;

        if (imagesOnPage.length === 0) {
          drawText(evidencePage, '(No images)', margin, ey, 10, false, rgb(0.5, 0.5, 0.5));
        } else {
          // Two columns layout
          const imgMaxW = (contentWidth - 10) / 2;
          const imgMaxH = 200;

          let col = 0;
          for (const img of imagesOnPage) {
            const { width: iw, height: ih } = img.scale(1);
            const scale = Math.min(imgMaxW / iw, imgMaxH / ih, 1);
            const dw = iw * scale;
            const dh = ih * scale;

            if (ey - dh < margin + 20) {
              // New page for more images
              const cont = pdfDoc.addPage([pageWidth, pageHeight]);
              ey = pageHeight - margin;
              drawText(cont, `${section.title} (continued)`, margin, ey, 12, true, rgb(0.1, 0.2, 0.6));
              ey -= 24;
              col = 0;
            }

            const xPos = margin + col * (imgMaxW + 10);
            evidencePage.drawImage(img, {
              x: xPos,
              y: ey - dh,
              width: dw,
              height: dh,
            });

            col++;
            if (col >= 2) {
              col = 0;
              ey -= dh + 10;
            }
          }
        }

        drawText(
          evidencePage,
          `Generated: ${generatedAt} (Cairo Time)`,
          margin,
          margin + 10,
          8,
          false,
          rgb(0.5, 0.5, 0.5),
        );
      }
    }

    const pdfBytes = await pdfDoc.save();
    return Buffer.from(pdfBytes);
  }

  private async embedImages(
    pdfDoc: PDFDocument,
    imageUrls: string[],
  ): Promise<Awaited<ReturnType<PDFDocument['embedJpg']>>[]> {
    const embedded: Awaited<ReturnType<PDFDocument['embedJpg']>>[] = [];

    for (const url of imageUrls) {
      try {
        const filePath = path.join(process.cwd(), url.replace(/^\//, ''));
        if (!fs.existsSync(filePath)) continue;
        const bytes = fs.readFileSync(filePath);
        const lower = url.toLowerCase();
        if (lower.endsWith('.png')) {
          embedded.push(await pdfDoc.embedPng(bytes));
        } else {
          embedded.push(await pdfDoc.embedJpg(bytes));
        }
      } catch (err) {
        this.logger.warn(`Could not embed image ${url}: ${(err as Error).message}`);
      }
    }

    return embedded;
  }

  private buildRoute(job: any): string {
    const origin =
      job.originAirport?.code ||
      job.fromZone?.name ||
      job.originHotel?.name ||
      '-';
    const dest =
      job.destinationAirport?.code ||
      job.toZone?.name ||
      job.destinationHotel?.name ||
      '-';
    return `${origin} > ${dest}`;
  }

  private sanitize(text: string): string {
    return String(text ?? '')
      .replace(/\u2192/g, '>')
      .replace(/\u2014/g, '-')
      .replace(/\u2013/g, '-')
      .replace(/\u2026/g, '...')
      .replace(/[\u201C\u201D]/g, '"')
      .replace(/[\u2018\u2019]/g, "'")
      // eslint-disable-next-line no-control-regex
      .replace(/[^\x00-\xFF]/g, '?');
  }
}
