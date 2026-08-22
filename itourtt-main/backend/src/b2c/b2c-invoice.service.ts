import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';
import { PrismaService } from '../prisma/prisma.service.js';
import type { B2CInvoiceStatus } from '../../generated/prisma/enums.js';

// One invoice per guest booking, created when the booking is paid. Kept simple
// and self-contained (the agent-invoice generator in finance/invoice-export is
// agent-specific). Fields stay Odoo-mappable for a later export.
@Injectable()
export class B2CInvoiceService {
  private readonly logger = new Logger(B2CInvoiceService.name);

  constructor(private readonly prisma: PrismaService) {}

  private readonly bookingInclude = {
    guestBooking: {
      include: {
        fromZone: { select: { name: true } },
        toZone: { select: { name: true } },
        originAirport: { select: { name: true } },
        destinationAirport: { select: { name: true } },
        hotel: { select: { name: true } },
        vehicleType: { select: { name: true } },
      },
    },
  } as const;

  // ─────────────────────────────────────────────
  // CREATE (idempotent)
  // ─────────────────────────────────────────────

  /**
   * Ensure a single invoice exists for the booking. Safe to call repeatedly
   * (e.g. on webhook re-delivery) — the unique guest_booking_id guarantees one
   * invoice per booking. Returns the invoice record.
   */
  async ensureForBooking(bookingId: string) {
    const existing = await this.prisma.b2CInvoice.findUnique({
      where: { guestBookingId: bookingId },
    });
    if (existing) return existing;

    const booking = await this.prisma.guestBooking.findUnique({
      where: { id: bookingId },
      select: {
        id: true,
        b2cClientId: true,
        subtotal: true,
        taxAmount: true,
        total: true,
        currency: true,
        paymentStatus: true,
      },
    });
    if (!booking) throw new NotFoundException(`Guest booking "${bookingId}" not found`);

    const status: B2CInvoiceStatus =
      booking.paymentStatus === 'PAID' ? 'PAID' : 'ISSUED';

    // Allocate the next sequential number, retrying on the (rare) race where two
    // payments settle at once and collide on the unique invoice_number.
    for (let attempt = 0; attempt < 5; attempt++) {
      const invoiceNumber = await this.nextInvoiceNumber();
      try {
        return await this.prisma.b2CInvoice.create({
          data: {
            invoiceNumber,
            guestBookingId: booking.id,
            b2cClientId: booking.b2cClientId,
            subtotal: booking.subtotal,
            taxAmount: booking.taxAmount,
            total: booking.total,
            currency: booking.currency,
            status,
          },
        });
      } catch (err: any) {
        // P2002 = unique constraint. Re-check for a booking-level invoice (another
        // worker may have created it), otherwise retry with a fresh number.
        if (err?.code === 'P2002') {
          const raced = await this.prisma.b2CInvoice.findUnique({
            where: { guestBookingId: bookingId },
          });
          if (raced) return raced;
          continue;
        }
        throw err;
      }
    }
    throw new Error('Could not allocate a unique invoice number after retries');
  }

  private async nextInvoiceNumber(): Promise<string> {
    const rows = await this.prisma.$queryRawUnsafe<{ invoice_number: string }[]>(
      `SELECT invoice_number FROM b2c_invoices WHERE invoice_number ~ '^INV-B2C-[0-9]+$' ORDER BY invoice_number DESC LIMIT 1`,
    );
    let next = 1;
    if (rows.length > 0) {
      const seq = parseInt(rows[0].invoice_number.split('-')[2], 10);
      if (!isNaN(seq)) next = seq + 1;
    }
    return `INV-B2C-${String(next).padStart(5, '0')}`;
  }

  // ─────────────────────────────────────────────
  // READ (ownership-scoped)
  // ─────────────────────────────────────────────

  async listForClient(clientId: string) {
    return this.prisma.b2CInvoice.findMany({
      where: { b2cClientId: clientId, deletedAt: null },
      orderBy: { issuedAt: 'desc' },
      select: {
        id: true,
        invoiceNumber: true,
        issuedAt: true,
        currency: true,
        total: true,
        status: true,
        guestBooking: {
          select: { bookingRef: true, jobDate: true, serviceType: true },
        },
      },
    });
  }

  /** Returns the PDF buffer + filename for an invoice the client owns. */
  async getOwnedPdf(clientId: string, invoiceId: string) {
    const invoice = await this.prisma.b2CInvoice.findFirst({
      where: { id: invoiceId, b2cClientId: clientId, deletedAt: null },
      select: { id: true },
    });
    if (!invoice) throw new NotFoundException('Invoice not found');
    return this.generatePdf(invoiceId);
  }

