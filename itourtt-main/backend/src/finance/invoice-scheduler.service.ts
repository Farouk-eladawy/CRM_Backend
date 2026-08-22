import { Injectable, Logger } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';
import { PrismaService } from '../prisma/prisma.service.js';
import { InvoiceStatus, Currency } from '../../generated/prisma/client.js';

const CAIRO_TZ = 'Africa/Cairo';

/** Returns a Date representing "now" in Cairo local time (for day/month extraction). */
function cairoNow(): Date {
  const now = new Date();
  // Format current time in Cairo timezone then parse it back as a local Date
  const cairoStr = now.toLocaleString('en-CA', { timeZone: CAIRO_TZ, hour12: false });
  // cairoStr looks like "2026-03-06, 14:30:00"
  const normalized = cairoStr.replace(',', '');
  return new Date(normalized);
}

function generateInvoiceNumber(): string {
  const now = cairoNow();
  const yy = String(now.getFullYear()).slice(-2);
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  const seq = Math.floor(Math.random() * 9000) + 1000;
  return `INV-${yy}${mm}${dd}-${seq}`;
}

@Injectable()
export class InvoiceSchedulerService {
  private readonly logger = new Logger(InvoiceSchedulerService.name);

  constructor(private readonly prisma: PrismaService) {}

