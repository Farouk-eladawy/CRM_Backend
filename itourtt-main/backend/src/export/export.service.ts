import { Injectable, Logger, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import { GoogleDriveService, isDriveFileId } from '../google-drive/google-drive.service.js';
import { calcRepScore, scoreToFeeAndEval } from '../common/utils/rep-score.util.js';
import * as XLSX from 'xlsx';
import { PDFDocument, rgb } from 'pdf-lib';
import fontkit from '@pdf-lib/fontkit';
import * as fs from 'fs';
import * as path from 'path';
import { createRequire } from 'module';
import sharp from 'sharp';
import archiver from 'archiver';
import type { Response } from 'express';
import { serviceTypeLabel, NON_FLIGHT_SERVICE_TYPES } from '../common/utils/service-type.util.js';

const _require = createRequire(import.meta.url);
const { convertArabic } = _require('arabic-reshaper') as { convertArabic: (t: string) => string };
const bidi = _require('bidi-js') as (text: string, opts: Record<string, unknown>) => {
  getEmbeddingLevels: (text: string, opts: Record<string, unknown>) => unknown;
  getReorderedString: (text: string, levels: unknown) => string;
};

/** Returns true if the string contains any Arabic Unicode characters. */
function hasArabic(text: string): boolean {
  return /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/.test(text);
}

/**
 * Normalises a logoUrl that may be stored as a full URL (e.g. http://localhost:3001/uploads/x.jpg)
 * or as a relative path (/uploads/x.jpg) into a local filesystem path.
 */
function resolveLogoPath(logoUrl: string): string {
  if (logoUrl.startsWith('http://') || logoUrl.startsWith('https://')) {
    const pathname = new URL(logoUrl).pathname; // e.g. /uploads/x.jpg
    return path.join(process.cwd(), pathname.replace(/^\//, ''));
  }
  return path.join(process.cwd(), logoUrl.replace(/^\//, ''));
}

/**
 * Loads a logo file and embeds it into the PDF document.
 * Supports JPEG, PNG, and SVG (SVG is rasterised to PNG via sharp).
 * Returns null if the logo cannot be loaded.
 */
async function embedLogo(
  pdfDoc: PDFDocument,
  logoUrl: string,
): Promise<Awaited<ReturnType<typeof pdfDoc.embedPng>> | null> {
  try {
    const logoPath = resolveLogoPath(logoUrl);
    const ext = logoUrl.toLowerCase();
    if (ext.endsWith('.svg')) {
      // Rasterise SVG → PNG with a fixed height; sharp handles width automatically
      const pngBytes = await sharp(logoPath).png().toBuffer();
      return await pdfDoc.embedPng(pngBytes);
    }
    const bytes = fs.readFileSync(logoPath);
    if (ext.endsWith('.png')) {
      return await pdfDoc.embedPng(bytes);
    }
    return await pdfDoc.embedJpg(bytes);
  } catch {
    return null;
  }
}

/** Reshape + visually reorder Arabic text so pdf-lib renders it correctly.
 *  Passes through unchanged if the text contains no Arabic characters. */
function arabicize(text: string): string {
  if (!text || !hasArabic(text)) return text;
  const reshaped = convertArabic(text);
  const bidiObj = bidi(reshaped, { defaultParaLevel: 1 });
  return bidiObj.getReorderedString(
    reshaped,
    bidiObj.getEmbeddingLevels(reshaped, { defaultParaLevel: 1 }),
  );
}

/** Resolve the absolute paths to the bundled fonts. */
function fontPaths() {
  const base = path.join(process.cwd(), 'fonts');
  return {
    arabicRegular: path.join(base, 'Cairo-Regular.woff2'),
    arabicBold:    path.join(base, 'Cairo-Bold.woff2'),
    latinRegular:  path.join(base, 'DejaVuSans-Regular.ttf'),
    latinBold:     path.join(base, 'DejaVuSans-Bold.ttf'),
  };
}

@Injectable()
export class ExportService {
  private readonly logger = new Logger(ExportService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly googleDrive: GoogleDriveService,
  ) {}

  // ─────────────────────────────────────────────
  // CUSTOMERS (Agent → res.partner)
  // ─────────────────────────────────────────────

  async exportCustomers(): Promise<Buffer> {
    const agents = await this.fetchAllInBatches((cursor) =>
      this.prisma.agent.findMany({
        where: { deletedAt: null },
        include: { creditTerms: true },
        orderBy: { legalName: 'asc' },
        take: 1000,
        ...(cursor ? { skip: 1, cursor: { id: cursor } } : {}),
      }),
    );

    const rows = agents.map((a) => ({
      name: a.legalName,
      company_type: 'company',
      is_company: true,
      street: a.address || '',
      city: a.city || '',
      country_id: a.country || 'Egypt',
      phone: a.phone || '',
      email: a.email || '',
      vat: a.taxId || '',
      customer_rank: 1,
      supplier_rank: 0,
      property_payment_term_id: a.creditTerms
        ? `${a.creditTerms.creditDays} Days`
        : '',
      property_account_receivable_id: '120000',
      property_account_payable_id: '210000',
      ref: a.id,
    }));

    return this.createWorkbook(rows, 'res.partner');
  }

  // ─────────────────────────────────────────────
  // SUPPLIERS (Supplier → res.partner)
  // ─────────────────────────────────────────────

  async exportSuppliers(): Promise<Buffer> {
    const suppliers = await this.fetchAllInBatches((cursor) =>
      this.prisma.supplier.findMany({
        where: { deletedAt: null },
        orderBy: { legalName: 'asc' },
        take: 1000,
        ...(cursor ? { skip: 1, cursor: { id: cursor } } : {}),
      }),
    );

    const rows = suppliers.map((s) => ({
      name: s.legalName,
      company_type: 'company',
      is_company: true,
      street: s.address || '',
      city: s.city || '',
      country_id: s.country || 'Egypt',
      phone: s.phone || '',
      email: s.email || '',
      vat: s.taxId || '',
      customer_rank: 0,
      supplier_rank: 1,
      property_account_receivable_id: '120000',
      property_account_payable_id: '210000',
      ref: s.id,
    }));

    return this.createWorkbook(rows, 'res.partner');
  }

  // ─────────────────────────────────────────────
  // CUSTOMER INVOICES (AgentInvoice → account.move out_invoice)
  // ─────────────────────────────────────────────

  async exportInvoices(dateFrom?: string, dateTo?: string): Promise<Buffer> {
    const dateFilter = this.buildDateFilter(dateFrom, dateTo, 'invoiceDate');
    const invoices = await this.prisma.agentInvoice.findMany({
      where: { status: { not: 'CANCELLED' }, ...dateFilter },
      include: {
        agent: true,
        customer: true,
        lines: {
          include: {
            trafficJob: true,
          },
        },
      },
      orderBy: { invoiceDate: 'asc' },
      take: 50_000,
    });

    const rows: Record<string, unknown>[] = [];

    for (const inv of invoices) {
      const partnerName = inv.agent?.legalName || inv.customer?.legalName || 'Unknown';
      for (const line of inv.lines) {
        rows.push({
          move_type: 'out_invoice',
          partner_id: partnerName,
          invoice_date: this.formatDate(inv.invoiceDate),
          invoice_date_due: this.formatDate(inv.dueDate),
          currency_id: inv.currency,
          journal_id: 'Customer Invoices',
          ref: inv.invoiceNumber,
          name: line.description,
          account_id: '400000',
          quantity: line.quantity,
          price_unit: Number(line.unitPrice),
          tax_ids: Number(line.taxRate) > 0 ? `VAT ${line.taxRate}%` : '',
          amount_currency: Number(line.lineTotal),
          external_reference: line.trafficJob?.internalRef || '',
        });
      }
    }

    return this.createWorkbook(rows, 'account.move');
  }

  // ─────────────────────────────────────────────
  // VENDOR BILLS (SupplierCost → account.move in_invoice)
  // ─────────────────────────────────────────────

  async exportVendorBills(dateFrom?: string, dateTo?: string): Promise<Buffer> {
    const dateFilter = this.buildDateFilter(dateFrom, dateTo, 'createdAt');
    const costs = await this.prisma.supplierCost.findMany({
      where: { ...dateFilter },
      include: {
        supplier: true,
        trafficJob: {
          include: {
            agent: true,
            fromZone: true,
            toZone: true,
          },
        },
      },
      orderBy: { createdAt: 'asc' },
      take: 50_000,
    });

    const rows = costs.map((c) => {
      const job = c.trafficJob;
      const routeDesc = job.fromZone && job.toZone
        ? `${job.fromZone.name} → ${job.toZone.name}`
        : job.internalRef;

      return {
        move_type: 'in_invoice',
        partner_id: c.supplier.legalName,
        invoice_date: this.formatDate(c.createdAt),
        currency_id: c.currency,
        journal_id: 'Vendor Bills',
        ref: job.internalRef,
        name: `Transport: ${routeDesc} (${serviceTypeLabel(job.serviceType)})`,
        account_id: '510000',
        quantity: 1,
        price_unit: Number(c.amount),
        tax_ids: '',
        amount_currency: Number(c.amount),
        external_reference: job.internalRef,
      };
    });

    return this.createWorkbook(rows, 'account.move');
  }

  // ─────────────────────────────────────────────
  // PAYMENTS (Payment → account.payment)
  // ─────────────────────────────────────────────

  async exportPayments(dateFrom?: string, dateTo?: string): Promise<Buffer> {
    const dateFilter = this.buildDateFilter(dateFrom, dateTo, 'paymentDate');
    const payments = await this.prisma.payment.findMany({
      where: { ...dateFilter },
      include: {
        agentInvoice: {
          include: {
            agent: true,
            customer: true,
          },
        },
      },
      orderBy: { paymentDate: 'asc' },
      take: 50_000,
    });

    const rows = payments.map((p) => ({
      payment_type: 'inbound',
      partner_type: 'customer',
      partner_id: p.agentInvoice.agent?.legalName || p.agentInvoice.customer?.legalName || 'Unknown',
      amount: Number(p.amount),
      currency_id: p.currency,
      journal_id: this.mapPaymentJournal(p.paymentMethod),
      date: this.formatDate(p.paymentDate),
      ref: p.agentInvoice.invoiceNumber,
      communication: p.reference || p.agentInvoice.invoiceNumber,
    }));

    return this.createWorkbook(rows, 'account.payment');
  }

  // ─────────────────────────────────────────────
  // JOURNAL ENTRIES
  // ─────────────────────────────────────────────

  async exportJournalEntries(dateFrom?: string, dateTo?: string): Promise<Buffer> {
    const dateFilter = this.buildDateFilter(dateFrom, dateTo, 'entryDate');
    const entries = await this.prisma.journalEntry.findMany({
      where: { ...dateFilter },
      include: {
        lines: {
          include: {
            account: true,
          },
        },
      },
      orderBy: { entryDate: 'asc' },
      take: 50_000,
    });

    const rows: Record<string, unknown>[] = [];

    for (const entry of entries) {
      for (const line of entry.lines) {
        rows.push({
          journal_id: this.mapJournalType(entry.journalType),
          date: this.formatDate(entry.entryDate),
          ref: entry.entryNumber,
          name: entry.description || '',
          account_id: line.account.code,
          debit: Number(line.debit),
          credit: Number(line.credit),
          currency_id: line.currency,
          amount_currency:
            Number(line.debit) > 0
              ? Number(line.debit)
              : -Number(line.credit),
        });
      }
    }

    return this.createWorkbook(rows, 'account.move.line');
  }

  // ─────────────────────────────────────────────
  // COLLECTIONS EXPORT
  // ─────────────────────────────────────────────

  async exportCollections(status?: string, dateFrom?: string, dateTo?: string): Promise<Buffer> {
    const where: any = { collectionRequired: true };

    if (status === 'PENDING') {
      where.collectionCollected = false;
    } else if (status === 'COLLECTED') {
      where.collectionCollected = true;
      where.collectionLiquidatedAt = null;
    } else if (status === 'LIQUIDATED') {
      where.collectionLiquidatedAt = { not: null };
    }

    if (dateFrom || dateTo) {
      where.jobDate = {};
      if (dateFrom) where.jobDate.gte = new Date(dateFrom);
      if (dateTo) where.jobDate.lte = new Date(dateTo);
    }

    const jobs = await this.prisma.trafficJob.findMany({
      where,
      include: {
        agent: { select: { legalName: true } },
        customer: { select: { legalName: true } },
        assignment: { include: { driver: { select: { name: true } } } },
      },
      orderBy: { jobDate: 'desc' },
    });

    const rows = jobs.map((j) => {
      let collectionStatus = 'PENDING';
      if (j.collectionLiquidatedAt) collectionStatus = 'LIQUIDATED';
      else if (j.collectionCollected) collectionStatus = 'COLLECTED';

      return {
        job_reference: j.internalRef,
        job_date: this.formatDate(j.jobDate),
        partner_name: j.agent?.legalName || j.customer?.legalName || '',
        driver_name: j.assignment?.driver?.name || '',
        collection_amount: j.collectionAmount ? Number(j.collectionAmount) : 0,
        collection_currency: j.collectionCurrency || 'EGP',
        status: collectionStatus,
        receipt_no: j.collectionReceiptNo || '',
        collected_at: j.collectionCollectedAt ? this.formatDate(j.collectionCollectedAt) : '',
        liquidated_at: j.collectionLiquidatedAt ? this.formatDate(j.collectionLiquidatedAt) : '',
      };
    });

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    this.autoSizeColumns(ws, rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Collections');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // REP FEES REPORT
  // ─────────────────────────────────────────────

  async exportRepFees(from: string, to: string): Promise<Buffer> {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const assignments = await this.prisma.trafficAssignment.findMany({
      where: {
        repId: { not: null },
        trafficJob: {
          jobDate: { gte: fromDate, lte: toDate },
          deletedAt: null,
        },
      },
      include: {
        rep: true,
        trafficJob: {
          include: {
            fromZone: true,
            toZone: true,
            flight: true,
            repFees: true,
          },
        },
      },
    });

    // Build summary rows aggregated by rep
    const repMap = new Map<
      string,
      { name: string; feePerFlight: number; flights: number; total: number }
    >();

    const detailRows: Record<string, unknown>[] = [];

    for (const a of assignments) {
      if (!a.rep) continue;
      const repId = a.repId!;
      const feePerFlight = Number(a.rep.feePerFlight);
      const isArr = a.trafficJob.serviceType === 'ARR';
      const existingFee = a.trafficJob.repFees.find((f) => f.repId === repId);
      const amount = existingFee
        ? Number(existingFee.amount)
        : isArr
          ? feePerFlight
          : 0;

      if (isArr) {
        const existing = repMap.get(repId);
        if (existing) {
          existing.flights++;
          existing.total += amount;
        } else {
          repMap.set(repId, {
            name: a.rep.name,
            feePerFlight,
            flights: 1,
            total: amount,
          });
        }
      }

      detailRows.push({
        'Rep Name': a.rep.name,
        'Service Type': serviceTypeLabel(a.trafficJob.serviceType),
        'Flight No': a.trafficJob.flight?.flightNo || '—',
        Carrier: a.trafficJob.flight?.carrier || '—',
        'Job Ref': a.trafficJob.internalRef,
        Pax: a.trafficJob.paxCount,
        Route:
          a.trafficJob.fromZone && a.trafficJob.toZone
            ? `${a.trafficJob.fromZone.name} → ${a.trafficJob.toZone.name}`
            : '—',
        Status: a.trafficJob.status,
        'Fee Amount': amount,
      });
    }

    const summaryRows = Array.from(repMap.values()).map((r) => ({
      'Rep Name': r.name,
      'Fee/Flight': r.feePerFlight,
      Flights: r.flights,
      Total: r.total,
    }));

    // Grand total row
    const grandTotal = summaryRows.reduce((sum, r) => sum + r.Total, 0);
    summaryRows.push({
      'Rep Name': 'GRAND TOTAL',
      'Fee/Flight': 0,
      Flights: summaryRows.reduce((sum, r) => sum + r.Flights, 0),
      Total: grandTotal,
    });

    // Create multi-sheet workbook
    const wb = XLSX.utils.book_new();

    const summaryWs = XLSX.utils.json_to_sheet(summaryRows);
    this.autoSizeColumns(summaryWs, summaryRows);
    XLSX.utils.book_append_sheet(wb, summaryWs, 'Summary');

    if (detailRows.length > 0) {
      const detailWs = XLSX.utils.json_to_sheet(detailRows);
      this.autoSizeColumns(detailWs, detailRows);
      XLSX.utils.book_append_sheet(wb, detailWs, 'Details');
    }

    const buf = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
    return Buffer.from(buf);
  }

  // ─────────────────────────────────────────────
  // DISPATCH DAY EXPORT
  // ─────────────────────────────────────────────

  async exportDispatchDay(date: string): Promise<Buffer> {
    const jobDate = new Date(date);

    const baseInclude = {
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
      flight: true,
      jobExtras: { orderBy: { createdAt: 'asc' as const } },
      assignment: {
        include: {
          vehicle: { include: { vehicleType: true } },
          driver: true,
          rep: true,
          supplier: true,
          supplierCarType: { include: { vehicleType: true } },
        },
      },
    };

    const baseWhere = { jobDate, deletedAt: null };

    const [arrivals, departures, otherJobs] = await Promise.all([
      this.prisma.trafficJob.findMany({
        where: { ...baseWhere, serviceType: 'ARR' as any },
        include: baseInclude,
        orderBy: [{ flight: { arrivalTime: 'asc' } }, { createdAt: 'asc' }],
      }),
      this.prisma.trafficJob.findMany({
        where: { ...baseWhere, serviceType: 'DEP' as any },
        include: baseInclude,
        orderBy: [{ flight: { departureTime: 'asc' } }, { createdAt: 'asc' }],
      }),
      this.prisma.trafficJob.findMany({
        where: { ...baseWhere, serviceType: { in: NON_FLIGHT_SERVICE_TYPES as any } },
        include: baseInclude,
        orderBy: { createdAt: 'asc' },
      }),
    ]);

    const mapJob = (job: any): Record<string, unknown> => {
      const origin =
        job.originAirport?.code ||
        job.originZone?.name ||
        job.originHotel?.name ||
        '';
      const destination =
        job.destinationAirport?.code ||
        job.destinationZone?.name ||
        job.destinationHotel?.name ||
        '';
      const fmtTime = (d: Date | string | null | undefined) => {
        if (!d) return '';
        const dt = new Date(d);
        return `${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`;
      };

      const a = job.assignment;
      const isOwned = !a?.supplierId;
      const supplierName = a?.supplier?.tradeName || a?.supplier?.legalName || '';
      // Own car has a plate; supplier car is identified by its supplier name.
      const vehicle = isOwned
        ? (a?.vehicle?.plateNumber || '')
        : supplierName;
      const vehicleType =
        a?.vehicle?.vehicleType?.name || a?.supplierCarType?.vehicleType?.name || '';
      const seatCapacity =
        a?.vehicle?.vehicleType?.seatCapacity ??
        a?.supplierCarType?.vehicleType?.seatCapacity ??
        '';
      const driverName = isOwned
        ? (a?.driver?.name || '')
        : (a?.externalDriverName || supplierName || '');
      const driverMobile = isOwned
        ? (a?.driver?.mobileNumber || '')
        : (a?.externalDriverPhone || '');

      return {
        'Ref': job.internalRef,
        'Agent Ref': job.agentRef || '',
        'Channel': job.bookingChannel,
        'Status': job.status,
        'Agent / Customer':
          job.agent?.legalName || job.customer?.legalName || '',
        'Client Name': job.clientName || '',
        'Client Mobile': job.clientMobile || '',
        'Cust Rep Name': job.custRepName || '',
        'Cust Rep Mobile': job.custRepMobile || '',
        'Meeting Point': job.custRepMeetingPoint || '',
        'Meeting Time': fmtTime(job.custRepMeetingTime),
        'Origin': origin,
        'Destination': destination,
        'From Zone': job.fromZone?.name || '',
        'To Zone': job.toZone?.name || '',
        'Adults': job.adultCount,
        'Children': job.childCount,
        'Pax': job.paxCount,
        'Pick-Up Time': fmtTime(job.pickUpTime),
        'Flight No': job.flight?.flightNo || '',
        'Carrier': job.flight?.carrier || '',
        'Terminal': job.flight?.terminal || '',
        'Arrival Time': fmtTime(job.flight?.arrivalTime),
        'Departure Time': fmtTime(job.flight?.departureTime),
        'Vehicle': vehicle,
        'Vehicle Type': vehicleType,
        'Seat Capacity': seatCapacity,
        'Driver': driverName,
        'Driver Mobile': driverMobile,
        'Rep': job.assignment?.rep?.name || '',
        'Rep Mobile': job.assignment?.rep?.mobileNumber || '',
        'Extras': (job.jobExtras ?? [])
          .filter((e: any) => e.qty > 0)
          .map((e: any) => `${e.name} x${e.qty}`)
          .join(', '),
        'Print Sign': job.printSign ? 'Yes' : 'No',
        'Notes': job.notes || '',
      };
    };

    const wb = XLSX.utils.book_new();

    const addSheet = (name: string, jobs: any[]) => {
      const rows = jobs.map(mapJob);
      if (rows.length === 0) {
        // Add empty sheet with headers only
        const headers = Object.keys(mapJob({
          internalRef: '', bookingChannel: '', status: '',
          adultCount: '', childCount: '', paxCount: '',
          jobExtras: [],
          printSign: false,
        }));
        const ws = XLSX.utils.aoa_to_sheet([headers]);
        XLSX.utils.book_append_sheet(wb, ws, name);
      } else {
        const ws = XLSX.utils.json_to_sheet(rows);
        this.autoSizeColumns(ws, rows);
        XLSX.utils.book_append_sheet(wb, ws, name);
      }
    };

    addSheet('Arrivals', arrivals);
    addSheet('Departures', departures);
    addSheet('Other Services', otherJobs);

    const buf = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
    return Buffer.from(buf);
  }

  // ─────────────────────────────────────────────
  // CLIENT SIGNS PDF
  // ─────────────────────────────────────────────

  async generateClientSigns(date: string): Promise<Buffer> {
    const jobDate = new Date(date);

    // Fetch company settings for logo
    const settings = await this.prisma.companySettings.findFirst();
    const logoUrl = settings?.logoUrl; // e.g. "/uploads/filename.jpg"

    // Fetch jobs with printSign=true for the given date
    const jobs = await this.prisma.trafficJob.findMany({
      where: {
        jobDate,
        printSign: true,
        clientName: { not: null },
        deletedAt: null,
      },
      include: { assignment: { include: { rep: true } } },
      orderBy: { createdAt: 'asc' },
    });

    if (jobs.length === 0) {
      throw new Error('NO_SIGN_JOBS');
    }

    const pdfDoc = await PDFDocument.create();
    pdfDoc.registerFontkit(fontkit);

    const fp = fontPaths();
    const latinFont    = await pdfDoc.embedFont(fs.readFileSync(fp.latinRegular));
    const latinBold    = await pdfDoc.embedFont(fs.readFileSync(fp.latinBold));
    const arabicFont   = await pdfDoc.embedFont(fs.readFileSync(fp.arabicRegular));
    const arabicBold   = await pdfDoc.embedFont(fs.readFileSync(fp.arabicBold));

    /** Pick the right font: Cairo Arabic for Arabic text, DejaVu Sans otherwise. */
    const pickFont = (text: string, isBold = false) =>
      hasArabic(text) ? (isBold ? arabicBold : arabicFont) : (isBold ? latinBold : latinFont);

    // Load logo if available
    const logoImage = logoUrl ? await embedLogo(pdfDoc, logoUrl) : null;

    // Landscape A4: 842 x 595 pt
    const pageWidth = 842;
    const pageHeight = 595;
    const margin = 30;

    for (const job of jobs) {
      const page = pdfDoc.addPage([pageWidth, pageHeight]);
      const clientName = job.clientName || '';

      // Draw border rectangle
      page.drawRectangle({
        x: margin,
        y: margin,
        width: pageWidth - 2 * margin,
        height: pageHeight - 2 * margin,
        borderColor: rgb(0, 0, 0),
        borderWidth: 2,
      });

      let currentY = pageHeight - margin - 20;

      // Logo hidden until further notice
      currentY -= 60;

      // Draw "Mr/Mrs" text below logo, left-aligned
      page.drawText('Mr/Mrs', {
        x: margin + 30,
        y: currentY,
        size: 18,
        font: latinFont,
        color: rgb(0.3, 0.3, 0.3),
      });

      currentY -= 30;

      // Draw client name in large bold text, centered
      // Auto-size font to fit within page width
      const displayName = arabicize(clientName);
      const nameFont = pickFont(clientName, true);
      let fontSize = 72;
      const maxTextWidth = pageWidth - 2 * margin - 60;
      let textWidth = nameFont.widthOfTextAtSize(displayName, fontSize);
      while (textWidth > maxTextWidth && fontSize > 24) {
        fontSize -= 2;
        textWidth = nameFont.widthOfTextAtSize(displayName, fontSize);
      }

      // Center the name vertically in the remaining space
      const textX = (pageWidth - textWidth) / 2;
      const remainingHeight = currentY - margin;
      const textY = margin + remainingHeight / 2 - fontSize / 3;

      page.drawText(displayName, {
        x: textX,
        y: textY,
        size: fontSize,
        font: nameFont,
        color: rgb(0, 0, 0),
      });

      // Draw rep name at bottom-right corner (size 10pt), always — fallback to "—"
      const repName = job.assignment?.rep?.name ?? '—';
      const repDisplay = arabicize(repName);
      const repFont = pickFont(repName);
      const repSize = 10;
      const repW = repFont.widthOfTextAtSize(repDisplay, repSize);
      page.drawText(repDisplay, {
        x: pageWidth - margin - 8 - repW,
        y: margin + 8,
        size: repSize,
        font: repFont,
        color: rgb(0.3, 0.3, 0.3),
      });
    }

    const pdfBytes = await pdfDoc.save();
    return Buffer.from(pdfBytes);
  }

  // ─────────────────────────────────────────────
  // JOB EVIDENCE PDF (server-side, no browser needed)
  // ─────────────────────────────────────────────

  async generateJobEvidencePdf(jobId: string): Promise<Buffer> {
    /** Normalize and arabicize text for PDF rendering. */
    const s = (text: string | null | undefined): string => {
      if (!text) return '-';
      return arabicize(
        (text + '')
          .replace(/\u2192/g, '>').replace(/\u2014/g, '-').replace(/\u2013/g, '-')
          .replace(/\u2026/g, '...').replace(/[\u201C\u201D]/g, '"')
          .replace(/[\u2018\u2019]/g, "'"),
      );
    };

    const [settings, job] = await Promise.all([
      this.prisma.companySettings.findFirst(),
      this.prisma.trafficJob.findUnique({
        where: { id: jobId },
        include: {
          agent: true,
          assignment: { include: { vehicle: true, driver: true, rep: true } },
          flight: true,
          fromZone: true,
          toZone: true,
          originAirport: true,
          destinationAirport: true,
          originHotel: true,
          destinationHotel: true,
          noShowEvidence: { orderBy: { createdAt: 'asc' } },
          inPlaceEvidence: { orderBy: { createdAt: 'asc' } },
          completedEvidence: { orderBy: { createdAt: 'asc' } },
        },
      }),
    ]);

    if (!job) throw new NotFoundException('Job not found');

    const pdfDoc = await PDFDocument.create();
    pdfDoc.registerFontkit(fontkit);

    const fp = fontPaths();
    const regular    = await pdfDoc.embedFont(fs.readFileSync(fp.latinRegular));
    const bold       = await pdfDoc.embedFont(fs.readFileSync(fp.latinBold));
    const arabicFont = await pdfDoc.embedFont(fs.readFileSync(fp.arabicRegular));
    const arabicBold = await pdfDoc.embedFont(fs.readFileSync(fp.arabicBold));

    /** Returns the correct font — Cairo Arabic if Arabic, DejaVu Sans otherwise. */
    const pickFont = (text: string, isBold = false) =>
      hasArabic(text) ? (isBold ? arabicBold : arabicFont) : (isBold ? bold : regular);

    const PW = 595, PH = 842, M = 36, CW = PW - 2 * M;
    const black = rgb(0, 0, 0);
    const grayC = rgb(0.5, 0.5, 0.5);
    const lightBg = rgb(0.95, 0.95, 0.95);
    const darkText = rgb(0.2, 0.2, 0.2);

    // Load company logo
    const logoImg = settings?.logoUrl ? await embedLogo(pdfDoc, settings.logoUrl) : null;

    // Page cursor helpers
    let page = pdfDoc.addPage([PW, PH]);
    let y = PH - M;

    const newPage = () => { page = pdfDoc.addPage([PW, PH]); y = PH - M; };
    const need = (h: number) => { if (y - h < M + 24) newPage(); };

    const truncate = (text: string, font: typeof bold, size: number, maxW: number): string => {
      if (font.widthOfTextAtSize(text, size) <= maxW) return text;
      let t = text;
      while (t.length > 3 && font.widthOfTextAtSize(t + '...', size) > maxW) t = t.slice(0, -1);
      return t + '...';
    };

    // ── HEADER ──
    if (logoImg) {
      const d = logoImg.scale(1);
      const sc = Math.min(120 / d.width, 40 / d.height, 1);
      page.drawImage(logoImg, { x: M, y: y - d.height * sc, width: d.width * sc, height: d.height * sc });
    } else {
      page.drawText(s(settings?.companyName ?? 'iTour'), { x: M, y: y - 12, size: 11, font: bold, color: black });
    }

    const title = 'Job Evidence Report';
    const tw = bold.widthOfTextAtSize(title, 15);
    page.drawText(title, { x: (PW - tw) / 2, y: y - 18, size: 15, font: bold, color: black });

    const dateStr = new Date(job.jobDate).toLocaleDateString('en-GB');
    const dw = regular.widthOfTextAtSize(dateStr, 9);
    page.drawText(dateStr, { x: PW - M - dw, y: y - 12, size: 9, font: regular, color: grayC });

    y -= 52;
    page.drawLine({ start: { x: M, y }, end: { x: PW - M, y }, thickness: 1, color: black });
    y -= 14;

    // ── SECTION HEADER ──
    const drawSectionHeader = (label: string) => {
      need(22);
      page.drawRectangle({ x: M, y: y - 16, width: CW, height: 16, color: lightBg });
      page.drawRectangle({ x: M, y: y - 16, width: 3, height: 16, color: darkText });
      page.drawText(label.toUpperCase(), { x: M + 8, y: y - 11, size: 7.5, font: bold, color: darkText });
      y -= 22;
    };

    // ── JOB DETAILS ──
    drawSectionHeader('Job Details');

    const origin = job.originAirport
      ? `${job.originAirport.name} (${job.originAirport.code})`
      : (job.originHotel?.name ?? job.fromZone?.name ?? '—');
    const dest = job.destinationAirport
      ? `${job.destinationAirport.name} (${job.destinationAirport.code})`
      : (job.destinationHotel?.name ?? job.toZone?.name ?? '—');

    const details: [string, string][] = [
      ['Job Ref',      s(job.internalRef)],
      ['Agent',        s(job.agent?.legalName)],
      ['Agent Ref',    s(job.agentRef)],
      ['Date',         dateStr],
      ['Service Type', s(serviceTypeLabel(job.serviceType))],
      ['Status',       s(job.status)],
      ['Pax Count',    String(job.paxCount)],
      ['Client',       s(job.clientName)],
      ['Route',        s(`${origin} > ${dest}`)],
      ['Vehicle',      s(job.assignment?.vehicle?.plateNumber)],
      ['Driver',       s(job.assignment?.driver?.name)],
      ['Rep',          s(job.assignment?.rep?.name)],
    ];
    if (job.flight) {
      details.push(['Flight', s(`${job.flight.carrier ?? ''} ${job.flight.flightNo}`.trim())]);
    }

    const ROW_H = 17;
    const COL_W = CW / 2;
    const KEY_W = 62;

    for (let i = 0; i < details.length; i += 2) {
      need(ROW_H + 2);
      const bg = Math.floor(i / 2) % 2 === 0 ? rgb(0.97, 0.97, 0.97) : rgb(1, 1, 1);
      page.drawRectangle({ x: M, y: y - ROW_H, width: CW, height: ROW_H, color: bg });

      for (let c = 0; c < 2; c++) {
        const idx = i + c;
        if (idx >= details.length) break;
        const [key, val] = details[idx];
        const xBase = M + c * COL_W;
        page.drawText(key + ':', {
          x: xBase + 4, y: y - ROW_H + 5,
          size: 7.5, font: regular, color: grayC,
        });
        const valFont = pickFont(val, true);
        page.drawText(truncate(val, valFont, 8, COL_W - KEY_W - 8), {
          x: xBase + KEY_W, y: y - ROW_H + 5,
          size: 8, font: valFont, color: black,
        });
      }
      y -= ROW_H;
    }
    y -= 10;

    // ── EVIDENCE SECTIONS ──
    const driverName = job.assignment?.driver?.name ?? null;
    const repName    = job.assignment?.rep?.name    ?? null;

    const repEvidence = [
      ...job.inPlaceEvidence.filter(e => repName    && e.submittedBy === repName),
      ...job.noShowEvidence,
    ];
    const driverEvidence = [
      ...job.inPlaceEvidence.filter(e => driverName && e.submittedBy === driverName),
      ...job.completedEvidence,
      // fallback: items not attributed to either party go under driver
      ...job.inPlaceEvidence.filter(
        e => (!repName || e.submittedBy !== repName) && (!driverName || e.submittedBy !== driverName),
      ),
    ];

    const IMG_COLS = 3;
    const IMG_GAP  = 6;
    const IMG_W    = (CW - IMG_GAP * (IMG_COLS - 1)) / IMG_COLS;
    const IMG_H    = 115;

    const embedImage = async (rawUrl: string) => {
      let imgBytes: Buffer;

      if (isDriveFileId(rawUrl)) {
        const buf = await this.googleDrive.getFileBuffer(rawUrl);
        if (!buf) throw new Error(`Drive file not available: ${rawUrl}`);
        imgBytes = buf;
        // Detect PNG header
        const isPng = imgBytes[0] === 0x89 && imgBytes[1] === 0x50;
        return isPng ? pdfDoc.embedPng(imgBytes) : pdfDoc.embedJpg(imgBytes);
      }

      const imgPath = path.join(process.cwd(), rawUrl.replace(/^\//, ''));
      imgBytes = fs.readFileSync(imgPath);
      return rawUrl.toLowerCase().includes('.png')
        ? pdfDoc.embedPng(imgBytes)
        : pdfDoc.embedJpg(imgBytes);
    };

    const drawEvidenceGroup = async (label: string, items: typeof repEvidence) => {
      if (!items.length) return;
      drawSectionHeader(label);

      // Pre-fetch all images in parallel across all evidence items in this group
      const allUrls = items.flatMap(ev => ev.imageUrls ?? []);
      const embeddedMap = new Map<string, Awaited<ReturnType<typeof embedImage>> | null>();
      await Promise.all(
        allUrls.map(async (rawUrl) => {
          if (embeddedMap.has(rawUrl)) return;
          try {
            embeddedMap.set(rawUrl, await embedImage(rawUrl));
          } catch {
            embeddedMap.set(rawUrl, null);
          }
        }),
      );

      for (const ev of items) {
        const metaDate = new Date(ev.createdAt).toLocaleString('en-GB', { timeZone: 'Africa/Cairo' });
        const rawMeta = `Submitted by: ${ev.submittedBy}   |   ${metaDate}`;
        const metaFont = pickFont(rawMeta);
        const meta = truncate(s(rawMeta), metaFont, 7.5, CW - 10);
        need(22);
        page.drawRectangle({ x: M, y: y - 18, width: CW, height: 18, color: lightBg });
        page.drawText(meta, { x: M + 5, y: y - 12.5, size: 7.5, font: metaFont, color: darkText });
        y -= 24;

        const imageUrls: string[] = ev.imageUrls ?? [];
        for (let i = 0; i < imageUrls.length; i += IMG_COLS) {
          need(IMG_H + IMG_GAP + 4);
          const row = imageUrls.slice(i, i + IMG_COLS);
          let rowH = 0;

          for (let c = 0; c < row.length; c++) {
            const rawUrl = row[c];
            const xBase  = M + c * (IMG_W + IMG_GAP);
            const embedded = embeddedMap.get(rawUrl) ?? null;
            if (embedded) {
              try {
                const d  = embedded.scale(1);
                const sc = Math.min(IMG_W / d.width, IMG_H / d.height);
                const iw = d.width  * sc;
                const ih = d.height * sc;
                rowH = Math.max(rowH, ih);
                const ix = xBase + (IMG_W - iw) / 2;
                page.drawImage(embedded, { x: ix, y: y - ih, width: iw, height: ih });
                page.drawRectangle({
                  x: ix - 1, y: y - ih - 1, width: iw + 2, height: ih + 2,
                  borderColor: rgb(0.78, 0.78, 0.78), borderWidth: 0.5,
                });
              } catch {
                rowH = Math.max(rowH, IMG_H);
                page.drawRectangle({ x: xBase, y: y - IMG_H, width: IMG_W, height: IMG_H, color: rgb(0.9, 0.9, 0.9) });
                page.drawText('Image unavailable', { x: xBase + 4, y: y - IMG_H / 2, size: 8, font: regular, color: grayC });
              }
            } else {
              rowH = Math.max(rowH, IMG_H);
              page.drawRectangle({ x: xBase, y: y - IMG_H, width: IMG_W, height: IMG_H, color: rgb(0.9, 0.9, 0.9) });
              page.drawText('Image unavailable', { x: xBase + 4, y: y - IMG_H / 2, size: 8, font: regular, color: grayC });
            }
          }
          y -= (rowH + IMG_GAP);
        }
        y -= 6;
      }
    };

    await drawEvidenceGroup('Rep Evidence', repEvidence);
    await drawEvidenceGroup('Driver Evidence', driverEvidence);

    if (!repEvidence.length && !driverEvidence.length) {
      need(20);
      page.drawText('No evidence submitted for this job.', {
        x: M, y: y - 12, size: 10, font: regular, color: grayC,
      });
    }

    // ── FOOTER on every page ──
    const now       = new Date().toLocaleString('en-GB', { timeZone: 'Africa/Cairo' });
    const compName  = s(settings?.companyName ?? 'iTour');
    const totalPgs  = pdfDoc.getPageCount();
    const footerY   = M + 4;

    for (let p = 0; p < totalPgs; p++) {
      const pg  = pdfDoc.getPage(p);
      const pgW = pg.getWidth();
      pg.drawLine({
        start: { x: M, y: footerY + 12 }, end: { x: pgW - M, y: footerY + 12 },
        thickness: 0.5, color: rgb(0.75, 0.75, 0.75),
      });
      pg.drawText(compName, { x: M, y: footerY, size: 7, font: regular, color: grayC });
      const fr = `Issued on ${s(now)}`;
      pg.drawText(fr, { x: pgW - M - regular.widthOfTextAtSize(fr, 7), y: footerY, size: 7, font: regular, color: grayC });
      const pn  = `Page ${p + 1} of ${totalPgs}`;
      const pnw = regular.widthOfTextAtSize(pn, 7);
      pg.drawText(pn, { x: (pgW - pnw) / 2, y: footerY, size: 7, font: regular, color: grayC });
    }

    return Buffer.from(await pdfDoc.save());
  }

  // ─────────────────────────────────────────────
  // DAILY DISPATCH REPORT EXPORT
  // ─────────────────────────────────────────────

  async exportDailyDispatchReport(date: string): Promise<Buffer> {
    const jobDate = new Date(date);

    const jobs = await this.prisma.trafficJob.findMany({
      where: { jobDate, deletedAt: null },
      include: {
        agent: true,
        customer: true,
        fromZone: true,
        toZone: true,
        flight: true,
        assignment: {
          include: {
            vehicle: { include: { vehicleType: true } },
            driver: true,
            rep: true,
          },
        },
      },
      orderBy: { createdAt: 'asc' },
    });

    const rows = jobs.map((job) => ({
      'Ref': job.internalRef,
      'Agent / Customer': job.agent?.legalName || job.customer?.legalName || '',
      'Service Type': serviceTypeLabel(job.serviceType),
      'Status': job.status,
      'Client Name': job.clientName || '',
      'Pax': job.paxCount,
      'From': job.fromZone?.name || '',
      'To': job.toZone?.name || '',
      'Flight No': job.flight?.flightNo || '',
      'Carrier': job.flight?.carrier || '',
      'Vehicle': job.assignment?.vehicle?.plateNumber || '',
      'Vehicle Type': job.assignment?.vehicle?.vehicleType?.name || '',
      'Driver': job.assignment?.driver?.name || '',
      'Rep': job.assignment?.rep?.name || '',
    }));

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    this.autoSizeColumns(ws, rows);
    XLSX.utils.book_append_sheet(wb, ws, `Dispatch ${date}`);
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // DRIVER TRIP REPORT EXPORT
  // ─────────────────────────────────────────────

  async exportDriverTrips(from: string, to: string): Promise<Buffer> {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const assignments = await this.prisma.trafficAssignment.findMany({
      where: {
        driverId: { not: null },
        trafficJob: {
          jobDate: { gte: fromDate, lte: toDate },
          deletedAt: null,
        },
      },
      include: {
        driver: true,
        trafficJob: {
          include: {
            fromZone: true,
            toZone: true,
            agent: true,
          },
        },
      },
    });

    // Aggregate by driver for summary
    const driverMap = new Map<string, { name: string; mobile: string; trips: number; fees: number }>();

    const detailRows: Record<string, unknown>[] = [];

    for (const a of assignments) {
      if (!a.driver) continue;
      const existing = driverMap.get(a.driverId!);
      if (existing) {
        existing.trips++;
      } else {
        driverMap.set(a.driverId!, {
          name: a.driver.name,
          mobile: a.driver.mobileNumber,
          trips: 1,
          fees: 0,
        });
      }

      detailRows.push({
        'Driver': a.driver.name,
        'Job Date': this.formatDate(a.trafficJob.jobDate),
        'Service Type': serviceTypeLabel(a.trafficJob.serviceType),
        'Route': a.trafficJob.fromZone && a.trafficJob.toZone
          ? `${a.trafficJob.fromZone.name} → ${a.trafficJob.toZone.name}`
          : '—',
        'Agent': a.trafficJob.agent?.legalName || '—',
        'Ref': a.trafficJob.internalRef,
      });
    }

    // Fetch fees
    const fees = await this.prisma.driverTripFee.findMany({
      where: {
        trafficJob: {
          jobDate: { gte: fromDate, lte: toDate },
          deletedAt: null,
        },
      },
    });
    for (const fee of fees) {
      const d = driverMap.get(fee.driverId);
      if (d) d.fees += Number(fee.amount);
    }

    const summaryRows = Array.from(driverMap.values()).map((d) => ({
      'Driver': d.name,
      'Mobile': d.mobile,
      'Trips': d.trips,
      'Total Fees': d.fees,
    }));

    const wb = XLSX.utils.book_new();

    const summaryWs = XLSX.utils.json_to_sheet(summaryRows);
    this.autoSizeColumns(summaryWs, summaryRows);
    XLSX.utils.book_append_sheet(wb, summaryWs, 'Summary');

    if (detailRows.length > 0) {
      const detailWs = XLSX.utils.json_to_sheet(detailRows);
      this.autoSizeColumns(detailWs, detailRows);
      XLSX.utils.book_append_sheet(wb, detailWs, 'Details');
    }

    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // AGENT STATEMENT EXPORT
  // ─────────────────────────────────────────────

  async exportAgentStatement(agentId: string, from: string, to: string): Promise<Buffer> {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const agent = await this.prisma.agent.findUnique({
      where: { id: agentId },
      include: { creditTerms: true },
    });

    const invoices = await this.prisma.agentInvoice.findMany({
      where: {
        agentId,
        invoiceDate: { gte: fromDate, lte: toDate },
      },
      include: { payments: true },
      orderBy: { invoiceDate: 'asc' },
    });

    const rows = invoices.map((inv) => {
      const paid = inv.payments.reduce((sum, p) => sum + Number(p.amount), 0);
      return {
        'Invoice #': inv.invoiceNumber,
        'Date': this.formatDate(inv.invoiceDate),
        'Due Date': this.formatDate(inv.dueDate),
        'Currency': inv.currency,
        'Subtotal': Number(inv.subtotal),
        'Tax': Number(inv.taxAmount),
        'Total': Number(inv.total),
        'Paid': paid,
        'Balance': Number(inv.total) - paid,
        'Status': inv.status,
      };
    });

    // Add totals row
    const totalInvoiced = rows.reduce((sum, r) => sum + (r['Total'] as number), 0);
    const totalPaid = rows.reduce((sum, r) => sum + (r['Paid'] as number), 0);
    rows.push({
      'Invoice #': 'TOTALS',
      'Date': '',
      'Due Date': '',
      'Currency': '' as any,
      'Subtotal': rows.reduce((sum, r) => sum + (r['Subtotal'] as number), 0),
      'Tax': rows.reduce((sum, r) => sum + (r['Tax'] as number), 0),
      'Total': totalInvoiced,
      'Paid': totalPaid,
      'Balance': totalInvoiced - totalPaid,
      'Status': '' as any,
    });

    const wb = XLSX.utils.book_new();

    // Agent info sheet
    const infoRows = [
      { Field: 'Agent', Value: agent?.legalName || '' },
      { Field: 'Trade Name', Value: agent?.tradeName || '' },
      { Field: 'Period', Value: `${from} to ${to}` },
      { Field: 'Credit Limit', Value: agent?.creditTerms ? Number(agent.creditTerms.creditLimit) : 'N/A' },
      { Field: 'Credit Days', Value: agent?.creditTerms?.creditDays ?? 'N/A' },
      { Field: 'Total Invoiced', Value: totalInvoiced },
      { Field: 'Total Paid', Value: totalPaid },
      { Field: 'Outstanding', Value: totalInvoiced - totalPaid },
    ];
    const infoWs = XLSX.utils.json_to_sheet(infoRows);
    this.autoSizeColumns(infoWs, infoRows);
    XLSX.utils.book_append_sheet(wb, infoWs, 'Summary');

    const invoiceWs = XLSX.utils.json_to_sheet(rows);
    this.autoSizeColumns(invoiceWs, rows);
    XLSX.utils.book_append_sheet(wb, invoiceWs, 'Invoices');

    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // REVENUE REPORT EXPORT
  // ─────────────────────────────────────────────

  async exportRevenue(from: string, to: string): Promise<Buffer> {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const invoices = await this.prisma.agentInvoice.findMany({
      where: {
        invoiceDate: { gte: fromDate, lte: toDate },
        status: { not: 'CANCELLED' as any },
      },
      include: {
        agent: true,
        customer: true,
        lines: { include: { trafficJob: true } },
      },
    });

    let totalRevenue = 0;
    const byAgent = new Map<string, { name: string; revenue: number; invoices: number; jobs: number }>();
    const byServiceType: Record<string, number> = {};

    for (const inv of invoices) {
      const invTotal = Number(inv.total);
      totalRevenue += invTotal;
      const partnerId = inv.agentId || inv.customerId || 'unknown';
      const partnerName = inv.agent?.legalName || inv.customer?.legalName || 'Unknown';
      const entry = byAgent.get(partnerId) || { name: partnerName, revenue: 0, invoices: 0, jobs: 0 };
      entry.revenue += invTotal;
      entry.invoices++;
      byAgent.set(partnerId, entry);

      for (const line of inv.lines) {
        if (line.trafficJob) {
          byServiceType[line.trafficJob.serviceType] = (byServiceType[line.trafficJob.serviceType] || 0) + Number(line.lineTotal);
          byAgent.get(partnerId)!.jobs++;
        }
      }
    }

    const [driverFees, repFees, supplierCosts] = await Promise.all([
      this.prisma.driverTripFee.aggregate({
        where: { trafficJob: { jobDate: { gte: fromDate, lte: toDate }, deletedAt: null } },
        _sum: { amount: true },
      }),
      this.prisma.repFee.aggregate({
        where: { trafficJob: { jobDate: { gte: fromDate, lte: toDate }, deletedAt: null } },
        _sum: { amount: true },
      }),
      this.prisma.supplierCost.aggregate({
        where: { trafficJob: { jobDate: { gte: fromDate, lte: toDate }, deletedAt: null } },
        _sum: { amount: true },
      }),
    ]);

    const totalDriverFees = Number(driverFees._sum.amount || 0);
    const totalRepFees = Number(repFees._sum.amount || 0);
    const totalSupplierCosts = Number(supplierCosts._sum.amount || 0);
    const totalCosts = totalDriverFees + totalRepFees + totalSupplierCosts;

    const wb = XLSX.utils.book_new();

    // Summary sheet
    const summaryRows = [
      { Metric: 'Period', Value: `${from} to ${to}` },
      { Metric: 'Total Revenue', Value: totalRevenue },
      { Metric: 'Driver Fees', Value: totalDriverFees },
      { Metric: 'Rep Fees', Value: totalRepFees },
      { Metric: 'Supplier Costs', Value: totalSupplierCosts },
      { Metric: 'Total Costs', Value: totalCosts },
      { Metric: 'Gross Profit', Value: totalRevenue - totalCosts },
      { Metric: 'Profit Margin %', Value: totalRevenue > 0 ? Math.round(((totalRevenue - totalCosts) / totalRevenue) * 100) : 0 },
    ];
    const summaryWs = XLSX.utils.json_to_sheet(summaryRows);
    this.autoSizeColumns(summaryWs, summaryRows);
    XLSX.utils.book_append_sheet(wb, summaryWs, 'Summary');

    // By Agent sheet
    const agentRows = Array.from(byAgent.values())
      .sort((a, b) => b.revenue - a.revenue)
      .map((a) => ({
        'Agent / Customer': a.name,
        'Revenue': a.revenue,
        'Invoices': a.invoices,
        'Jobs': a.jobs,
      }));
    if (agentRows.length > 0) {
      const agentWs = XLSX.utils.json_to_sheet(agentRows);
      this.autoSizeColumns(agentWs, agentRows);
      XLSX.utils.book_append_sheet(wb, agentWs, 'By Agent');
    }

    // By Service Type sheet
    const stRows = Object.entries(byServiceType).map(([type, revenue]) => ({
      'Service Type': serviceTypeLabel(type),
      'Revenue': revenue,
    }));
    if (stRows.length > 0) {
      const stWs = XLSX.utils.json_to_sheet(stRows);
      this.autoSizeColumns(stWs, stRows);
      XLSX.utils.book_append_sheet(wb, stWs, 'By Service Type');
    }

    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // VEHICLE COMPLIANCE REPORT EXPORT
  // ─────────────────────────────────────────────

  async exportVehicleCompliance(): Promise<Buffer> {
    const vehicles = await this.prisma.vehicle.findMany({
      where: { deletedAt: null },
      include: {
        vehicleType: true,
        compliance: true,
      },
      orderBy: { plateNumber: 'asc' },
    });

    const today = new Date();
    const rows = vehicles.map((v) => {
      const c = v.compliance;
      const licenseStatus = c?.licenseExpiryDate
        ? new Date(c.licenseExpiryDate) < today ? 'EXPIRED' : 'VALID'
        : 'N/A';
      const insuranceStatus = c?.insuranceExpiryDate
        ? new Date(c.insuranceExpiryDate) < today ? 'EXPIRED' : 'VALID'
        : c?.hasInsurance ? 'VALID' : 'N/A';

      return {
        'Plate Number': v.plateNumber,
        'Vehicle Type': v.vehicleType?.name || '',
        'Ownership': v.ownership,
        'Active': v.isActive ? 'Yes' : 'No',
        'License Expiry': c?.licenseExpiryDate ? this.formatDate(c.licenseExpiryDate) : '',
        'License Status': licenseStatus,
        'Has Insurance': c?.hasInsurance ? 'Yes' : 'No',
        'Insurance Expiry': c?.insuranceExpiryDate ? this.formatDate(c.insuranceExpiryDate) : '',
        'Insurance Status': insuranceStatus,
        'Annual Payment': c?.annualPayment ? Number(c.annualPayment) : '',
        'GPS Subscription': c?.gpsSubscription ? Number(c.gpsSubscription) : '',
        'Tourism Fund': c?.tourismSupportFund ? Number(c.tourismSupportFund) : '',
        'Registration Fees': c?.registrationFees ? Number(c.registrationFees) : '',
      };
    });

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    this.autoSizeColumns(ws, rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Vehicle Compliance');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  private autoSizeColumns(
    ws: XLSX.WorkSheet,
    data: Record<string, unknown>[],
  ) {
    if (data.length > 0) {
      const colWidths = Object.keys(data[0]).map((key) => {
        const maxLen = Math.max(
          key.length,
          ...data.map((row) => String(row[key] ?? '').length),
        );
        return { wch: Math.min(maxLen + 2, 40) };
      });
      ws['!cols'] = colWidths;
    }
  }

  // ─────────────────────────────────────────────
  // HELPERS
  // ─────────────────────────────────────────────

  private formatDate(date: Date): string {
    return date.toISOString().split('T')[0];
  }

  // ── Africa/Cairo formatters — match the on-screen reports, which render
  //    stored UTC timestamps in Cairo time (Egypt is UTC+2, UTC+3 in DST). ──
  private cairoDate(date: Date | null | undefined): string {
    if (!date) return '—';
    return new Date(date).toLocaleDateString('en-CA', { timeZone: 'Africa/Cairo' }); // YYYY-MM-DD
  }

  private cairoTime(date: Date | null | undefined): string {
    if (!date) return '—';
    return new Date(date).toLocaleTimeString('en-GB', { timeZone: 'Africa/Cairo', hour: '2-digit', minute: '2-digit', hour12: false }); // HH:MM
  }

  private cairoDateTime(date: Date | null | undefined): string {
    if (!date) return '—';
    return `${this.cairoDate(date)} ${this.cairoTime(date)}`; // YYYY-MM-DD HH:MM
  }

  private mapPaymentJournal(method: string): string {
    switch (method) {
      case 'CASH':
        return 'Cash';
      case 'BANK_TRANSFER':
        return 'Bank';
      case 'CHECK':
        return 'Bank';
      default:
        return 'Cash';
    }
  }

  private mapJournalType(type: string): string {
    switch (type) {
      case 'SALE':
        return 'Customer Invoices';
      case 'PURCHASE':
        return 'Vendor Bills';
      case 'CASH':
        return 'Cash';
      case 'BANK':
        return 'Bank';
      case 'GENERAL':
        return 'Miscellaneous';
      default:
        return 'Miscellaneous';
    }
  }

  // ─────────────────────────────────────────────
  // EVIDENCE ZIP — stream all evidence images for a job as a .zip
  // ─────────────────────────────────────────────

  async streamEvidenceZip(jobId: string, res: Response): Promise<void> {
    const job = await this.prisma.trafficJob.findUnique({
      where: { id: jobId },
      select: {
        internalRef: true,
        status: true,
        noShowEvidence:  { select: { imageUrls: true }, orderBy: { createdAt: 'asc' } },
        inPlaceEvidence: { select: { imageUrls: true }, orderBy: { createdAt: 'asc' } },
        completedEvidence: { select: { imageUrls: true }, orderBy: { createdAt: 'asc' } },
      },
    });

    if (!job) throw new NotFoundException('Job not found');

    const ref = job.internalRef.replace(/[^a-zA-Z0-9_-]/g, '_');
    const status = (job.status as string).toLowerCase();

    const uploadsDir = path.resolve('uploads');

    const fetchImageBuffer = async (url: string): Promise<Buffer | null> => {
      if (isDriveFileId(url)) {
        return this.googleDrive.getFileBuffer(url);
      }
      // Legacy local file
      const localPath = path.join(uploadsDir, url.replace(/^\/uploads\//, ''));
      if (fs.existsSync(localPath)) return fs.readFileSync(localPath);
      return null;
    };

    const guessExt = (url: string) => {
      const m = url.match(/\.(jpe?g|png|webp|gif)(\?|$)/i);
      return m ? `.${m[1].toLowerCase().replace('jpeg', 'jpg')}` : '.jpg';
    };

    type EvidenceGroup = { type: string; urls: string[] };
    const groups: EvidenceGroup[] = [
      { type: 'noshow',    urls: job.noShowEvidence.flatMap((e) => e.imageUrls) },
      { type: 'inplace',   urls: job.inPlaceEvidence.flatMap((e) => e.imageUrls) },
      { type: 'completed', urls: job.completedEvidence.flatMap((e) => e.imageUrls) },
    ];

    // Fetch all images in parallel across all groups to avoid serial Drive round-trips
    const fetchWork = groups.flatMap(({ type, urls }) =>
      urls.map((url, idx) => ({ type, idx: idx + 1, url })),
    );
    const fetched = await Promise.all(
      fetchWork.map(async ({ type, idx, url }) => ({
        type,
        idx,
        url,
        buf: await fetchImageBuffer(url),
      })),
    );

    const zipName = `evidence_${ref}.zip`;
    res.set({
      'Content-Type': 'application/zip',
      'Content-Disposition': `attachment; filename="${zipName}"`,
    });

    const archive = archiver('zip', { zlib: { level: 6 } });
    archive.on('error', (err) => {
      this.logger.error('Archive error during evidence ZIP', err);
      if (!res.headersSent) res.status(500).end();
    });
    archive.pipe(res);

    for (const { type, idx, url, buf } of fetched) {
      if (!buf) continue;
      const ext = guessExt(url);
      archive.append(buf, { name: `${ref}-${status}-${type}-${idx}${ext}` });
    }

    await archive.finalize();
  }

  private async fetchAllInBatches<T extends { id: string }>(
    fetcher: (cursor: string | null) => Promise<T[]>,
  ): Promise<T[]> {
    const all: T[] = [];
    let cursor: string | null = null;
    while (true) {
      const batch = await fetcher(cursor);
      all.push(...batch);
      if (batch.length < 1000) break;
      cursor = batch[batch.length - 1].id;
    }
    return all;
  }

  private createWorkbook(
    data: Record<string, unknown>[],
    sheetName: string,
  ): Buffer {
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(data);

    // Auto-size columns
    if (data.length > 0) {
      const colWidths = Object.keys(data[0]).map((key) => {
        const maxLen = Math.max(
          key.length,
          ...data.map((row) => String(row[key] ?? '').length),
        );
        return { wch: Math.min(maxLen + 2, 40) };
      });
      ws['!cols'] = colWidths;
    }

    XLSX.utils.book_append_sheet(wb, ws, sheetName);
    const buf = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
    return Buffer.from(buf);
  }

  // ─────────────────────────────────────────────
  // EVIDENCE DATA — JSON for client-side HTML rendering
  // ─────────────────────────────────────────────

  async getEvidenceData(jobId: string) {
    const [settings, job] = await Promise.all([
      this.prisma.companySettings.findFirst({
        select: { companyName: true, logoUrl: true },
      }),
      this.prisma.trafficJob.findUnique({
        where: { id: jobId },
        include: {
          agent: { select: { legalName: true, tradeName: true } },
          assignment: {
            include: {
              vehicle: { select: { plateNumber: true, vehicleType: { select: { name: true } } } },
              driver: { select: { name: true, mobileNumber: true } },
              rep: { select: { name: true, mobileNumber: true } },
            },
          },
          flight: true,
          fromZone: { select: { name: true } },
          toZone: { select: { name: true } },
          originAirport: { select: { name: true, code: true } },
          destinationAirport: { select: { name: true, code: true } },
          originHotel: { select: { name: true } },
          destinationHotel: { select: { name: true } },
          noShowEvidence: { orderBy: { createdAt: 'asc' } },
          inPlaceEvidence: { orderBy: { createdAt: 'asc' } },
          completedEvidence: { orderBy: { createdAt: 'asc' } },
        },
      }),
    ]);

    if (!job) throw new NotFoundException('Job not found');

    return {
      companyName: settings?.companyName ?? 'iTour',
      logoUrl: settings?.logoUrl ?? null,
      job: {
        id: job.id,
        internalRef: job.internalRef,
        agentRef: job.agentRef,
        serviceType: job.serviceType,
        status: job.status,
        paxCount: job.paxCount,
        jobDate: job.jobDate,
        pickUpTime: job.pickUpTime,
        notes: job.notes,
        agentName: job.agent?.tradeName ?? job.agent?.legalName ?? null,
        route: {
          fromZone: job.fromZone?.name ?? null,
          toZone: job.toZone?.name ?? null,
          originAirport: job.originAirport ? `${job.originAirport.name} (${job.originAirport.code})` : null,
          destinationAirport: job.destinationAirport ? `${job.destinationAirport.name} (${job.destinationAirport.code})` : null,
          originHotel: job.originHotel?.name ?? null,
          destinationHotel: job.destinationHotel?.name ?? null,
        },
        flight: job.flight ? {
          flightNo: job.flight.flightNo,
          carrier: job.flight.carrier,
          arrivalTime: job.flight.arrivalTime,
          departureTime: job.flight.departureTime,
        } : null,
        assignment: job.assignment ? {
          vehicle: job.assignment.vehicle ? {
            plateNumber: job.assignment.vehicle.plateNumber,
            vehicleType: job.assignment.vehicle.vehicleType.name,
          } : null,
          driver: job.assignment.driver ? {
            name: job.assignment.driver.name,
            mobile: job.assignment.driver.mobileNumber,
          } : null,
          rep: job.assignment.rep ? {
            name: job.assignment.rep.name,
            mobile: job.assignment.rep.mobileNumber,
          } : null,
        } : null,
      },
      evidence: {
        noShow: job.noShowEvidence.map(e => ({
          id: e.id,
          submittedBy: e.submittedBy,
          createdAt: e.createdAt,
          imageUrls: e.imageUrls,
          gpsMapLink: e.gpsMapLink,
        })),
        inPlace: job.inPlaceEvidence.map(e => ({
          id: e.id,
          submittedBy: e.submittedBy,
          createdAt: e.createdAt,
          imageUrls: e.imageUrls,
          gpsMapLink: e.gpsMapLink,
        })),
        completed: job.completedEvidence.map(e => ({
          id: e.id,
          submittedBy: e.submittedBy,
          createdAt: e.createdAt,
          imageUrls: e.imageUrls,
          gpsMapLink: e.gpsMapLink,
        })),
      },
    };
  }

  // ─────────────────────────────────────────────
  // SUPPLIER JOBS REPORT
  // ─────────────────────────────────────────────

  async getSupplierJobsReport(opts: {
    from: string;
    to: string;
    supplierId?: string;
    supplierStatus?: string;
  }) {
    const fromDate = new Date(opts.from);
    const toDate = new Date(opts.to);

    const assignments = await this.prisma.trafficAssignment.findMany({
      where: {
        supplierId: { not: null },
        ...(opts.supplierId ? { supplierId: opts.supplierId } : {}),
        ...(opts.supplierStatus && opts.supplierStatus !== 'ALL'
          ? { supplierStatus: opts.supplierStatus as any }
          : {}),
        trafficJob: {
          deletedAt: null,
          jobDate: { gte: fromDate, lte: toDate },
        },
      },
      include: {
        supplier: { select: { id: true, tradeName: true, legalName: true } },
        trafficJob: {
          include: {
            agent: { select: { legalName: true } },
            originAirport:      { select: { code: true } },
            originHotel:        { select: { name: true } },
            originZone:         { select: { name: true } },
            destinationAirport: { select: { code: true } },
            destinationHotel:   { select: { name: true } },
            destinationZone:    { select: { name: true } },
            fromZone:           { select: { name: true } },
            toZone:             { select: { name: true } },
          },
        },
      },
      orderBy: { trafficJob: { jobDate: 'asc' } },
    });

    const rows = assignments.map((a) => {
      const job = a.trafficJob;
      const from =
        job.originAirport?.code ??
        job.originHotel?.name ??
        job.originZone?.name ??
        job.fromZone?.name;
      const to =
        job.destinationAirport?.code ??
        job.destinationHotel?.name ??
        job.destinationZone?.name ??
        job.toZone?.name;
      const route = from && to ? `${from} → ${to}` : '—';
      return {
        id: a.id,
        jobRef: job.internalRef,
        agentName: job.agent?.legalName ?? '—',
        agentRef: job.agentRef ?? '—',
        serviceDate: job.jobDate,
        route,
        supplierName:
          a.supplier?.tradeName ?? a.supplier?.legalName ?? '—',
        supplierStatus: a.supplierStatus,
      };
    });

    return { total: rows.length, rows };
  }

  // ─────────────────────────────────────────────
  // CAR JOBS REPORT
  // ─────────────────────────────────────────────

  async getOwnedActiveVehicles() {
    return this.prisma.vehicle.findMany({
      where: { ownership: 'OWNED', isActive: true, deletedAt: null },
      select: { id: true, plateNumber: true },
      orderBy: { plateNumber: 'asc' },
    });
  }

  async getCarJobsReport(opts: {
    from: string;
    to: string;
    vehicleId?: string;
  }) {
    const fromDate = new Date(opts.from);
    const toDate = new Date(opts.to);

    const assignments = await this.prisma.trafficAssignment.findMany({
      where: {
        vehicleId: { not: null },
        ...(opts.vehicleId ? { vehicleId: opts.vehicleId } : {}),
        vehicle: { ownership: 'OWNED', isActive: true },
        trafficJob: {
          deletedAt: null,
          jobDate: { gte: fromDate, lte: toDate },
        },
      },
      include: {
        vehicle: { select: { id: true, plateNumber: true } },
        driver: { select: { name: true } },
        trafficJob: {
          include: {
            agent:              { select: { legalName: true } },
            originAirport:      { select: { code: true } },
            originHotel:        { select: { name: true } },
            originZone:         { select: { name: true } },
            destinationAirport: { select: { code: true } },
            destinationHotel:   { select: { name: true } },
            destinationZone:    { select: { name: true } },
          },
        },
      },
      orderBy: { trafficJob: { jobDate: 'asc' } },
    });

    const rows = assignments.map((a) => {
      const job = a.trafficJob;
      const origin =
        job.originAirport?.code ??
        job.originHotel?.name ??
        job.originZone?.name ??
        '—';
      const destination =
        job.destinationAirport?.code ??
        job.destinationHotel?.name ??
        job.destinationZone?.name ??
        '—';
      return {
        id: a.id,
        jobRef: job.internalRef,
        agentName: job.agent?.legalName ?? '—',
        serviceDate: job.jobDate,
        origin,
        destination,
        driver: a.driver?.name ?? '—',
        jobStatus: job.status,
        plateNumber: a.vehicle?.plateNumber ?? '—',
        transferPrice: job.transferPrice ? Number(job.transferPrice) : null,
        transferPriceCurrency: job.transferPriceCurrency ?? 'EGP',
      };
    });

    const totals = { USD: 0, EUR: 0, EGP: 0 };
    for (const r of rows) {
      if (r.transferPrice !== null && r.transferPriceCurrency in totals) {
        totals[r.transferPriceCurrency as keyof typeof totals] += r.transferPrice;
      }
    }

    return { total: rows.length, rows, totals };
  }

  async exportVisaReport(from: string, to: string): Promise<Buffer> {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const jobs = await this.prisma.trafficJob.findMany({
      where: {
        jobDate: { gte: fromDate, lte: toDate },
        deletedAt: null,
        flight: { isNot: null },
      },
      include: {
        flight: { select: { flightNo: true, arrivalTime: true, departureTime: true, terminal: true } },
      },
      orderBy: [{ jobDate: 'asc' }, { flight: { arrivalTime: 'asc' } }],
    });

    const rows = jobs.map((j) => ({
      'Client Name': j.clientName ?? '—',
      'Flight Number': j.flight?.flightNo ?? '—',
      'Arrival Time': this.cairoDateTime(j.flight?.arrivalTime ?? j.flight?.departureTime ?? null),
      'Terminal': j.flight?.terminal ?? '—',
    }));

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    this.autoSizeColumns(ws, rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Visa Report');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  async exportSalesReport(from: string, to: string): Promise<Buffer> {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const jobs = await this.prisma.trafficJob.findMany({
      where: {
        jobDate: { gte: fromDate, lte: toDate },
        deletedAt: null,
      },
      include: {
        flight: { select: { flightNo: true, arrivalTime: true, departureTime: true, terminal: true } },
        destinationHotel: { select: { name: true } },
        originHotel: { select: { name: true } },
      },
      orderBy: [{ jobDate: 'asc' }, { internalRef: 'asc' }],
    });

    // Match the on-screen report, which renders flight times in Africa/Cairo.
    const cairoDate = (d: Date) =>
      d.toLocaleDateString('en-CA', { timeZone: 'Africa/Cairo' }); // YYYY-MM-DD
    const cairoTime = (d: Date) =>
      d.toLocaleTimeString('en-GB', { timeZone: 'Africa/Cairo', hour: '2-digit', minute: '2-digit', hour12: false }); // HH:MM

    const rows = jobs.map((j) => {
      const flightTime = j.flight?.arrivalTime ?? j.flight?.departureTime ?? null;
      return {
        'Internal Ref': j.internalRef,
        'Agent Ref': j.agentRef ?? '—',
        'Flight No.': j.flight?.flightNo ?? '—',
        'Terminal': j.flight?.terminal ?? '—',
        'Arrival Date': flightTime ? cairoDate(flightTime) : '—',
        'Arrival Time': flightTime ? cairoTime(flightTime) : '—',
        'Pax': j.paxCount,
        'Hotel Name': j.destinationHotel?.name ?? j.originHotel?.name ?? '—',
        'Client Name': j.clientName ?? '—',
        'Client Number': j.clientMobile ?? '—',
      };
    });

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    this.autoSizeColumns(ws, rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Sales Report');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // EVIDENCE EXCEL EXPORT
  // ─────────────────────────────────────────────

  async exportEvidenceReport(from: string, to: string, status?: string, agentId?: string, repId?: string, driverId?: string): Promise<Buffer> {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const where: Record<string, unknown> = { jobDate: { gte: fromDate, lte: toDate }, deletedAt: null };
    if (status && status !== 'ALL') {
      const statusList = status.split(',').map((s) => s.trim()).filter(Boolean);
      where.status = statusList.length === 1 ? statusList[0] : { in: statusList };
    }
    if (agentId) where.agentId = agentId;
    if (repId || driverId) {
      where.assignment = {
        ...(repId ? { repId } : {}),
        ...(driverId ? { driverId } : {}),
      };
    }

    const jobs = await this.prisma.trafficJob.findMany({
      where,
      include: {
        agent: { select: { legalName: true } },
        fromZone: { select: { name: true } },
        toZone: { select: { name: true } },
        originAirport: { select: { name: true, code: true } },
        destinationAirport: { select: { name: true, code: true } },
        originHotel: { select: { name: true } },
        destinationHotel: { select: { name: true } },
        flight: { select: { flightNo: true, carrier: true } },
        assignment: {
          include: {
            vehicle: { select: { plateNumber: true } },
            driver: { select: { name: true } },
            rep: { select: { name: true } },
            supplier: { select: { legalName: true, tradeName: true } },
          },
        },
        noShowEvidence: { select: { gpsMapLink: true, imageUrls: true } },
        inPlaceEvidence: { select: { gpsMapLink: true, imageUrls: true } },
        completedEvidence: { select: { gpsMapLink: true, imageUrls: true } },
      },
      orderBy: { jobDate: 'asc' },
    });

    function resolveDriver(a: typeof jobs[number]['assignment']) {
      if (!a) return '—';
      if (a.driver?.name) return a.driver.name;
      if ((a as any).externalDriverName) return (a as any).externalDriverName;
      if (a.supplier) return (a.supplier as any).tradeName ?? a.supplier.legalName;
      return '—';
    }

    const rows = jobs.map((j) => {
      const origin = j.originAirport ? `${j.originAirport.name} (${j.originAirport.code})` : (j.originHotel?.name ?? j.fromZone?.name ?? '—');
      const dest = j.destinationAirport ? `${j.destinationAirport.name} (${j.destinationAirport.code})` : (j.destinationHotel?.name ?? j.toZone?.name ?? '—');
      const noShowPhotos = j.noShowEvidence.reduce((s, e) => s + e.imageUrls.length, 0);
      const inPlacePhotos = j.inPlaceEvidence.reduce((s, e) => s + e.imageUrls.length, 0);
      const completedPhotos = j.completedEvidence.reduce((s, e) => s + e.imageUrls.length, 0);
      const noShowGps = j.noShowEvidence.map((e) => e.gpsMapLink).filter(Boolean).join(', ');
      const inPlaceGps = j.inPlaceEvidence.map((e) => e.gpsMapLink).filter(Boolean).join(', ');
      const completedGps = j.completedEvidence.map((e) => e.gpsMapLink).filter(Boolean).join(', ');
      return {
        'Internal Ref': j.internalRef,
        'Agent Name': j.agent?.legalName ?? '—',
        'Agent Ref': j.agentRef ?? '—',
        'Service Date': j.jobDate.toISOString().split('T')[0],
        'Service Type': serviceTypeLabel(j.serviceType),
        'Status': j.status,
        'Pax': j.paxCount,
        'Client': j.clientName ?? '—',
        'Origin': origin,
        'Destination': dest,
        'Flight No': j.flight?.flightNo ?? '—',
        'Driver': resolveDriver(j.assignment),
        'Rep': j.assignment?.rep?.name ?? '—',
        'Plate': j.assignment?.vehicle?.plateNumber ?? '—',
        'Has Evidence': (noShowPhotos + inPlacePhotos + completedPhotos) > 0 ? 'Yes' : 'No',
        'No-Show Photos': noShowPhotos,
        'No-Show GPS': noShowGps || '—',
        'In-Place Photos': inPlacePhotos,
        'In-Place GPS': inPlaceGps || '—',
        'Completed Photos': completedPhotos,
        'Completed GPS': completedGps || '—',
      };
    });

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    this.autoSizeColumns(ws, rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Evidence Report');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // DRIVER SCORE EXCEL EXPORT
  // ─────────────────────────────────────────────

  async exportDriverScoreReport(from: string, to: string, driverId?: string): Promise<Buffer> {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    function calcDriverScore(s: { attendance: boolean; appearance: boolean; carCleanliness: boolean; maintenance: boolean; work: boolean }) {
      return (s.attendance ? 30 : 0) + (s.appearance ? 20 : 0) + (s.carCleanliness ? 10 : 0) + (s.maintenance ? 10 : 0) + (s.work ? 30 : 0);
    }
    function driverScoreToEval(total: number) {
      if (total >= 90) return 'Excellent';
      if (total >= 70) return 'Good';
      if (total >= 50) return 'Average';
      return 'Poor';
    }
    function driverScoreToMultiplier(total: number) {
      if (total >= 90) return 1.0;
      if (total >= 70) return 0.9;
      if (total >= 50) return 0.75;
      return 0.5;
    }

    const scores = await this.prisma.driverJobScore.findMany({
      where: {
        ...(driverId ? { driverId } : {}),
        trafficJob: { jobDate: { gte: fromDate, lte: toDate }, deletedAt: null },
      },
      include: {
        driver: { select: { name: true } },
        trafficJob: {
          include: {
            fromZone: { select: { name: true } },
            toZone: { select: { name: true } },
            originAirport: { select: { code: true } },
            destinationAirport: { select: { code: true } },
          },
        },
      },
      orderBy: [{ trafficJob: { jobDate: 'asc' } }, { driver: { name: 'asc' } }],
    });

    const rows = scores.map((s) => {
      const total = calcDriverScore(s);
      const from = s.trafficJob.originAirport?.code ?? s.trafficJob.fromZone?.name ?? '—';
      const to = s.trafficJob.destinationAirport?.code ?? s.trafficJob.toZone?.name ?? '—';
      return {
        'Internal Ref': s.trafficJob.internalRef,
        'Job Date': s.trafficJob.jobDate.toISOString().split('T')[0],
        'Service Type': serviceTypeLabel(s.trafficJob.serviceType),
        'Pax': s.trafficJob.paxCount,
        'Status': s.trafficJob.status,
        'Driver': s.driver.name,
        'Route': `${from} → ${to}`,
        'Attendance': s.attendance ? 'Yes' : 'No',
        'Appearance': s.appearance ? 'Yes' : 'No',
        'Car Cleanliness': s.carCleanliness ? 'Yes' : 'No',
        'Maintenance': s.maintenance ? 'Yes' : 'No',
        'Work': s.work ? 'Yes' : 'No',
        'Total Score': total,
        'Fee %': Math.round(driverScoreToMultiplier(total) * 100),
        'Evaluation': driverScoreToEval(total),
      };
    });

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    this.autoSizeColumns(ws, rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Driver Score');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // REP SCORE EXCEL EXPORT
  // ─────────────────────────────────────────────

  async exportRepScoreReport(from: string, to: string, repId?: string): Promise<Buffer> {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const scores = await this.prisma.repJobScore.findMany({
      where: {
        ...(repId ? { repId } : {}),
        trafficJob: { jobDate: { gte: fromDate, lte: toDate }, deletedAt: null },
      },
      include: {
        rep: { select: { name: true } },
        trafficJob: {
          include: {
            originAirport: { select: { code: true } },
            originHotel: { select: { name: true } },
            originZone: { select: { name: true } },
            destinationAirport: { select: { code: true } },
            destinationHotel: { select: { name: true } },
            destinationZone: { select: { name: true } },
            flight: { select: { flightNo: true, carrier: true } },
          },
        },
      },
      orderBy: [{ rep: { name: 'asc' } }, { trafficJob: { jobDate: 'asc' } }],
    });

    const rows = scores.map((s) => {
      const total = calcRepScore(s);
      const { fee, evaluation } = scoreToFeeAndEval(total);
      const origin = s.trafficJob.originAirport?.code ?? s.trafficJob.originHotel?.name ?? s.trafficJob.originZone?.name ?? '—';
      const dest = s.trafficJob.destinationAirport?.code ?? s.trafficJob.destinationHotel?.name ?? s.trafficJob.destinationZone?.name ?? '—';
      return {
        'Internal Ref': s.trafficJob.internalRef,
        'Service Type': serviceTypeLabel(s.trafficJob.serviceType),
        'Pax': s.trafficJob.paxCount,
        'Status': s.trafficJob.status,
        'Rep': s.rep.name,
        'Origin': origin,
        'Destination': dest,
        'Flight No': s.trafficJob.flight?.flightNo ?? '—',
        'Carrier': s.trafficJob.flight?.carrier ?? '—',
        'Attendance': s.attendance ? 'Yes' : 'No',
        'Appearance': s.appearance ? 'Yes' : 'No',
        'Work': s.work ? 'Yes' : 'No',
        'Survey': s.survey ? 'Yes' : 'No',
        'Review': s.review ? 'Yes' : 'No',
        'Total Score': total,
        'Fee (EGP)': fee,
        'Evaluation': evaluation,
      };
    });

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    this.autoSizeColumns(ws, rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Rep Score');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // GUEST SURVEY EXCEL EXPORT
  // ─────────────────────────────────────────────

  async exportGuestSurveyReport(from: string, to: string, repId?: string): Promise<Buffer> {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const surveys = await this.prisma.guestSurvey.findMany({
      where: {
        ...(repId ? { repId } : {}),
        trafficJob: { jobDate: { gte: fromDate, lte: toDate }, deletedAt: null },
      },
      include: {
        rep: { select: { name: true } },
        trafficJob: { select: { internalRef: true, jobDate: true, serviceType: true } },
      },
      orderBy: [{ rep: { name: 'asc' } }, { createdAt: 'asc' }],
    });

    const rows = surveys.map((s) => ({
      'Date': this.formatDate(s.trafficJob.jobDate),
      'Submitted': this.cairoDate(s.createdAt),
      'Rep': s.rep.name,
      'Job Ref': s.trafficJob.internalRef,
      'Service Type': serviceTypeLabel(s.trafficJob.serviceType),
      'Flight No': s.flightNo ?? '',
      'Hotel': s.hotelName ?? '',
      'Nationality': s.guestNationality ?? '',
      'Age Range': s.ageRange ?? '',
      'Adults': s.noOfAdults,
      'Children': s.noOfChildren,
      'Infants': s.noOfInfants,
      'Stay Length': s.stayLength ?? '',
      'Repeat Guest': s.repeaterGuest ?? '',
      'Local Travel Agent': s.localTravelAgent ?? '',
      'Contact Number': s.contactNumber ?? '',
      'Email': s.email ?? '',
      'General Comment': s.generalComment ?? '',
    }));

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    this.autoSizeColumns(ws, rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Guest Surveys');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // JOB STATUS EXCEL EXPORT
  // ─────────────────────────────────────────────

  async exportJobStatusReport(from: string, to: string, status?: string, repId?: string, repStatus?: string, driverStatus?: string, serviceType?: string): Promise<Buffer> {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const where: Record<string, unknown> = { jobDate: { gte: fromDate, lte: toDate }, deletedAt: null };
    if (status && status !== 'ALL') {
      const statusList = status.split(',').map((s) => s.trim()).filter(Boolean);
      where.status = statusList.length === 1 ? statusList[0] : { in: statusList };
    }
    if (serviceType && serviceType !== 'ALL') where.serviceType = serviceType;

    const assignmentFilter: Record<string, unknown> = {};
    if (repId && repId !== 'ALL') assignmentFilter.repId = repId;
    if (repStatus && repStatus !== 'ALL') assignmentFilter.repStatus = repStatus;
    if (driverStatus && driverStatus !== 'ALL') assignmentFilter.driverStatus = driverStatus;
    if (Object.keys(assignmentFilter).length > 0) where.assignment = assignmentFilter;

    const jobs = await this.prisma.trafficJob.findMany({
      where,
      include: {
        agent: { select: { legalName: true, tradeName: true } },
        assignment: {
          select: {
            driverStatus: true,
            repStatus: true,
            externalDriverName: true,
            driver: { select: { name: true } },
            rep: { select: { name: true } },
            supplier: { select: { legalName: true, tradeName: true } },
          },
        },
        flight: { select: { arrivalTime: true, flightNo: true } },
      },
      orderBy: { jobDate: 'asc' },
    });

    function resolveDriver(a: { driver?: { name: string } | null; externalDriverName?: string | null; supplier?: { tradeName?: string | null; legalName: string } | null } | null) {
      if (!a) return '—';
      if (a.driver?.name) return a.driver.name;
      if (a.externalDriverName) return a.externalDriverName;
      if (a.supplier) return a.supplier.tradeName ?? a.supplier.legalName;
      return '—';
    }

    const rows = jobs.map((j) => ({
      'Internal Ref': j.internalRef,
      'Agent Ref': j.agentRef ?? '—',
      'Agent': j.agent?.tradeName ?? j.agent?.legalName ?? '—',
      'Service Date': j.jobDate.toISOString().split('T')[0],
      'Service Type': serviceTypeLabel(j.serviceType),
      'Time': j.serviceType === 'ARR' ? this.cairoTime(j.flight?.arrivalTime ?? null) : this.cairoTime(j.pickUpTime ?? null),
      'Flight No': j.flight?.flightNo ?? '—',
      'Price': j.priceAmount ? Number(j.priceAmount) : '—',
      'Price Currency': j.priceCurrency ?? '—',
      'Transfer Price': j.transferPrice ? Number(j.transferPrice) : '—',
      'Transfer Currency': j.transferPriceCurrency ?? '—',
      'Status': j.status,
      'Rep Status': j.assignment?.repStatus ?? '—',
      'Driver Status': j.assignment?.driverStatus ?? '—',
      'Rep': j.assignment?.rep?.name ?? '—',
      'Driver': resolveDriver(j.assignment ?? null),
    }));

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    this.autoSizeColumns(ws, rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Job Status');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // DEPARTURE EXCEL EXPORT
  // ─────────────────────────────────────────────

  async exportDepartureReport(from: string, to: string, serviceType?: string): Promise<Buffer> {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const where: Record<string, unknown> = { jobDate: { gte: fromDate, lte: toDate }, deletedAt: null };
    if (serviceType && serviceType !== 'ALL') where.serviceType = serviceType;

    const jobs = await this.prisma.trafficJob.findMany({
      where,
      orderBy: [{ jobDate: 'asc' }, { pickUpTime: 'asc' }],
    });

    const rows = jobs.map((j) => ({
      'Service Date': j.jobDate.toISOString().split('T')[0],
      'Service Type': serviceTypeLabel(j.serviceType),
      'Customer Name': j.clientName ?? '—',
      'Customer Number': j.clientMobile ?? '—',
      'Pax': j.paxCount,
      'Pickup Time': this.cairoTime(j.pickUpTime ?? null),
    }));

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    this.autoSizeColumns(ws, rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Departure Report');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // FLIGHT DELAY EXCEL EXPORT
  // ─────────────────────────────────────────────

  async exportFlightDelayReport(from: string, to: string, repName?: string): Promise<Buffer> {
    const fromDate = new Date(from);
    const toDate = new Date(to);
    toDate.setHours(23, 59, 59, 999);

    const notifications = await this.prisma.userNotification.findMany({
      where: {
        type: 'FLIGHT_DELAY' as any,
        trafficJobId: { not: null },
        createdAt: { gte: fromDate, lte: toDate },
      },
      include: {
        trafficJob: {
          select: {
            internalRef: true,
            agentRef: true,
            jobDate: true,
            assignment: { select: { rep: { select: { name: true } } } },
          },
        },
      },
      orderBy: [{ trafficJobId: 'asc' }, { createdAt: 'asc' }],
    });

    const fmtTime = (d: Date) =>
      d.toLocaleTimeString('en-GB', { timeZone: 'Africa/Cairo', hour: '2-digit', minute: '2-digit', hour12: false });

    const seen = new Set<string>();
    const rows: Record<string, unknown>[] = [];

    for (const n of notifications) {
      const meta = n.metadata as { repName?: string; oldArrivalTime?: string | null; newArrivalTime?: string } | null;
      if (!meta?.newArrivalTime) continue;
      const key = `${n.trafficJobId}|${meta.newArrivalTime}`;
      if (seen.has(key)) continue;
      seen.add(key);

      const reportedBy = meta.repName ?? '—';
      if (repName && repName !== 'ALL' && reportedBy !== repName) continue;

      const currentRepName = (n.trafficJob as any)?.assignment?.rep?.name ?? null;
      const oldArr = meta.oldArrivalTime ? new Date(meta.oldArrivalTime) : null;
      const newArr = new Date(meta.newArrivalTime);

      rows.push({
        'Internal Ref': (n.trafficJob as any)?.internalRef ?? '—',
        'Agent Ref': (n.trafficJob as any)?.agentRef ?? '—',
        'Job Date': (n.trafficJob as any)?.jobDate?.toISOString().split('T')[0] ?? '—',
        'Old Arrival Date': this.cairoDate(oldArr),
        'Old Arrival Time': oldArr ? fmtTime(oldArr) : '—',
        'New Arrival Date': this.cairoDate(newArr),
        'New Arrival Time': fmtTime(newArr),
        'Reported By': reportedBy,
        'Current Rep': currentRepName && currentRepName !== reportedBy ? currentRepName : '—',
        'Reported At': this.cairoDateTime(n.createdAt),
      });
    }

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    this.autoSizeColumns(ws, rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Flight Delay');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // SUPPLIER JOBS EXCEL EXPORT
  // ─────────────────────────────────────────────

  async exportSupplierJobsExcel(from: string, to: string, supplierId?: string, supplierStatus?: string): Promise<Buffer> {
    const { rows } = await this.getSupplierJobsReport({ from, to, supplierId, supplierStatus });

    const data = rows.map((r) => ({
      'Job Ref': r.jobRef,
      'Agent Name': r.agentName,
      'Agent Ref': r.agentRef,
      'Service Date': r.serviceDate instanceof Date ? r.serviceDate.toISOString().split('T')[0] : String(r.serviceDate).split('T')[0],
      'Route': r.route,
      'Supplier': r.supplierName,
      'Supplier Status': r.supplierStatus,
    }));

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(data);
    this.autoSizeColumns(ws, data);
    XLSX.utils.book_append_sheet(wb, ws, 'Supplier Jobs');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // CAR JOBS EXCEL EXPORT
  // ─────────────────────────────────────────────

  async exportCarJobsExcel(from: string, to: string, vehicleId?: string): Promise<Buffer> {
    const { rows } = await this.getCarJobsReport({ from, to, vehicleId });

    const data = rows.map((r) => ({
      'Job Ref': r.jobRef,
      'Agent Name': r.agentName,
      'Service Date': r.serviceDate instanceof Date ? r.serviceDate.toISOString().split('T')[0] : String(r.serviceDate).split('T')[0],
      'Origin': r.origin,
      'Destination': r.destination,
      'Driver': r.driver,
      'Status': r.jobStatus,
      'Plate Number': r.plateNumber,
      'Transfer Price': r.transferPrice ?? '—',
      'Currency': r.transferPriceCurrency,
    }));

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(data);
    this.autoSizeColumns(ws, data);
    XLSX.utils.book_append_sheet(wb, ws, 'Car Jobs');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // REVIEW REPORT EXCEL EXPORT
  // ─────────────────────────────────────────────

  async exportReviewReport(from: string, to: string, status?: string): Promise<Buffer> {
    const fromDate = new Date(from);
    const toDate = new Date(to);
    toDate.setHours(23, 59, 59, 999);

    const where: Record<string, unknown> = { jobDate: { gte: fromDate, lte: toDate }, deletedAt: null };
    if (status && status !== 'ALL') {
      const statusList = status.split(',').map((s) => s.trim()).filter(Boolean);
      where.status = statusList.length === 1 ? statusList[0] : { in: statusList };
    }

    const jobs = await this.prisma.trafficJob.findMany({
      where,
      include: {
        agent: { select: { legalName: true, tradeName: true } },
        originAirport: { select: { code: true } },
        originZone: { select: { name: true } },
        originHotel: { select: { name: true } },
        destinationAirport: { select: { code: true } },
        destinationZone: { select: { name: true } },
        destinationHotel: { select: { name: true } },
        assignment: {
          select: {
            driver: { select: { name: true } },
            externalDriverName: true,
            supplier: { select: { legalName: true, tradeName: true } },
            rep: { select: { name: true } },
          },
        },
      },
      orderBy: [{ jobDate: 'asc' }, { internalRef: 'asc' }],
    });

    function resolveDriver(a: { driver?: { name: string } | null; externalDriverName?: string | null; supplier?: { tradeName?: string | null; legalName: string } | null } | null) {
      if (!a) return '—';
      if (a.driver?.name) return a.driver.name;
      if (a.externalDriverName) return a.externalDriverName;
      if (a.supplier) return a.supplier.tradeName ?? a.supplier.legalName;
      return '—';
    }

    const rows = jobs.map((j) => ({
      'Internal Ref': j.internalRef,
      'Agent Name': j.agent?.tradeName ?? j.agent?.legalName ?? '—',
      'Agent Ref': j.agentRef ?? '—',
      'Service Date': j.jobDate.toISOString().split('T')[0],
      'Service Type': serviceTypeLabel(j.serviceType),
      'Status': j.status,
      'Pax': j.paxCount,
      'Client': j.clientName ?? '—',
      'Origin': j.originHotel?.name ?? j.originZone?.name ?? j.originAirport?.code ?? '—',
      'Destination': j.destinationHotel?.name ?? j.destinationZone?.name ?? j.destinationAirport?.code ?? '—',
      'Driver Name': resolveDriver(j.assignment ?? null),
      'Rep Name': j.assignment?.rep?.name ?? '—',
      'Notes': j.notes ?? '',
    }));

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    this.autoSizeColumns(ws, rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Review Report');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  /** Build a Prisma date range filter for a given field. Both bounds are optional. */
  private buildDateFilter(
    dateFrom: string | undefined,
    dateTo: string | undefined,
    field: string,
  ): Record<string, unknown> {
    if (!dateFrom && !dateTo) return {};
    const filter: Record<string, Date> = {};
    if (dateFrom) filter['gte'] = new Date(dateFrom);
    if (dateTo) {
      const end = new Date(dateTo);
      end.setHours(23, 59, 59, 999);
      filter['lte'] = end;
    }
    return { [field]: filter };
  }
}