  // ─────────────────────────────────────────────
  // READ (admin — not ownership-scoped)
  // ─────────────────────────────────────────────

  /**
   * Paginated admin list of all B2C invoices, newest first. Access is gated by
   * the `finance.b2cInvoices` permission on the controller, so no client scope.
   */
  async listAll(params: {
    page?: number;
    limit?: number;
    search?: string;
    dateFrom?: string;
    dateTo?: string;
    status?: string;
  }) {
    const page = params.page && params.page > 0 ? params.page : 1;
    const limit = params.limit && params.limit > 0 ? params.limit : 20;
    const skip = (page - 1) * limit;

    const where: Record<string, unknown> = { deletedAt: null };

    if (params.status) {
      where.status = params.status as B2CInvoiceStatus;
    }

    if (params.dateFrom || params.dateTo) {
      const issuedAt: Record<string, Date> = {};
      if (params.dateFrom) issuedAt.gte = new Date(params.dateFrom);
      if (params.dateTo) {
        // Include the whole `dateTo` day.
        const to = new Date(params.dateTo);
        to.setHours(23, 59, 59, 999);
        issuedAt.lte = to;
      }
      where.issuedAt = issuedAt;
    }

    if (params.search?.trim()) {
      const q = params.search.trim();
      where.OR = [
        { invoiceNumber: { contains: q, mode: 'insensitive' } },
        { guestBooking: { is: { bookingRef: { contains: q, mode: 'insensitive' } } } },
        { guestBooking: { is: { guestName: { contains: q, mode: 'insensitive' } } } },
        { guestBooking: { is: { guestEmail: { contains: q, mode: 'insensitive' } } } },
      ];
    }

    const [data, total] = await Promise.all([
      this.prisma.b2CInvoice.findMany({
        where,
        skip,
        take: limit,
        orderBy: { issuedAt: 'desc' },
        select: {
          id: true,
          invoiceNumber: true,
          issuedAt: true,
          currency: true,
          subtotal: true,
          taxAmount: true,
          total: true,
          status: true,
          guestBooking: {
            select: {
              bookingRef: true,
              guestName: true,
              guestEmail: true,
              jobDate: true,
              serviceType: true,
            },
          },
        },
      }),
      this.prisma.b2CInvoice.count({ where }),
    ]);

    return {
      data,
      meta: { total, page, limit, totalPages: Math.ceil(total / limit) },
    };
  }

  /** Admin PDF download — access gated by the controller permission. */
  async getPdfById(invoiceId: string) {
    return this.generatePdf(invoiceId);
  }

  // ─────────────────────────────────────────────
  // PDF
  // ─────────────────────────────────────────────

