import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';
import * as XLSX from 'xlsx';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class InvoiceExportService {
  constructor(private readonly prisma: PrismaService) {}

  // ─────────────────────────────────────────────
  // SHARED: Fetch invoice with all relations
  // ─────────────────────────────────────────────

  private async fetchInvoiceData(invoiceId: string) {
    const invoice = await this.prisma.agentInvoice.findUnique({
      where: { id: invoiceId },
      include: {
        agent: true,
        customer: true,
        lines: {
          include: {
            trafficJob: {
              include: {
                fromZone: { select: { name: true } },
                toZone: { select: { name: true } },
                originAirport: { select: { code: true, name: true } },
                destinationAirport: { select: { code: true, name: true } },
                originHotel: { select: { name: true } },
                destinationHotel: { select: { name: true } },
                flight: { select: { flightNo: true, carrier: true } },
                jobExtras: { select: { name: true, qty: true } },
                assignment: {
                  include: {
                    vehicle: {
                      include: { vehicleType: { select: { name: true } } },
                    },
                  },
                },
                agent: { select: { legalName: true } },
              },
            },
          },
          orderBy: { createdAt: 'asc' },
        },
      },
    });

    if (!invoice) {
      throw new NotFoundException(`Invoice with ID "${invoiceId}" not found`);
    }

    const settings = await this.prisma.companySettings.findFirst();
    return { invoice, settings };
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

  private buildExtras(job: any): string {
    return (job.jobExtras ?? [])
      .filter((e: any) => e.qty > 0)
      .map((e: any) => `${e.name} x${e.qty}`)
      .join(', ');
  }

  private formatDate(date: Date | string): string {
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toISOString().split('T')[0];
  }

  private stripHtml(html: string | null | undefined): string {
    if (!html) return '';
    return html.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim();
  }

  /** Replace non-WinAnsi characters so pdf-lib StandardFonts don't crash */
  private sanitizeForPdf(text: string): string {
    return text
      .replace(/\u2192/g, '>')  // → arrow
      .replace(/\u2014/g, '-')  // — em dash
      .replace(/\u2013/g, '-')  // – en dash
      .replace(/\u2026/g, '...')  // … ellipsis
      .replace(/[\u201C\u201D]/g, '"')  // curly double quotes
      .replace(/[\u2018\u2019]/g, "'")  // curly single quotes
      // eslint-disable-next-line no-control-regex
      .replace(/[^\x00-\xFF]/g, '?');  // any remaining non-Latin1
  }

  // ─────────────────────────────────────────────
  // PDF GENERATION
  // ─────────────────────────────────────────────

  async generateInvoicePdf(invoiceId: string, userId?: string): Promise<Buffer> {
    const { invoice, settings } = await this.fetchInvoiceData(invoiceId);

    // Fetch generating user name for footer
    let generatedByName = '';
    if (userId) {
      const user = await this.prisma.user.findUnique({ where: { id: userId }, select: { name: true } });
      if (user) generatedByName = this.sanitizeForPdf(user.name);
    }

    const pdfDoc = await PDFDocument.create();
    const fontBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
    const fontRegular = await pdfDoc.embedFont(StandardFonts.Helvetica);

    // Load company logo
    let logoImage: Awaited<ReturnType<typeof pdfDoc.embedJpg>> | null = null;
    if (settings?.logoUrl) {
      try {
        const logoPath = path.join(process.cwd(), settings.logoUrl.replace(/^\//, ''));
        const logoBytes = fs.readFileSync(logoPath);
        const ext = settings.logoUrl.toLowerCase();
        if (ext.endsWith('.png')) {
          logoImage = await pdfDoc.embedPng(logoBytes);
        } else {
          logoImage = await pdfDoc.embedJpg(logoBytes);
        }
      } catch {
        // Logo not found, continue without
      }
    }

    // A4 Portrait dimensions
    const pageWidth = 595;
    const pageHeight = 842;
    const margin = 40;
    const contentWidth = pageWidth - 2 * margin;
    const footerText = this.sanitizeForPdf(this.stripHtml(settings?.reportFooterHtml));
    const headerText = this.sanitizeForPdf(this.stripHtml(settings?.reportHeaderHtml));

    // Resolve currency from agent if available, else from invoice
    const currency = invoice.agent?.currency || invoice.currency;

    // Table column config
    const cols = [
      { label: '#', width: 22 },
      { label: 'Date', width: 55 },
      { label: 'Agent Ref', width: 65 },
      { label: 'Service', width: 42 },
      { label: 'Route', width: 90 },
      { label: 'Pax', width: 25 },
      { label: 'Vehicle', width: 55 },
      { label: 'Extras', width: 75 },
      { label: 'Amount', width: 56 },
    ];
    const rowHeight = 18;
    const tableHeaderHeight = 22;

    // Prepare line data (sanitize for WinAnsi-safe PDF output)
    const lineRows = invoice.lines.map((line, idx) => {
      const job = line.trafficJob;
      return {
        num: String(idx + 1),
        date: job ? this.formatDate(job.jobDate) : '-',
        ref: this.sanitizeForPdf(job?.agentRef || '-'),
        service: job?.serviceType || '-',
        route: this.sanitizeForPdf(job ? this.buildRoute(job) : line.description),
        pax: job ? String(job.paxCount) : '-',
        vehicle: this.sanitizeForPdf(job?.assignment?.vehicle?.vehicleType?.name || '-'),
        extras: this.sanitizeForPdf(job ? this.buildExtras(job) : ''),
        amount: Number(line.lineTotal).toFixed(2),
      };
    });

    // Agent details for Bill To
    const agent = invoice.agent;
    const entityName = this.sanitizeForPdf(agent?.legalName || invoice.customer?.legalName || '-');
    const entityTrade = this.sanitizeForPdf(agent?.tradeName || '');

    let pageNum = 0;
    let lineIdx = 0;
    const totalPages = Math.max(1, Math.ceil((lineRows.length - 22) / 38) + 1);

    while (lineIdx < lineRows.length || pageNum === 0) {
      pageNum++;
      const page = pdfDoc.addPage([pageWidth, pageHeight]);
      let y = pageHeight - margin;

      // ── Page header (first page only) ──
      if (pageNum === 1) {
        // Company logo
        if (logoImage) {
          const logoDims = logoImage.scale(1);
          const maxLogoWidth = 180;
          const scale = Math.min(maxLogoWidth / logoDims.width, 60 / logoDims.height);
          const logoW = logoDims.width * scale;
          const logoH = logoDims.height * scale;
          page.drawImage(logoImage, {
            x: margin,
            y: y - logoH,
            width: logoW,
            height: logoH,
          });
          y -= logoH + 8;
        }

        // Header text (from settings)
        if (headerText) {
          page.drawText(headerText, {
            x: margin,
            y,
            size: 8,
            font: fontRegular,
            color: rgb(0.4, 0.4, 0.4),
            maxWidth: contentWidth / 2,
          });
          y -= 12;
        } else {
          y -= 6;
        }

        // Invoice info — right side
        const rightX = pageWidth - margin;
        const invoiceInfoY = pageHeight - margin - (logoImage ? 0 : 5);
        page.drawText(`Invoice: ${invoice.invoiceNumber}`, {
          x: rightX - fontBold.widthOfTextAtSize(`Invoice: ${invoice.invoiceNumber}`, 11),
          y: invoiceInfoY,
          size: 11,
          font: fontBold,
          color: rgb(0.1, 0.1, 0.1),
        });
        page.drawText(`Date: ${this.formatDate(invoice.invoiceDate)}`, {
          x: rightX - fontRegular.widthOfTextAtSize(`Date: ${this.formatDate(invoice.invoiceDate)}`, 9),
          y: invoiceInfoY - 14,
          size: 9,
          font: fontRegular,
          color: rgb(0.3, 0.3, 0.3),
        });
        page.drawText(`Due: ${this.formatDate(invoice.dueDate)}`, {
          x: rightX - fontRegular.widthOfTextAtSize(`Due: ${this.formatDate(invoice.dueDate)}`, 9),
          y: invoiceInfoY - 26,
          size: 9,
          font: fontRegular,
          color: rgb(0.3, 0.3, 0.3),
        });
        page.drawText(`Currency: ${currency}`, {
          x: rightX - fontRegular.widthOfTextAtSize(`Currency: ${currency}`, 9),
          y: invoiceInfoY - 38,
          size: 9,
          font: fontRegular,
          color: rgb(0.3, 0.3, 0.3),
        });
        const statusText = `Status: ${invoice.status}`;
        page.drawText(statusText, {
          x: rightX - fontRegular.widthOfTextAtSize(statusText, 9),
          y: invoiceInfoY - 50,
          size: 9,
          font: fontRegular,
          color: rgb(0.3, 0.3, 0.3),
        });

        // Separator line
        y -= 4;
        page.drawLine({
          start: { x: margin, y },
          end: { x: pageWidth - margin, y },
          thickness: 0.5,
          color: rgb(0.7, 0.7, 0.7),
        });
        y -= 16;

        // Agent/Customer info — Bill To
        page.drawText('Bill To:', {
          x: margin,
          y,
          size: 8,
          font: fontRegular,
          color: rgb(0.5, 0.5, 0.5),
        });
        y -= 14;
        page.drawText(entityName, {
          x: margin,
          y,
          size: 11,
          font: fontBold,
          color: rgb(0.1, 0.1, 0.1),
        });
        if (entityTrade) {
          y -= 13;
          page.drawText(entityTrade, {
            x: margin,
            y,
            size: 9,
            font: fontRegular,
            color: rgb(0.3, 0.3, 0.3),
          });
        }
        // Agent full details
        if (agent) {
          const detailColor = rgb(0.35, 0.35, 0.35);
          const detailSize = 8;
          if (agent.address || agent.city || agent.country) {
            y -= 12;
            const addr = [agent.address, agent.city, agent.country].filter(Boolean).join(', ');
            page.drawText(this.sanitizeForPdf(addr), {
              x: margin, y, size: detailSize, font: fontRegular, color: detailColor, maxWidth: contentWidth / 2,
            });
          }
          if (agent.taxId) {
            y -= 12;
            page.drawText(`Tax ID: ${this.sanitizeForPdf(agent.taxId)}`, {
              x: margin, y, size: detailSize, font: fontRegular, color: detailColor,
            });
          }
          if (agent.email) {
            y -= 12;
            page.drawText(`Email: ${this.sanitizeForPdf(agent.email)}`, {
              x: margin, y, size: detailSize, font: fontRegular, color: detailColor,
            });
          }
          if (agent.phone) {
            y -= 12;
            page.drawText(`Phone: ${this.sanitizeForPdf(agent.phone)}`, {
              x: margin, y, size: detailSize, font: fontRegular, color: detailColor,
            });
          }
        }
        y -= 16;
      }

      // ── Table header ──
      const tableTop = y;
      page.drawRectangle({
        x: margin,
        y: tableTop - tableHeaderHeight,
        width: contentWidth,
        height: tableHeaderHeight,
        color: rgb(0.25, 0.25, 0.3),
      });

      let colX = margin + 4;
      for (const col of cols) {
        page.drawText(col.label, {
          x: colX,
          y: tableTop - 15,
          size: 8,
          font: fontBold,
          color: rgb(1, 1, 1),
        });
        colX += col.width;
      }
      y = tableTop - tableHeaderHeight;

      // ── Table rows ──
      const bottomLimit = margin + 40; // space for footer + totals
      while (lineIdx < lineRows.length && y - rowHeight > bottomLimit) {
        const row = lineRows[lineIdx];
        const isEven = lineIdx % 2 === 0;

        if (isEven) {
          page.drawRectangle({
            x: margin,
            y: y - rowHeight,
            width: contentWidth,
            height: rowHeight,
            color: rgb(0.95, 0.95, 0.97),
          });
        }

        colX = margin + 4;
        const values = [row.num, row.date, row.ref, row.service, row.route, row.pax, row.vehicle, row.extras, row.amount];
        for (let i = 0; i < cols.length; i++) {
          let text = values[i];
          // Truncate to fit column
          const maxChars = Math.floor(cols[i].width / 4.5);
          if (text.length > maxChars) text = text.slice(0, maxChars - 2) + '..';

          const textX = i === cols.length - 1
            ? colX + cols[i].width - 4 - fontRegular.widthOfTextAtSize(text, 8)
            : colX;

          page.drawText(text, {
            x: textX,
            y: y - 13,
            size: 8,
            font: fontRegular,
            color: rgb(0.15, 0.15, 0.15),
          });
          colX += cols[i].width;
        }

        y -= rowHeight;
        lineIdx++;
      }

      // ── Totals (last page only or if all rows rendered) ──
      if (lineIdx >= lineRows.length) {
        y -= 10;
        page.drawLine({
          start: { x: pageWidth - margin - 170, y },
          end: { x: pageWidth - margin, y },
          thickness: 0.5,
          color: rgb(0.7, 0.7, 0.7),
        });
        y -= 16;

        const totalsX = pageWidth - margin - 170;
        const amountX = pageWidth - margin;

        // Subtotal
        const subtotalStr = Number(invoice.subtotal).toFixed(2);
        page.drawText('Subtotal', { x: totalsX, y, size: 9, font: fontRegular, color: rgb(0.3, 0.3, 0.3) });
        page.drawText(subtotalStr, {
          x: amountX - fontRegular.widthOfTextAtSize(subtotalStr, 9),
          y,
          size: 9,
          font: fontRegular,
          color: rgb(0.15, 0.15, 0.15),
        });
        y -= 14;

        // Tax
        if (Number(invoice.taxAmount) > 0) {
          const taxStr = Number(invoice.taxAmount).toFixed(2);
          page.drawText('Tax', { x: totalsX, y, size: 9, font: fontRegular, color: rgb(0.3, 0.3, 0.3) });
          page.drawText(taxStr, {
            x: amountX - fontRegular.widthOfTextAtSize(taxStr, 9),
            y,
            size: 9,
            font: fontRegular,
            color: rgb(0.15, 0.15, 0.15),
          });
          y -= 14;
        }

        // Total
        const totalStr = `${currency} ${Number(invoice.total).toFixed(2)}`;
        page.drawText('Total', { x: totalsX, y, size: 10, font: fontBold, color: rgb(0.1, 0.1, 0.1) });
        page.drawText(totalStr, {
          x: amountX - fontBold.widthOfTextAtSize(totalStr, 10),
          y,
          size: 10,
          font: fontBold,
          color: rgb(0.1, 0.1, 0.1),
        });
      }

      // ── Footer ──
      let footerY = margin + 14;
      if (footerText) {
        page.drawText(footerText, {
          x: margin,
          y: footerY,
          size: 7,
          font: fontRegular,
          color: rgb(0.5, 0.5, 0.5),
          maxWidth: contentWidth - 120,
        });
      }
      if (generatedByName) {
        footerY = margin + 2;
        page.drawText(`Generated by: ${generatedByName}`, {
          x: margin,
          y: footerY,
          size: 6.5,
          font: fontRegular,
          color: rgb(0.55, 0.55, 0.55),
        });
      }
      const pageLabel = `Page ${pageNum}`;
      page.drawText(pageLabel, {
        x: pageWidth - margin - fontRegular.widthOfTextAtSize(pageLabel, 7),
        y: margin + 14,
        size: 7,
        font: fontRegular,
        color: rgb(0.5, 0.5, 0.5),
      });
    }

    const pdfBytes = await pdfDoc.save();
    return Buffer.from(pdfBytes);
  }

  // ─────────────────────────────────────────────
  // EXCEL GENERATION
  // ─────────────────────────────────────────────

  async generateInvoiceExcel(invoiceId: string, userId?: string): Promise<Buffer> {
    const { invoice, settings } = await this.fetchInvoiceData(invoiceId);

    let generatedByName = '';
    if (userId) {
      const user = await this.prisma.user.findUnique({ where: { id: userId }, select: { name: true } });
      if (user) generatedByName = user.name;
    }

    const agent = invoice.agent;
    const entityName = agent?.legalName || invoice.customer?.legalName || '-';
    const currency = agent?.currency || invoice.currency;

    const data: (string | number | null)[][] = [];

    // Header rows
    data.push([
      `Invoice: ${invoice.invoiceNumber}`,
      null,
      null,
      `Date: ${this.formatDate(invoice.invoiceDate)}`,
      null,
      null,
      null,
      `Due: ${this.formatDate(invoice.dueDate)}`,
    ]);
    data.push([]);

    // Bill To block
    data.push([`Bill To: ${entityName}`]);
    if (agent) {
      if (agent.tradeName) data.push([`Trade Name: ${agent.tradeName}`]);
      if (agent.address || agent.city || agent.country) {
        data.push([[agent.address, agent.city, agent.country].filter(Boolean).join(', ')]);
      }
      if (agent.taxId) data.push([`Tax ID: ${agent.taxId}`]);
      if (agent.email) data.push([`Email: ${agent.email}`]);
      if (agent.phone) data.push([`Phone: ${agent.phone}`]);
    }
    data.push([
      null,
      null,
      null,
      `Currency: ${currency}`,
      null,
      null,
      null,
      `Status: ${invoice.status}`,
    ]);
    data.push([]); // separator

    // Table header
    data.push([
      '#', 'Date', 'Agent Ref', 'Service Type', 'Route', 'Pax', 'Vehicle', 'Extras',
      'Qty', 'Unit Price', 'Tax Rate %', 'Tax Amount', 'Total',
    ]);

    // Line items
    for (let i = 0; i < invoice.lines.length; i++) {
      const line = invoice.lines[i];
      const job = line.trafficJob;
      data.push([
        i + 1,
        job ? this.formatDate(job.jobDate) : '',
        job?.agentRef || '',
        job?.serviceType || '',
        job ? this.buildRoute(job) : line.description,
        job?.paxCount ?? '',
        job?.assignment?.vehicle?.vehicleType?.name || '',
        job ? this.buildExtras(job) : '',
        line.quantity,
        Number(line.unitPrice),
        Number(line.taxRate),
        Number(line.taxAmount),
        Number(line.lineTotal),
      ]);
    }

    // Totals
    data.push([]);
    data.push([null, null, null, null, null, null, null, null, null, null, null, 'Subtotal', Number(invoice.subtotal)]);
    if (Number(invoice.taxAmount) > 0) {
      data.push([null, null, null, null, null, null, null, null, null, null, null, 'Tax', Number(invoice.taxAmount)]);
    }
    data.push([null, null, null, null, null, null, null, null, null, null, null, 'TOTAL', Number(invoice.total)]);

    // Footer
    if (generatedByName) {
      data.push([]);
      data.push([`Generated by: ${generatedByName}`]);
    }

    const ws = XLSX.utils.aoa_to_sheet(data);
    ws['!cols'] = [
      { wch: 4 }, { wch: 12 }, { wch: 14 }, { wch: 14 }, { wch: 25 },
      { wch: 6 }, { wch: 15 }, { wch: 18 }, { wch: 6 }, { wch: 12 },
      { wch: 10 }, { wch: 12 }, { wch: 14 },
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Invoice');

    const buf = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
    return Buffer.from(buf);
  }
}
