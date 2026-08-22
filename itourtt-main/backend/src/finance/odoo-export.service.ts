import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import * as XLSX from 'xlsx';

const COUNTRY_MAP: Record<string, string> = {
  Egypt: 'base.eg',
  'Saudi Arabia': 'base.sa',
  UAE: 'base.ae',
  Jordan: 'base.jo',
  Kuwait: 'base.kw',
};

function countryRef(country: string | null): string {
  if (!country) return 'base.eg';
  return COUNTRY_MAP[country] ?? 'base.eg';
}

function toDate(d: Date | null | undefined): string {
  if (!d) return '';
  return d.toISOString().slice(0, 10);
}

function toNum(v: unknown): number {
  return Number(v ?? 0);
}

// Wrap a single worksheet in a workbook (used for one-sheet CSV exports).
function wb_single(ws: XLSX.WorkSheet, sheetName: string): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, sheetName);
  return wb;
}

@Injectable()
export class OdooExportService {
  constructor(private readonly prisma: PrismaService) {}

  // ─────────────────────────────────────────────
  // 1. res.partner — Agents (customers) + Suppliers (vendors)
  // ─────────────────────────────────────────────

  async exportPartners(): Promise<Buffer> {
    const [agents, suppliers] = await Promise.all([
      this.prisma.agent.findMany({
        where: { deletedAt: null },
        select: {
          id: true,
          legalName: true,
          tradeName: true,
          taxId: true,
          address: true,
          city: true,
          country: true,
          phone: true,
          email: true,
        },
        orderBy: { legalName: 'asc' },
      }),
      this.prisma.supplier.findMany({
        where: { deletedAt: null },
        select: {
          id: true,
          legalName: true,
          tradeName: true,
          taxId: true,
          address: true,
          city: true,
          country: true,
          phone: true,
          email: true,
        },
        orderBy: { legalName: 'asc' },
      }),
    ]);

    const headers = [
      'id',              // External ID
      'name',
      'company_type',
      'vat',
      'street',
      'city',
      'country_id/id',
      'phone',
      'email',
      'customer_rank',
      'supplier_rank',
      'lang',
      'comment',
    ];

    const rows: unknown[][] = [headers];

    for (const a of agents) {
      rows.push([
        `itour_agent_${a.id}`,
        a.legalName,
        'company',
        a.taxId ?? '',
        a.address ?? '',
        a.city ?? '',
        countryRef(a.country),
        a.phone ?? '',
        a.email ?? '',
        1,
        0,
        'en_US',
        a.tradeName ? `Trade name: ${a.tradeName}` : '',
      ]);
    }

    for (const s of suppliers) {
      rows.push([
        `itour_supplier_${s.id}`,
        s.legalName,
        'company',
        s.taxId ?? '',
        s.address ?? '',
        s.city ?? '',
        countryRef(s.country),
        s.phone ?? '',
        s.email ?? '',
        0,
        1,
        'en_US',
        s.tradeName ? `Trade name: ${s.tradeName}` : '',
      ]);
    }

    const ws = XLSX.utils.aoa_to_sheet(rows);
    ws['!cols'] = [
      { wch: 30 }, { wch: 35 }, { wch: 14 }, { wch: 18 },
      { wch: 30 }, { wch: 15 }, { wch: 12 }, { wch: 18 },
      { wch: 28 }, { wch: 14 }, { wch: 14 }, { wch: 8 }, { wch: 30 },
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'res.partner');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // 2. account.move (out_invoice) — Agent invoices
  // ─────────────────────────────────────────────

  async exportCustomerInvoices(dateFrom?: string, dateTo?: string): Promise<Buffer> {
    const invoices = await this.prisma.agentInvoice.findMany({
      where: {
        status: { in: ['POSTED', 'PAID'] },
        agentId: { not: null },
        ...(dateFrom || dateTo
          ? {
              invoiceDate: {
                ...(dateFrom ? { gte: new Date(dateFrom) } : {}),
                ...(dateTo ? { lte: new Date(dateTo) } : {}),
              },
            }
          : {}),
      },
      include: {
        agent: { select: { id: true, legalName: true } },
        lines: { orderBy: { id: 'asc' } },
      },
      orderBy: { invoiceDate: 'asc' },
    });

    const headers = [
      'id',                           // External ID (first line only)
      'move_type',
      'partner_id/id',
      'partner_id/name',
      'invoice_date',
      'invoice_date_due',
      'currency_id/name',
      'ref',                          // Invoice number
      'invoice_line_ids/sequence',
      'invoice_line_ids/name',
      'invoice_line_ids/quantity',
      'invoice_line_ids/price_unit',
      'invoice_line_ids/tax_ids/amount',
      'invoice_line_ids/price_subtotal',
      'invoice_line_ids/price_total',
      'amount_untaxed',               // First line only
      'amount_tax',                   // First line only
      'amount_total',                 // First line only
      'state',
    ];

    const rows: unknown[][] = [headers];

    for (const inv of invoices) {
      for (let i = 0; i < inv.lines.length; i++) {
        const line = inv.lines[i];
        const isFirst = i === 0;
        rows.push([
          isFirst ? `itour_inv_${inv.id}` : '',
          'out_invoice',
          inv.agent ? `itour_agent_${inv.agent.id}` : '',
          inv.agent?.legalName ?? '',
          toDate(inv.invoiceDate),
          toDate(inv.dueDate),
          inv.currency,
          inv.invoiceNumber,
          i + 1,
          line.description,
          toNum(line.quantity),
          toNum(line.unitPrice),
          toNum(line.taxRate),
          toNum(line.unitPrice) * toNum(line.quantity),
          toNum(line.lineTotal),
          isFirst ? toNum(inv.subtotal) : '',
          isFirst ? toNum(inv.taxAmount) : '',
          isFirst ? toNum(inv.total) : '',
          'posted',
        ]);
      }
    }

    const ws = XLSX.utils.aoa_to_sheet(rows);
    ws['!cols'] = [
      { wch: 28 }, { wch: 12 }, { wch: 28 }, { wch: 32 },
      { wch: 12 }, { wch: 12 }, { wch: 8 }, { wch: 20 },
      { wch: 8 }, { wch: 40 }, { wch: 8 }, { wch: 12 },
      { wch: 10 }, { wch: 14 }, { wch: 14 }, { wch: 14 },
      { wch: 12 }, { wch: 14 }, { wch: 10 },
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'account.move (invoices)');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // 2b. B2C — guests as res.partner + invoices as account.move (out_invoice)
  // ─────────────────────────────────────────────

  // Stable Odoo external id for a guest: registered B2C clients dedupe by their
  // user id; walk-in guests (no account) dedupe by email so repeat guests map to
  // one partner. Both invoice and partner files MUST derive the id the same way.
  private b2cPartnerId(inv: {
    b2cClientId: string | null;
    guestBooking: { guestEmail: string; id: string };
  }): string {
    if (inv.b2cClientId) return `itour_b2c_${inv.b2cClientId}`;
    const email = (inv.guestBooking.guestEmail || '').trim().toLowerCase();
    if (email) return `itour_b2cguest_${email.replace(/[^a-z0-9]+/g, '_')}`;
    return `itour_b2cguest_${inv.guestBooking.id}`;
  }

  private b2cInvoiceWhere(dateFrom?: string, dateTo?: string) {
    return {
      deletedAt: null,
      ...(dateFrom || dateTo
        ? {
            issuedAt: {
              ...(dateFrom ? { gte: new Date(dateFrom) } : {}),
              ...(dateTo ? { lte: new Date(dateTo) } : {}),
            },
          }
        : {}),
    };
  }

  private readonly b2cInvoiceInclude = {
    b2cClient: { select: { id: true, name: true, email: true } },
    guestBooking: {
      select: {
        id: true,
        guestName: true,
        guestEmail: true,
        guestPhone: true,
        guestCountry: true,
        serviceType: true,
        fromZone: { select: { name: true } },
        toZone: { select: { name: true } },
        originAirport: { select: { name: true } },
        destinationAirport: { select: { name: true } },
      },
    },
  } as const;

  /** res.partner CSV for B2C guests that have an invoice (customers). */
  async exportB2CPartners(dateFrom?: string, dateTo?: string): Promise<Buffer> {
    const invoices = await this.prisma.b2CInvoice.findMany({
      where: this.b2cInvoiceWhere(dateFrom, dateTo),
      include: this.b2cInvoiceInclude,
      orderBy: { issuedAt: 'asc' },
    });

    const headers = [
      'id', 'name', 'company_type', 'vat', 'street', 'city',
      'country_id/id', 'phone', 'email', 'customer_rank', 'supplier_rank',
      'lang', 'comment',
    ];
    const rows: unknown[][] = [headers];

    // One row per distinct partner.
    const seen = new Set<string>();
    for (const inv of invoices) {
      const pid = this.b2cPartnerId(inv);
      if (seen.has(pid)) continue;
      seen.add(pid);
      const b = inv.guestBooking;
      rows.push([
        pid,
        inv.b2cClient?.name || b.guestName,
        'person',
        '',                                   // guests have no VAT
        '',                                   // no street stored
        '',
        countryRef(b.guestCountry),
        b.guestPhone ?? '',
        inv.b2cClient?.email || b.guestEmail || '',
        1,                                    // customer_rank
        0,
        'en_US',
        'B2C website guest',
      ]);
    }

    const ws = XLSX.utils.aoa_to_sheet(rows);
    return Buffer.from(XLSX.write(wb_single(ws, 'res.partner'), { type: 'buffer', bookType: 'csv' }));
  }

  /** account.move (out_invoice) CSV for B2C guest invoices. */
  async exportB2CCustomerInvoices(dateFrom?: string, dateTo?: string): Promise<Buffer> {
    const invoices = await this.prisma.b2CInvoice.findMany({
      where: this.b2cInvoiceWhere(dateFrom, dateTo),
      include: this.b2cInvoiceInclude,
      orderBy: { issuedAt: 'asc' },
    });

    const headers = [
      'id', 'move_type', 'partner_id/id', 'partner_id/name',
      'invoice_date', 'invoice_date_due', 'currency_id/name', 'ref',
      'invoice_line_ids/sequence', 'invoice_line_ids/name',
      'invoice_line_ids/quantity', 'invoice_line_ids/price_unit',
      'invoice_line_ids/tax_ids/amount', 'invoice_line_ids/price_subtotal',
      'invoice_line_ids/price_total',
      'amount_untaxed', 'amount_tax', 'amount_total', 'state',
    ];
    const rows: unknown[][] = [headers];

    for (const inv of invoices) {
      const b = inv.guestBooking;
      const origin = b.originAirport?.name || b.fromZone?.name || '-';
      const dest = b.destinationAirport?.name || b.toZone?.name || '-';
      const serviceLabel =
        b.serviceType === 'ARR' ? 'Arrival transfer'
        : b.serviceType === 'DEP' ? 'Departure transfer'
        : 'City transfer';
      const subtotal = toNum(inv.subtotal);
      const tax = toNum(inv.taxAmount);
      const taxRate = subtotal > 0 ? Math.round((tax / subtotal) * 100) : 0;
      rows.push([
        `itour_b2cinv_${inv.id}`,
        'out_invoice',
        this.b2cPartnerId(inv),
        inv.b2cClient?.name || b.guestName,
        toDate(inv.issuedAt),
        toDate(inv.issuedAt),                 // B2C is paid up-front: due = issued
        inv.currency,
        inv.invoiceNumber,
        1,
        `${serviceLabel}: ${origin} > ${dest}`,
        1,
        subtotal,
        taxRate,
        subtotal,
        toNum(inv.total),
        subtotal,
        tax,
        toNum(inv.total),
        'posted',
      ]);
    }

    const ws = XLSX.utils.aoa_to_sheet(rows);
    return Buffer.from(XLSX.write(wb_single(ws, 'account.move (b2c)'), { type: 'buffer', bookType: 'csv' }));
  }

  // ─────────────────────────────────────────────
  // 3. account.move (in_invoice) — Vendor bills from supplier costs
  // ─────────────────────────────────────────────

  async exportVendorBills(dateFrom?: string, dateTo?: string): Promise<Buffer> {
    const costs = await this.prisma.supplierCost.findMany({
      where: {
        isPosted: true,
        ...(dateFrom || dateTo
          ? {
              createdAt: {
                ...(dateFrom ? { gte: new Date(dateFrom) } : {}),
                ...(dateTo ? { lte: new Date(dateTo) } : {}),
              },
            }
          : {}),
      },
      include: {
        supplier: { select: { id: true, legalName: true } },
        trafficJob: {
          select: {
            internalRef: true,
            jobDate: true,
            serviceType: true,
          },
        },
      },
      orderBy: { createdAt: 'asc' },
    });

    const headers = [
      'id',
      'move_type',
      'partner_id/id',
      'partner_id/name',
      'invoice_date',
      'currency_id/name',
      'ref',
      'invoice_line_ids/sequence',
      'invoice_line_ids/name',
      'invoice_line_ids/quantity',
      'invoice_line_ids/price_unit',
      'invoice_line_ids/tax_ids/amount',
      'invoice_line_ids/price_total',
      'amount_total',
      'state',
    ];

    const rows: unknown[][] = [headers];

    for (const cost of costs) {
      rows.push([
        `itour_bill_${cost.id}`,
        'in_invoice',
        `itour_supplier_${cost.supplierId}`,
        cost.supplier.legalName,
        toDate(cost.createdAt),
        cost.currency,
        cost.trafficJob.internalRef,
        1,
        `Transport service – ${cost.trafficJob.serviceType} – ${toDate(cost.trafficJob.jobDate)}`,
        1,
        toNum(cost.amount),
        0,
        toNum(cost.amount),
        toNum(cost.amount),
        'posted',
      ]);
    }

    const ws = XLSX.utils.aoa_to_sheet(rows);
    ws['!cols'] = [
      { wch: 28 }, { wch: 12 }, { wch: 28 }, { wch: 32 },
      { wch: 12 }, { wch: 8 }, { wch: 18 }, { wch: 8 },
      { wch: 44 }, { wch: 8 }, { wch: 12 }, { wch: 10 },
      { wch: 14 }, { wch: 14 }, { wch: 10 },
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'account.move (bills)');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // 4. account.payment — Customer payments
  // ─────────────────────────────────────────────

  async exportPayments(dateFrom?: string, dateTo?: string): Promise<Buffer> {
    const payments = await this.prisma.payment.findMany({
      where: {
        isPosted: true,
        ...(dateFrom || dateTo
          ? {
              paymentDate: {
                ...(dateFrom ? { gte: new Date(dateFrom) } : {}),
                ...(dateTo ? { lte: new Date(dateTo) } : {}),
              },
            }
          : {}),
      },
      include: {
        agentInvoice: {
          include: {
            agent: { select: { id: true, legalName: true } },
          },
        },
      },
      orderBy: { paymentDate: 'asc' },
    });

    const methodMap: Record<string, string> = {
      CASH: 'cash',
      BANK_TRANSFER: 'bank',
      CHECK: 'check',
    };

    const headers = [
      'id',
      'payment_type',
      'partner_type',
      'partner_id/id',
      'partner_id/name',
      'date',
      'amount',
      'currency_id/name',
      'journal_id/name',
      'ref',
      'invoice_ids/id',
    ];

    const rows: unknown[][] = [headers];

    for (const p of payments) {
      rows.push([
        `itour_payment_${p.id}`,
        'inbound',
        'customer',
        p.agentInvoice.agent ? `itour_agent_${p.agentInvoice.agent.id}` : '',
        p.agentInvoice.agent?.legalName ?? '',
        toDate(p.paymentDate),
        toNum(p.amount),
        p.currency,
        methodMap[p.paymentMethod] ?? 'cash',
        p.reference ?? p.agentInvoice.invoiceNumber,
        `itour_inv_${p.agentInvoiceId}`,
      ]);
    }

    const ws = XLSX.utils.aoa_to_sheet(rows);
    ws['!cols'] = [
      { wch: 28 }, { wch: 12 }, { wch: 12 }, { wch: 28 },
      { wch: 32 }, { wch: 12 }, { wch: 14 }, { wch: 8 },
      { wch: 14 }, { wch: 22 }, { wch: 28 },
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'account.payment');
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }

  // ─────────────────────────────────────────────
  // 5. Combined workbook (all 4 sheets in one file)
  // ─────────────────────────────────────────────

  async exportAllInOne(dateFrom?: string, dateTo?: string): Promise<Buffer> {
    const [agents, suppliers, invoices, costs, payments] = await Promise.all([
      this.prisma.agent.findMany({
        where: { deletedAt: null },
        select: { id: true, legalName: true, tradeName: true, taxId: true, address: true, city: true, country: true, phone: true, email: true },
        orderBy: { legalName: 'asc' },
      }),
      this.prisma.supplier.findMany({
        where: { deletedAt: null },
        select: { id: true, legalName: true, tradeName: true, taxId: true, address: true, city: true, country: true, phone: true, email: true },
        orderBy: { legalName: 'asc' },
      }),
      this.prisma.agentInvoice.findMany({
        where: {
          status: { in: ['POSTED', 'PAID'] },
          agentId: { not: null },
          ...(dateFrom || dateTo ? { invoiceDate: { ...(dateFrom ? { gte: new Date(dateFrom) } : {}), ...(dateTo ? { lte: new Date(dateTo) } : {}) } } : {}),
        },
        include: { agent: { select: { id: true, legalName: true } }, lines: { orderBy: { id: 'asc' } } },
        orderBy: { invoiceDate: 'asc' },
      }),
      this.prisma.supplierCost.findMany({
        where: {
          isPosted: true,
          ...(dateFrom || dateTo ? { createdAt: { ...(dateFrom ? { gte: new Date(dateFrom) } : {}), ...(dateTo ? { lte: new Date(dateTo) } : {}) } } : {}),
        },
        include: { supplier: { select: { id: true, legalName: true } }, trafficJob: { select: { internalRef: true, jobDate: true, serviceType: true } } },
        orderBy: { createdAt: 'asc' },
      }),
      this.prisma.payment.findMany({
        where: {
          isPosted: true,
          ...(dateFrom || dateTo ? { paymentDate: { ...(dateFrom ? { gte: new Date(dateFrom) } : {}), ...(dateTo ? { lte: new Date(dateTo) } : {}) } } : {}),
        },
        include: { agentInvoice: { include: { agent: { select: { id: true, legalName: true } } } } },
        orderBy: { paymentDate: 'asc' },
      }),
    ]);

    const wb = XLSX.utils.book_new();

    // Sheet 1: Partners
    const partnerRows: unknown[][] = [
      ['id', 'name', 'company_type', 'vat', 'street', 'city', 'country_id/id', 'phone', 'email', 'customer_rank', 'supplier_rank', 'lang', 'comment'],
      ...agents.map(a => [`itour_agent_${a.id}`, a.legalName, 'company', a.taxId ?? '', a.address ?? '', a.city ?? '', countryRef(a.country), a.phone ?? '', a.email ?? '', 1, 0, 'en_US', a.tradeName ? `Trade name: ${a.tradeName}` : '']),
      ...suppliers.map(s => [`itour_supplier_${s.id}`, s.legalName, 'company', s.taxId ?? '', s.address ?? '', s.city ?? '', countryRef(s.country), s.phone ?? '', s.email ?? '', 0, 1, 'en_US', s.tradeName ? `Trade name: ${s.tradeName}` : '']),
    ];
    const ws1 = XLSX.utils.aoa_to_sheet(partnerRows);
    XLSX.utils.book_append_sheet(wb, ws1, 'res.partner');

    // Sheet 2: Customer Invoices
    const invRows: unknown[][] = [
      ['id', 'move_type', 'partner_id/id', 'partner_id/name', 'invoice_date', 'invoice_date_due', 'currency_id/name', 'ref', 'invoice_line_ids/sequence', 'invoice_line_ids/name', 'invoice_line_ids/quantity', 'invoice_line_ids/price_unit', 'invoice_line_ids/tax_ids/amount', 'invoice_line_ids/price_total', 'amount_untaxed', 'amount_tax', 'amount_total', 'state'],
    ];
    for (const inv of invoices) {
      for (let i = 0; i < inv.lines.length; i++) {
        const line = inv.lines[i];
        const isFirst = i === 0;
        invRows.push([
          isFirst ? `itour_inv_${inv.id}` : '',
          'out_invoice',
          inv.agent ? `itour_agent_${inv.agent.id}` : '',
          inv.agent?.legalName ?? '',
          toDate(inv.invoiceDate),
          toDate(inv.dueDate),
          inv.currency,
          inv.invoiceNumber,
          i + 1,
          line.description,
          toNum(line.quantity),
          toNum(line.unitPrice),
          toNum(line.taxRate),
          toNum(line.lineTotal),
          isFirst ? toNum(inv.subtotal) : '',
          isFirst ? toNum(inv.taxAmount) : '',
          isFirst ? toNum(inv.total) : '',
          'posted',
        ]);
      }
    }
    const ws2 = XLSX.utils.aoa_to_sheet(invRows);
    XLSX.utils.book_append_sheet(wb, ws2, 'account.move (invoices)');

    // Sheet 3: Vendor Bills
    const billRows: unknown[][] = [
      ['id', 'move_type', 'partner_id/id', 'partner_id/name', 'invoice_date', 'currency_id/name', 'ref', 'invoice_line_ids/sequence', 'invoice_line_ids/name', 'invoice_line_ids/quantity', 'invoice_line_ids/price_unit', 'invoice_line_ids/tax_ids/amount', 'invoice_line_ids/price_total', 'amount_total', 'state'],
    ];
    for (const cost of costs) {
      billRows.push([
        `itour_bill_${cost.id}`,
        'in_invoice',
        `itour_supplier_${cost.supplierId}`,
        cost.supplier.legalName,
        toDate(cost.createdAt),
        cost.currency,
        cost.trafficJob.internalRef,
        1,
        `Transport service – ${cost.trafficJob.serviceType} – ${toDate(cost.trafficJob.jobDate)}`,
        1,
        toNum(cost.amount),
        0,
        toNum(cost.amount),
        toNum(cost.amount),
        'posted',
      ]);
    }
    const ws3 = XLSX.utils.aoa_to_sheet(billRows);
    XLSX.utils.book_append_sheet(wb, ws3, 'account.move (bills)');

    // Sheet 4: Payments
    const methodMap: Record<string, string> = { CASH: 'cash', BANK_TRANSFER: 'bank', CHECK: 'check' };
    const payRows: unknown[][] = [
      ['id', 'payment_type', 'partner_type', 'partner_id/id', 'partner_id/name', 'date', 'amount', 'currency_id/name', 'journal_id/name', 'ref', 'invoice_ids/id'],
    ];
    for (const p of payments) {
      payRows.push([
        `itour_payment_${p.id}`,
        'inbound',
        'customer',
        p.agentInvoice.agent ? `itour_agent_${p.agentInvoice.agent.id}` : '',
        p.agentInvoice.agent?.legalName ?? '',
        toDate(p.paymentDate),
        toNum(p.amount),
        p.currency,
        methodMap[p.paymentMethod] ?? 'cash',
        p.reference ?? p.agentInvoice.invoiceNumber,
        `itour_inv_${p.agentInvoiceId}`,
      ]);
    }
    const ws4 = XLSX.utils.aoa_to_sheet(payRows);
    XLSX.utils.book_append_sheet(wb, ws4, 'account.payment');

    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
  }
}