  /** Generate the invoice PDF. Returns the buffer + a download filename. */
  async generatePdf(invoiceId: string): Promise<{ buffer: Buffer; filename: string }> {
    const invoice = await this.prisma.b2CInvoice.findUnique({
      where: { id: invoiceId },
      include: this.bookingInclude,
    });
    if (!invoice) throw new NotFoundException('Invoice not found');

    const [company, website] = await Promise.all([
      this.prisma.companySettings.findFirst(),
      this.prisma.websiteSettings.findFirst(),
    ]);
    const brandName = this.s(website?.siteName || company?.companyName || 'Transfera');
    const issuerName = this.s(company?.companyName || 'iTour Transport & Traffic');

    const b = invoice.guestBooking;
    const origin = b.originAirport?.name || b.fromZone?.name || '-';
    const dest = b.destinationAirport?.name || b.toZone?.name || '-';
    const serviceLabel =
      b.serviceType === 'ARR' ? 'Arrival transfer'
      : b.serviceType === 'DEP' ? 'Departure transfer'
      : 'City transfer';

    const pdf = await PDFDocument.create();
    const page = pdf.addPage([595, 842]); // A4 portrait
    const bold = await pdf.embedFont(StandardFonts.HelveticaBold);
    const reg = await pdf.embedFont(StandardFonts.Helvetica);
    const dark = rgb(0.1, 0.1, 0.1);
    const grey = rgb(0.45, 0.45, 0.45);

    const M = 50;
    let y = 792;

    // Header
    page.drawText(this.s(brandName), { x: M, y, size: 20, font: bold, color: dark });
    page.drawText('INVOICE', { x: 595 - M - bold.widthOfTextAtSize('INVOICE', 20), y, size: 20, font: bold, color: rgb(0.85, 0.7, 0.1) });
    y -= 16;
    page.drawText(this.s(issuerName), { x: M, y, size: 9, font: reg, color: grey });
    y -= 30;

    // Invoice meta (right) + Bill-to (left)
    const metaX = 360;
    let metaY = y;
    const meta: [string, string][] = [
      ['Invoice No.', invoice.invoiceNumber],
      ['Date', this.fmtDate(invoice.issuedAt)],
      ['Booking Ref', b.bookingRef],
      ['Status', invoice.status],
    ];
    for (const [label, value] of meta) {
      page.drawText(label, { x: metaX, y: metaY, size: 9, font: reg, color: grey });
      page.drawText(this.s(value), { x: metaX + 80, y: metaY, size: 9, font: bold, color: dark });
      metaY -= 16;
    }

    page.drawText('Bill To:', { x: M, y, size: 9, font: bold, color: dark });
    let billY = y - 16;
    for (const line of [b.guestName, b.guestEmail, b.guestPhone].filter(Boolean)) {
      page.drawText(this.s(line as string), { x: M, y: billY, size: 9, font: reg, color: dark });
      billY -= 14;
    }

    y = Math.min(billY, metaY) - 24;

    // Line items header
    page.drawRectangle({ x: M, y: y - 4, width: 595 - 2 * M, height: 22, color: rgb(0.96, 0.96, 0.96) });
    page.drawText('Description', { x: M + 8, y: y + 2, size: 9, font: bold, color: dark });
    page.drawText('Amount', { x: 595 - M - 8 - bold.widthOfTextAtSize('Amount', 9), y: y + 2, size: 9, font: bold, color: dark });
    y -= 26;

    // Single line: the transfer
    const desc = this.s(`${serviceLabel}: ${origin} > ${dest}`);
    const sub = `${b.jobDate ? this.fmtDate(b.jobDate) : ''} · ${b.paxCount} pax · ${this.s(b.vehicleType?.name || '')}`;
    page.drawText(desc, { x: M + 8, y, size: 10, font: reg, color: dark });
    const amountStr = `${invoice.currency} ${Number(invoice.subtotal).toFixed(2)}`;
    page.drawText(amountStr, { x: 595 - M - 8 - reg.widthOfTextAtSize(amountStr, 10), y, size: 10, font: reg, color: dark });
    y -= 14;
    page.drawText(this.s(sub), { x: M + 8, y, size: 8, font: reg, color: grey });
    y -= 30;

    // Totals
    const totalsX = 360;
    const drawTotal = (label: string, value: string, strong = false) => {
      const f = strong ? bold : reg;
      page.drawText(label, { x: totalsX, y, size: strong ? 11 : 9, font: f, color: strong ? dark : grey });
      page.drawText(value, { x: 595 - M - 8 - f.widthOfTextAtSize(value, strong ? 11 : 9), y, size: strong ? 11 : 9, font: f, color: strong ? dark : grey });
      y -= strong ? 20 : 16;
    };
    drawTotal('Subtotal', `${invoice.currency} ${Number(invoice.subtotal).toFixed(2)}`);
    if (Number(invoice.taxAmount) > 0) {
      drawTotal('Tax', `${invoice.currency} ${Number(invoice.taxAmount).toFixed(2)}`);
    }
    page.drawLine({ start: { x: totalsX, y: y + 4 }, end: { x: 595 - M, y: y + 4 }, thickness: 0.5, color: rgb(0.8, 0.8, 0.8) });
    y -= 6;
    drawTotal('Total', `${invoice.currency} ${Number(invoice.total).toFixed(2)}`, true);

    // Footer
    page.drawText(
      this.s(`Thank you for choosing ${brandName}.`),
      { x: M, y: 60, size: 9, font: reg, color: grey },
    );

    const bytes = await pdf.save();
    return { buffer: Buffer.from(bytes), filename: `${invoice.invoiceNumber}.pdf` };
  }

  // ── helpers ──
  private fmtDate(date: Date | string): string {
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toISOString().split('T')[0];
  }

  /** Replace non-WinAnsi characters so pdf-lib StandardFonts don't crash. */
  private s(text: string): string {
    return text
      .replace(/→/g, '>')
      .replace(/[—–]/g, '-')
      .replace(/…/g, '...')
      .replace(/[“”]/g, '"')
      .replace(/[‘’]/g, "'")
      // eslint-disable-next-line no-control-regex
      .replace(/[^\x00-\xFF]/g, '?');
  }
}