  /**
   * Runs every day at 01:00 Cairo time.
   * Checks each agent's invoice cycle and auto-generates draft invoices.
   */
  @Cron('0 1 * * *', { timeZone: CAIRO_TZ })
  async runInvoiceCycleJob() {
    this.logger.log('Invoice cycle job started');

    const agents = await this.prisma.agent.findMany({
      where: { deletedAt: null, invoiceCycle: { isNot: null } },
      include: { invoiceCycle: true },
    });

    const today = cairoNow();
    const dayOfWeek = today.getDay(); // 0=Sun ... 6=Sat
    const dayOfMonth = today.getDate();

    let generated = 0;

    for (const agent of agents) {
      const cycle = agent.invoiceCycle;
      if (!cycle) continue;

      const isDue = this.isCycleDueToday(cycle.cycleType, cycle.dayOfWeek, cycle.dayOfMonth, dayOfWeek, dayOfMonth);
      if (!isDue) continue;

      try {
        const count = await this.generateCycleInvoice(agent.id, cycle.cycleType, today);
        if (count > 0) {
          generated++;
          this.logger.log(`Generated cycle invoice for agent ${agent.legalName} (${agent.id}): ${count} line(s)`);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        this.logger.error(`Failed to generate cycle invoice for agent ${agent.id}: ${msg}`);
      }
    }

    this.logger.log(`Invoice cycle job completed. Invoices generated: ${generated}`);
  }

  private isCycleDueToday(
    cycleType: string,
    dayOfWeek: number | null,
    dayOfMonth: number | null,
    todayDow: number,
    todayDom: number,
  ): boolean {
    if (cycleType === 'WEEKLY') {
      return dayOfWeek !== null && dayOfWeek === todayDow;
    }
    if (cycleType === 'BIWEEKLY') {
      // Fire every 2 weeks on the configured day of week
      // Use ISO week number parity (week 1 = odd, week 2 = even)
      const weekNo = this.isoWeekNumber(cairoNow());
      return dayOfWeek !== null && dayOfWeek === todayDow && weekNo % 2 === 0;
    }
    if (cycleType === 'MONTHLY') {
      return dayOfMonth !== null && dayOfMonth === todayDom;
    }
    return false;
  }

  private isoWeekNumber(d: Date): number {
    const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
    const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
    return Math.ceil((((date.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
  }

  private async generateCycleInvoice(agentId: string, cycleType: string, today: Date): Promise<number> {
    // Calculate period start based on cycle type
    const periodEnd = new Date(today);
    periodEnd.setHours(0, 0, 0, 0);

    const periodStart = new Date(periodEnd);
    if (cycleType === 'WEEKLY' || cycleType === 'BIWEEKLY') {
      const days = cycleType === 'BIWEEKLY' ? 14 : 7;
      periodStart.setDate(periodEnd.getDate() - days);
    } else {
      periodStart.setMonth(periodEnd.getMonth() - 1);
    }

    // Get agent details and price items
    const [agent, priceItems] = await Promise.all([
      this.prisma.agent.findUniqueOrThrow({
        where: { id: agentId },
        include: { creditTerms: true },
      }),
      this.prisma.agentPriceItem.findMany({ where: { agentId } }),
    ]);

    if (priceItems.length === 0) {
      this.logger.warn(`Agent ${agentId} has no price list — skipping cycle invoice`);
      return 0;
    }

    const priceMap = new Map<string, number>();
    for (const item of priceItems) {
      const key = `${item.serviceType}-${item.fromZoneId}-${item.toZoneId}-${item.vehicleTypeId}`;
      priceMap.set(key, Number(item.price ?? 0));
    }

    // Get uninvoiced completed jobs in the period
    const jobs = await this.prisma.trafficJob.findMany({
      where: {
        agentId,
        status: 'COMPLETED' as any,
        deletedAt: null,
        jobDate: { gte: periodStart, lt: periodEnd },
        invoiceLines: { none: {} },
      },
      include: {
        fromZone: { select: { name: true } },
        toZone: { select: { name: true } },
        flight: { select: { flightNo: true } },
        assignment: {
          include: { vehicle: { include: { vehicleType: { select: { id: true, name: true } } } } },
        },
      },
      orderBy: { jobDate: 'asc' },
    });

    if (jobs.length === 0) {
      this.logger.log(`Agent ${agentId}: no uninvoiced jobs in period ${periodStart.toISOString()} – ${periodEnd.toISOString()}`);
      return 0;
    }

    // Build invoice lines
    interface Line {
      trafficJobId: string;
      description: string;
      unitPrice: number;
      quantity: number;
      taxRate: number;
      taxAmount: number;
      lineTotal: number;
    }
    const lines: Line[] = [];

    for (const job of jobs) {
      const vehicleTypeId = job.assignment?.vehicle?.vehicleTypeId;
      if (!vehicleTypeId || !job.fromZoneId || !job.toZoneId) continue;

      const key = `${job.serviceType}-${job.fromZoneId}-${job.toZoneId}-${vehicleTypeId}`;
      const unitPrice = priceMap.get(key) ?? 0;
      if (unitPrice <= 0) continue;

      const route = `${job.fromZone?.name ?? '?'} → ${job.toZone?.name ?? '?'}`;
      const ref = job.internalRef ?? job.id;
      const vType = job.assignment?.vehicle?.vehicleType?.name ?? '';
      const desc = `${job.serviceType} ${route} (${vType}) — ${ref}`;

      lines.push({
        trafficJobId: job.id,
        description: desc,
        unitPrice,
        quantity: 1,
        taxRate: 0,
        taxAmount: 0,
        lineTotal: unitPrice,
      });
    }

    if (lines.length === 0) {
      this.logger.log(`Agent ${agentId}: no priceable jobs found in period`);
      return 0;
    }

    const subtotal = lines.reduce((s, l) => s + l.lineTotal, 0);
    const creditDays = agent.creditTerms?.creditDays ?? 30;
    const dueDate = new Date(today.getTime() + creditDays * 86400000);

    let invoiceNo = '';
    for (let i = 0; i < 5; i++) {
      invoiceNo = generateInvoiceNumber();
      const exists = await this.prisma.agentInvoice.findUnique({ where: { invoiceNumber: invoiceNo } });
      if (!exists) break;
    }

    await this.prisma.agentInvoice.create({
      data: {
        agentId,
        invoiceNumber: invoiceNo,
        invoiceDate: today,
        dueDate,
        currency: Currency.EGP,
        exchangeRate: 1,
        subtotal,
        taxAmount: 0,
        total: subtotal,
        status: InvoiceStatus.DRAFT,
        lines: { create: lines },
      },
    });

    return lines.length;
  }
}
