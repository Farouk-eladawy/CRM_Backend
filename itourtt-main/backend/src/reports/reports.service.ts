import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import type { JobStatus, ServiceType } from '../../generated/prisma/client.js';
import { calcRepScore, scoreToFeeAndEval } from '../common/utils/rep-score.util.js';

/** Returns the effective driver name: direct driver → external driver name → supplier name. */
function resolveDriverName(assignment: {
  driver?: { name: string } | null;
  externalDriverName?: string | null;
  supplier?: { tradeName?: string | null; legalName: string } | null;
} | null): string | null {
  if (!assignment) return null;
  if (assignment.driver?.name) return assignment.driver.name;
  if (assignment.externalDriverName) return assignment.externalDriverName;
  if (assignment.supplier) return assignment.supplier.tradeName ?? assignment.supplier.legalName;
  return null;
}

function calcDriverScore(s: {
  attendance: boolean;
  appearance: boolean;
  carCleanliness: boolean;
  maintenance: boolean;
  work: boolean;
}): number {
  return (
    (s.attendance ? 30 : 0) +
    (s.appearance ? 20 : 0) +
    (s.carCleanliness ? 10 : 0) +
    (s.maintenance ? 10 : 0) +
    (s.work ? 30 : 0)
  );
}

function driverScoreToEval(total: number): string {
  if (total >= 90) return 'Excellent';
  if (total >= 70) return 'Good';
  if (total >= 50) return 'Average';
  return 'Poor';
}

/** Returns the fee multiplier for a given driver score total (out of 100). */
function driverScoreToMultiplier(total: number): number {
  if (total >= 90) return 1.0;
  if (total >= 70) return 0.8;
  if (total >= 50) return 0.6;
  return 0.4;
}

@Injectable()
export class ReportsService {
  constructor(private readonly prisma: PrismaService) {}

  // ─────────────────────────────────────────────
  // DAILY DISPATCH SUMMARY
  // ─────────────────────────────────────────────

  async dailyDispatchSummary(date: string) {
    const jobDate = new Date(date);

    const jobs = await this.prisma.trafficJob.findMany({
      where: { jobDate, deletedAt: null },
      select: {
        id: true,
        internalRef: true,
        serviceType: true,
        status: true,
        paxCount: true,
        agent: { select: { legalName: true } },
        customer: { select: { legalName: true } },
        assignment: {
          select: {
            vehicle: { select: { plateNumber: true, vehicleType: { select: { name: true } } } },
            driver: { select: { name: true } },
            rep: { select: { name: true } },
          },
        },
      },
    });

    const totalJobs = jobs.length;
    const byStatus: Record<string, number> = {};
    const byServiceType: Record<string, number> = {};
    let assignedCount = 0;
    let unassignedCount = 0;

    for (const job of jobs) {
      byStatus[job.status] = (byStatus[job.status] || 0) + 1;
      byServiceType[job.serviceType] =
        (byServiceType[job.serviceType] || 0) + 1;
      // Exclude CANCELLED from assignment tracking
      if (job.status !== 'CANCELLED') {
        if (job.assignment) {
          assignedCount++;
        } else {
          unassignedCount++;
        }
      }
    }

    // Active jobs = all non-cancelled jobs (base for rate calculations)
    const activeJobs = totalJobs - (byStatus['CANCELLED'] || 0);

    const completionRate =
      activeJobs > 0
        ? Math.round(((byStatus['COMPLETED'] || 0) / activeJobs) * 100)
        : 0;

    const assignmentRate =
      activeJobs > 0 ? Math.round((assignedCount / activeJobs) * 100) : 0;

    return {
      date,
      totalJobs,
      activeJobs,
      assignedCount,
      unassignedCount,
      completionRate,
      assignmentRate,
      byStatus,
      byServiceType,
      jobs,
    };
  }

  // ─────────────────────────────────────────────
  // DRIVER TRIP REPORT
  // ─────────────────────────────────────────────

  async driverTripReport(from: string, to: string) {
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
            originAirport: true,
            destinationAirport: true,
            agent: true,
            driverJobScore: true,
          },
        },
      },
    });

    // Aggregate by driver
    const driverMap = new Map<
      string,
      {
        driver: { id: string; name: string; mobileNumber: string };
        tripCount: number;
        scoredCount: number;
        totalScore: number;
        trips: Array<{
          jobId: string;
          internalRef: string;
          jobDate: Date;
          serviceType: string;
          status: string;
          paxCount: number;
          route: string;
          agent: string;
          tripFee: number | null;
          tariffFee: number | null;
          driverJobScore: {
            attendance: boolean;
            appearance: boolean;
            carCleanliness: boolean;
            maintenance: boolean;
            work: boolean;
            total: number;
            evaluation: string;
          } | null;
        }>;
      }
    >();

    for (const a of assignments) {
      if (!a.driver) continue;
      const djs = a.trafficJob.driverJobScore;
      const scoreTotal = djs ? calcDriverScore(djs) : null;
      const tripInfo = {
        jobId: a.trafficJobId,
        internalRef: a.trafficJob.internalRef,
        jobDate: a.trafficJob.jobDate,
        serviceType: a.trafficJob.serviceType,
        status: a.trafficJob.status,
        paxCount: a.trafficJob.paxCount,
        route: (() => {
          const from = a.trafficJob.originAirport?.code ?? a.trafficJob.fromZone?.name;
          const to   = a.trafficJob.destinationAirport?.code ?? a.trafficJob.toZone?.name;
          return from && to ? `${from} → ${to}` : '—';
        })(),
        agent: a.trafficJob.agent?.legalName || '—',
        tripFee: null as number | null,
        tariffFee: null as number | null,
        driverJobScore: djs
          ? {
              attendance: djs.attendance,
              appearance: djs.appearance,
              carCleanliness: djs.carCleanliness,
              maintenance: djs.maintenance,
              work: djs.work,
              total: scoreTotal!,
              evaluation: driverScoreToEval(scoreTotal!),
            }
          : null,
      };

      const existing = driverMap.get(a.driverId!);
      if (existing) {
        existing.tripCount++;
        existing.trips.push(tripInfo);
        if (scoreTotal !== null) { existing.scoredCount++; existing.totalScore += scoreTotal; }
      } else {
        driverMap.set(a.driverId!, {
          driver: { id: a.driver.id, name: a.driver.name, mobileNumber: a.driver.mobileNumber },
          tripCount: 1,
          scoredCount: scoreTotal !== null ? 1 : 0,
          totalScore: scoreTotal ?? 0,
          trips: [tripInfo],
        });
      }
    }

    // Also fetch driver fees for the period
    const fees = await this.prisma.driverTripFee.findMany({
      where: {
        trafficJob: {
          jobDate: { gte: fromDate, lte: toDate },
          deletedAt: null,
        },
      },
    });

    const feeByDriver = new Map<string, number>();
    const feeByJob    = new Map<string, { amount: number; tariffAmount: number | null }>();
    for (const fee of fees) {
      const curr = feeByDriver.get(fee.driverId) || 0;
      feeByDriver.set(fee.driverId, curr + Number(fee.amount));
      feeByJob.set(fee.trafficJobId, {
        amount:       Number(fee.amount),
        tariffAmount: fee.tariffAmount != null ? Number(fee.tariffAmount) : null,
      });
    }

    // Attach per-trip fee to each trip
    for (const d of driverMap.values()) {
      for (const trip of d.trips) {
        const f = feeByJob.get(trip.jobId);
        if (f !== undefined) {
          trip.tripFee   = f.amount;
          trip.tariffFee = f.tariffAmount;
        }
      }
    }

    const drivers = Array.from(driverMap.values())
      .map((d) => ({
        ...d,
        totalFees: feeByDriver.get(d.driver.id) || 0,
        avgScore: d.scoredCount > 0 ? Math.round(d.totalScore / d.scoredCount) : null,
        missingScores: d.tripCount - d.scoredCount,
      }))
      .sort((a, b) => b.tripCount - a.tripCount);

    return {
      from,
      to,
      totalDrivers: drivers.length,
      totalTrips: assignments.length,
      drivers,
    };
  }

  // ─────────────────────────────────────────────
  // DRIVER JOB SCORE UPSERT
  // ─────────────────────────────────────────────

  async upsertDriverScore(
    jobId: string,
    scoredById: string,
    data: {
      attendance: boolean;
      appearance: boolean;
      carCleanliness: boolean;
      maintenance: boolean;
      work: boolean;
    },
  ) {
    const assignment = await this.prisma.trafficAssignment.findFirst({
      where: { trafficJobId: jobId, driverId: { not: null } },
    });
    if (!assignment?.driverId) {
      throw new NotFoundException(`No driver assignment found for job ${jobId}`);
    }

    await this.prisma.driverJobScore.upsert({
      where: { trafficJobId: jobId },
      update: { ...data, scoredById },
      create: { trafficJobId: jobId, driverId: assignment.driverId, scoredById, ...data },
    });

    const total = calcDriverScore(data);
    const multiplier = driverScoreToMultiplier(total);

    // Update the trip fee based on the score multiplier
    const existingFee = await this.prisma.driverTripFee.findFirst({
      where: { driverId: assignment.driverId, trafficJobId: jobId },
    });
    if (existingFee) {
      const base = Number(existingFee.tariffAmount ?? existingFee.amount);
      await this.prisma.driverTripFee.update({
        where: { id: existingFee.id },
        data: {
          tariffAmount: existingFee.tariffAmount ?? existingFee.amount,
          amount: Math.round(base * multiplier * 100) / 100,
        },
      });
    }

    return { ok: true, total, evaluation: driverScoreToEval(total) };
  }

  // ─────────────────────────────────────────────
  // AGENT STATEMENT
  // ─────────────────────────────────────────────

  async agentStatement(agentId: string, from: string, to: string) {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const agent = await this.prisma.agent.findUnique({
      where: { id: agentId },
      include: { creditTerms: true },
    });

    if (!agent) {
      return null;
    }

    // Invoices in period
    const invoices = await this.prisma.agentInvoice.findMany({
      where: {
        agentId,
        invoiceDate: { gte: fromDate, lte: toDate },
      },
      include: {
        lines: true,
        payments: true,
      },
      orderBy: { invoiceDate: 'asc' },
    });

    let totalInvoiced = 0;
    let totalPaid = 0;

    const invoiceRows = invoices.map((inv) => {
      const paid = inv.payments.reduce(
        (sum, p) => sum + Number(p.amount),
        0,
      );
      totalInvoiced += Number(inv.total);
      totalPaid += paid;

      return {
        invoiceNumber: inv.invoiceNumber,
        invoiceDate: inv.invoiceDate,
        dueDate: inv.dueDate,
        currency: inv.currency,
        subtotal: Number(inv.subtotal),
        taxAmount: Number(inv.taxAmount),
        total: Number(inv.total),
        paid,
        balance: Number(inv.total) - paid,
        status: inv.status,
        lineCount: inv.lines.length,
      };
    });

    // Jobs in period
    const jobCount = await this.prisma.trafficJob.count({
      where: {
        agentId,
        jobDate: { gte: fromDate, lte: toDate },
        deletedAt: null,
      },
    });

    return {
      agent: {
        id: agent.id,
        legalName: agent.legalName,
        tradeName: agent.tradeName,
        currency: agent.currency,
        creditLimit: agent.creditTerms
          ? Number(agent.creditTerms.creditLimit)
          : null,
        creditDays: agent.creditTerms?.creditDays || null,
      },
      period: { from, to },
      jobCount,
      totalInvoiced,
      totalPaid,
      outstandingBalance: totalInvoiced - totalPaid,
      invoices: invoiceRows,
    };
  }

  // ─────────────────────────────────────────────
  // REP FEE REPORT
  // ─────────────────────────────────────────────

  async repFeeReport(from: string, to: string) {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    // Query assignments where a rep is assigned for jobs within the date range
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
            agent: true,
            repFees: true,
            repJobScore: true,
            guestSurvey: { select: { id: true } },
            inPlaceEvidence: {
              select: { imageUrls: true, gpsMapLink: true, createdAt: true },
            },
          },
        },
      },
    });

    // Aggregate by rep
    const repMap = new Map<
      string,
      {
        repId: string;
        repName: string;
        feePerFlight: number;
        flightCount: number;
        totalAmount: number;
        fees: Array<{
          id: string;
          amount: number;
          status: string;
          trafficJob: (typeof assignments)[number]['trafficJob'];
        }>;
      }
    >();

    for (const a of assignments) {
      if (!a.rep) continue;

      const repId = a.repId!;
      const feePerFlight = Number(a.rep.feePerFlight);

      // For ARR jobs, fee = actual RepFee amount if exists, otherwise rep.feePerFlight
      const isArr = a.trafficJob.serviceType === 'ARR';
      const existingFee = a.trafficJob.repFees.find((f) => f.repId === repId);
      const amount = existingFee
        ? Number(existingFee.amount)
        : isArr
          ? feePerFlight
          : 0;

      const rjs = a.trafficJob.repJobScore;
      const scoreTotal = rjs ? calcRepScore(rjs) : null;
      const feeAndEval = scoreTotal !== null ? scoreToFeeAndEval(scoreTotal) : null;

      const feeEntry = {
        id: existingFee?.id || a.id,
        amount,
        status: a.trafficJob.status,
        isPosted: !!existingFee,
        repStatus: a.repStatus,
        inPlaceEvidence: a.trafficJob.inPlaceEvidence,
        hasSurvey: !!a.trafficJob.guestSurvey,
        repJobScore: rjs
          ? {
              attendance: rjs.attendance,
              appearance: rjs.appearance,
              work: rjs.work,
              survey: rjs.survey,
              review: rjs.review,
              total: scoreTotal,
              fee: feeAndEval?.fee ?? null,
              evaluation: feeAndEval?.evaluation ?? null,
            }
          : null,
        trafficJob: a.trafficJob,
      };

      const existing = repMap.get(repId);
      if (existing) {
        if (isArr) {
          existing.flightCount++;
          existing.totalAmount += amount;
        }
        existing.fees.push(feeEntry);
      } else {
        repMap.set(repId, {
          repId,
          repName: a.rep.name,
          feePerFlight,
          flightCount: isArr ? 1 : 0,
          totalAmount: isArr ? amount : 0,
          fees: [feeEntry],
        });
      }
    }

    const reps = Array.from(repMap.values()).sort((a, b) =>
      a.repName.localeCompare(b.repName),
    );

    const grandTotal = reps.reduce((sum, r) => sum + r.totalAmount, 0);
    const totalFlights = reps.reduce((sum, r) => sum + r.flightCount, 0);

    return {
      from,
      to,
      grandTotal,
      totalFlights,
      reps,
    };
  }

  // ─────────────────────────────────────────────
  // UPSERT REP SCORE
  // ─────────────────────────────────────────────

  async upsertRepScore(
    jobId: string,
    scoredById: string,
    data: {
      attendance: boolean;
      appearance: boolean;
      work: boolean;
      survey: boolean;
      review: boolean;
    },
  ) {
    const assignment = await this.prisma.trafficAssignment.findFirst({
      where: { trafficJobId: jobId, repId: { not: null } },
      include: { trafficJob: { select: { serviceType: true } } },
    });
    if (!assignment?.repId) {
      throw new NotFoundException(`No rep assignment found for job ${jobId}`);
    }

    const repId = assignment.repId;
    const isArr = assignment.trafficJob.serviceType === 'ARR';

    await this.prisma.repJobScore.upsert({
      where: { trafficJobId: jobId },
      update: { ...data, scoredById },
      create: { trafficJobId: jobId, repId, scoredById, ...data },
    });

    if (isArr) {
      const total = calcRepScore(data);
      const { fee } = scoreToFeeAndEval(total);

      const existingFee = await this.prisma.repFee.findFirst({
        where: { trafficJobId: jobId, repId },
      });

      if (existingFee) {
        await this.prisma.repFee.update({
          where: { id: existingFee.id },
          data: { amount: fee },
        });
      } else {
        await this.prisma.repFee.create({
          data: { trafficJobId: jobId, repId, amount: fee, currency: 'EGP' },
        });
      }
    }

    return { ok: true };
  }

  // ─────────────────────────────────────────────
  // REVENUE REPORT
  // ─────────────────────────────────────────────

  async revenueReport(from: string, to: string) {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    // Invoices in period
    const invoices = await this.prisma.agentInvoice.findMany({
      where: {
        invoiceDate: { gte: fromDate, lte: toDate },
        status: { not: 'CANCELLED' as any },
      },
      include: {
        agent: true,
        customer: true,
        lines: {
          include: {
            trafficJob: true,
          },
        },
      },
    });

    let totalRevenue = 0;
    const byAgent = new Map<
      string,
      { name: string; revenue: number; invoiceCount: number; jobCount: number }
    >();
    const byServiceType: Record<string, number> = {};

    for (const inv of invoices) {
      const invTotal = Number(inv.total);
      totalRevenue += invTotal;

      // By agent/customer (partner)
      const partnerId = inv.agentId || inv.customerId || 'unknown';
      const partnerName = inv.agent?.legalName || inv.customer?.legalName || 'Unknown';
      const agentEntry = byAgent.get(partnerId) || {
        name: partnerName,
        revenue: 0,
        invoiceCount: 0,
        jobCount: 0,
      };
      agentEntry.revenue += invTotal;
      agentEntry.invoiceCount++;
      byAgent.set(partnerId, agentEntry);

      // By service type from lines
      for (const line of inv.lines) {
        if (line.trafficJob) {
          const st = line.trafficJob.serviceType;
          byServiceType[st] = (byServiceType[st] || 0) + Number(line.lineTotal);

          const ae = byAgent.get(partnerId)!;
          ae.jobCount++;
        }
      }
    }

    // Costs in period
    const [driverFees, repFees, supplierCosts] = await Promise.all([
      this.prisma.driverTripFee.aggregate({
        where: {
          trafficJob: {
            jobDate: { gte: fromDate, lte: toDate },
            deletedAt: null,
          },
        },
        _sum: { amount: true },
      }),
      this.prisma.repFee.aggregate({
        where: {
          trafficJob: {
            jobDate: { gte: fromDate, lte: toDate },
            deletedAt: null,
          },
        },
        _sum: { amount: true },
      }),
      this.prisma.supplierCost.aggregate({
        where: {
          trafficJob: {
            jobDate: { gte: fromDate, lte: toDate },
            deletedAt: null,
          },
        },
        _sum: { amount: true },
      }),
    ]);

    const totalDriverFees = Number(driverFees._sum.amount || 0);
    const totalRepFees = Number(repFees._sum.amount || 0);
    const totalSupplierCosts = Number(supplierCosts._sum.amount || 0);
    const totalCosts = totalDriverFees + totalRepFees + totalSupplierCosts;

    const agents = Array.from(byAgent.entries())
      .map(([id, data]) => ({ agentId: id, ...data }))
      .sort((a, b) => b.revenue - a.revenue);

    return {
      period: { from, to },
      totalRevenue,
      totalCosts,
      grossProfit: totalRevenue - totalCosts,
      profitMargin:
        totalRevenue > 0
          ? Math.round(((totalRevenue - totalCosts) / totalRevenue) * 100)
          : 0,
      costBreakdown: {
        driverFees: totalDriverFees,
        repFees: totalRepFees,
        supplierCosts: totalSupplierCosts,
      },
      byServiceType,
      byAgent: agents,
    };
  }

  // ─────────────────────────────────────────────
  // REP SCORE REPORT
  // ─────────────────────────────────────────────

  async repScoreReport(from: string, to: string, repId?: string) {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const scores = await this.prisma.repJobScore.findMany({
      where: {
        ...(repId ? { repId } : {}),
        trafficJob: {
          jobDate: { gte: fromDate, lte: toDate },
          deletedAt: null,
        },
      },
      include: {
        rep: { select: { id: true, name: true } },
        trafficJob: {
          include: {
            fromZone: { select: { name: true } },
            toZone: { select: { name: true } },
            originAirport: { select: { name: true, code: true } },
            originZone: { select: { name: true } },
            originHotel: { select: { name: true } },
            destinationAirport: { select: { name: true, code: true } },
            destinationZone: { select: { name: true } },
            destinationHotel: { select: { name: true } },
            flight: { select: { flightNo: true, carrier: true } },
          },
        },
      },
      orderBy: [{ rep: { name: 'asc' } }, { trafficJob: { jobDate: 'asc' } }],
    });

    const rows = scores.map((s) => {
      const total = calcRepScore(s);
      const { fee, evaluation } = scoreToFeeAndEval(total);
      return {
        jobId: s.trafficJobId,
        internalRef: s.trafficJob.internalRef,
        serviceType: s.trafficJob.serviceType,
        paxCount: s.trafficJob.paxCount,
        status: s.trafficJob.status,
        repId: s.repId,
        repName: s.rep.name,
        fromZone: s.trafficJob.fromZone,
        toZone: s.trafficJob.toZone,
        originAirport: s.trafficJob.originAirport,
        originZone: s.trafficJob.originZone,
        originHotel: s.trafficJob.originHotel,
        destinationAirport: s.trafficJob.destinationAirport,
        destinationZone: s.trafficJob.destinationZone,
        destinationHotel: s.trafficJob.destinationHotel,
        flightNo: s.trafficJob.flight?.flightNo ?? null,
        carrier: s.trafficJob.flight?.carrier ?? null,
        attendance: s.attendance,
        appearance: s.appearance,
        work: s.work,
        survey: s.survey,
        review: s.review,
        total,
        fee,
        evaluation,
      };
    });

    const totalScore = rows.reduce((sum, r) => sum + r.total, 0);
    const avgScore = rows.length > 0 ? Math.round((totalScore / rows.length) * 10) / 10 : 0;
    const totalFee = rows.reduce((sum, r) => sum + r.fee, 0);

    return { from, to, rows, totalScore, avgScore, count: rows.length, totalFee };
  }

  // ─────────────────────────────────────────────
  // GUEST SURVEY REPORT
  // ─────────────────────────────────────────────

  async guestSurveyReport(from: string, to: string, repId?: string) {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const surveys = await this.prisma.guestSurvey.findMany({
      where: {
        ...(repId ? { repId } : {}),
        trafficJob: {
          jobDate: { gte: fromDate, lte: toDate },
          deletedAt: null,
        },
      },
      include: {
        rep: { select: { id: true, name: true } },
        trafficJob: {
          select: {
            id: true,
            internalRef: true,
            jobDate: true,
            serviceType: true,
          },
        },
      },
      orderBy: [{ rep: { name: 'asc' } }, { createdAt: 'asc' }],
    });

    const rows = surveys.map((s) => ({
      id: s.id,
      jobId: s.trafficJobId,
      internalRef: s.trafficJob.internalRef,
      jobDate: s.trafficJob.jobDate,
      submittedAt: s.createdAt,
      repId: s.repId,
      repName: s.rep.name,
      ageRange: s.ageRange,
      noOfAdults: s.noOfAdults,
      noOfChildren: s.noOfChildren,
      noOfInfants: s.noOfInfants,
      flightNo: s.flightNo,
      stayLength: s.stayLength,
      jobReference: s.jobReference,
      repeaterGuest: s.repeaterGuest,
      guestNationality: s.guestNationality,
      localTravelAgent: s.localTravelAgent,
      hotelName: s.hotelName,
      email: s.email,
      generalComment: s.generalComment,
      contactNumber: s.contactNumber,
    }));

    // Per-rep summary (count of surveys submitted in range)
    const repMap = new Map<string, { repId: string; repName: string; count: number }>();
    for (const r of rows) {
      const existing = repMap.get(r.repId);
      if (existing) existing.count++;
      else repMap.set(r.repId, { repId: r.repId, repName: r.repName, count: 1 });
    }
    const reps = Array.from(repMap.values()).sort((a, b) =>
      a.repName.localeCompare(b.repName),
    );

    return { from, to, count: rows.length, reps, rows };
  }

  // ─────────────────────────────────────────────
  // DRIVER SCORE REPORT
  // ─────────────────────────────────────────────

  async driverScoreReport(from: string, to: string, driverId?: string) {
    const fromDate = new Date(from);
    const toDate   = new Date(to);

    const scores = await this.prisma.driverJobScore.findMany({
      where: {
        ...(driverId ? { driverId } : {}),
        trafficJob: {
          jobDate: { gte: fromDate, lte: toDate },
          deletedAt: null,
        },
      },
      include: {
        driver: { select: { id: true, name: true } },
        trafficJob: {
          include: {
            fromZone:           { select: { name: true } },
            toZone:             { select: { name: true } },
            originAirport:      { select: { name: true, code: true } },
            destinationAirport: { select: { name: true, code: true } },
          },
        },
      },
      orderBy: [{ trafficJob: { jobDate: 'asc' } }, { driver: { name: 'asc' } }],
    });

    const rows = scores.map((s) => {
      const total      = calcDriverScore(s);
      const multiplier = driverScoreToMultiplier(total);
      const evaluation = driverScoreToEval(total);
      return {
        jobId:       s.trafficJobId,
        internalRef: s.trafficJob.internalRef,
        jobDate:     s.trafficJob.jobDate,
        serviceType: s.trafficJob.serviceType,
        paxCount:    s.trafficJob.paxCount,
        status:      s.trafficJob.status,
        driverId:    s.driverId,
        driverName:  s.driver.name,
        route: (() => {
          const from = s.trafficJob.originAirport?.code ?? s.trafficJob.fromZone?.name;
          const to   = s.trafficJob.destinationAirport?.code ?? s.trafficJob.toZone?.name;
          return from && to ? `${from} → ${to}` : '—';
        })(),
        attendance:    s.attendance,
        appearance:    s.appearance,
        carCleanliness: s.carCleanliness,
        maintenance:   s.maintenance,
        work:          s.work,
        total,
        multiplier,
        feePercent: Math.round(multiplier * 100),
        evaluation,
      };
    });

    const totalScore = rows.reduce((sum, r) => sum + r.total, 0);
    const avgScore   = rows.length > 0 ? Math.round((totalScore / rows.length) * 10) / 10 : 0;

    return { from, to, rows, totalScore, avgScore, count: rows.length };
  }

  // ─────────────────────────────────────────────
  // EVIDENCE REPORT
  // ─────────────────────────────────────────────

  async evidenceReport(from: string, to: string, status?: string, agentId?: string, repId?: string, driverId?: string) {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const where: Record<string, unknown> = {
      jobDate: { gte: fromDate, lte: toDate },
      deletedAt: null,
    };
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
        flight: {
          select: {
            flightNo: true,
            carrier: true,
            terminal: true,
            arrivalTime: true,
            departureTime: true,
          },
        },
        assignment: {
          include: {
            vehicle: { select: { plateNumber: true } },
            driver: { select: { name: true } },
            rep: { select: { name: true } },
            supplier: { select: { legalName: true, tradeName: true } },
          },
        },
        noShowEvidence: {
          select: { id: true, imageUrls: true, gpsMapLink: true, submittedBy: true, createdAt: true },
        },
        inPlaceEvidence: {
          select: { id: true, imageUrls: true, gpsMapLink: true, submittedBy: true, createdAt: true },
        },
        completedEvidence: {
          select: { id: true, imageUrls: true, gpsMapLink: true, submittedBy: true, createdAt: true },
        },
      },
      orderBy: { jobDate: 'asc' },
    });

    const rows = jobs.map((j) => ({
      jobId: j.id,
      internalRef: j.internalRef,
      agentName: j.agent?.legalName ?? null,
      agentRef: j.agentRef ?? null,
      jobDate: j.jobDate,
      serviceType: j.serviceType,
      status: j.status,
      paxCount: j.paxCount,
      clientName: j.clientName ?? null,
      fromZone: j.fromZone,
      toZone: j.toZone,
      originAirport: j.originAirport,
      destinationAirport: j.destinationAirport,
      originHotel: j.originHotel,
      destinationHotel: j.destinationHotel,
      flight: j.flight,
      pickUpTime: j.pickUpTime ?? null,
      driverName: resolveDriverName(j.assignment),
      repName: j.assignment?.rep?.name ?? null,
      assignment: j.assignment
        ? {
            vehicle: j.assignment.vehicle,
            driver: j.assignment.driver,
            rep: j.assignment.rep,
          }
        : null,
      noShowEvidence: j.noShowEvidence,
      inPlaceEvidence: j.inPlaceEvidence,
      completedEvidence: j.completedEvidence,
      hasEvidence:
        j.noShowEvidence.length > 0 ||
        j.inPlaceEvidence.length > 0 ||
        j.completedEvidence.length > 0,
    }));

    return { from, to, totalJobs: rows.length, rows };
  }

  // ─────────────────────────────────────────────
  // JOB STATUS REPORT
  // ─────────────────────────────────────────────

  async jobStatusReport(from: string, to: string, status?: string, repId?: string, repStatus?: string, driverStatus?: string, serviceType?: string) {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const where: Record<string, unknown> = {
      jobDate: { gte: fromDate, lte: toDate },
      deletedAt: null,
    };
    if (status && status !== 'ALL') {
      const statusList = status.split(',').map((s) => s.trim()).filter(Boolean);
      where.status = statusList.length === 1 ? statusList[0] : { in: statusList };
    }
    if (serviceType && serviceType !== 'ALL') {
      where.serviceType = serviceType as ServiceType;
    }

    // Build assignment filter
    const assignmentFilter: Record<string, unknown> = {};
    if (repId && repId !== 'ALL') assignmentFilter.repId = repId;
    if (repStatus && repStatus !== 'ALL') assignmentFilter.repStatus = repStatus;
    if (driverStatus && driverStatus !== 'ALL') assignmentFilter.driverStatus = driverStatus;
    if (Object.keys(assignmentFilter).length > 0) {
      where.assignment = assignmentFilter;
    }

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
        noShowEvidence: {
          select: { id: true, imageUrls: true, gpsMapLink: true, submittedBy: true, createdAt: true },
        },
        inPlaceEvidence: {
          select: { id: true, imageUrls: true, gpsMapLink: true, submittedBy: true, createdAt: true },
        },
        completedEvidence: {
          select: { id: true, imageUrls: true, gpsMapLink: true, submittedBy: true, createdAt: true },
        },
        flight: { select: { arrivalTime: true, flightNo: true } },
      },
      orderBy: { jobDate: 'asc' },
    });

    return {
      from,
      to,
      totalJobs: jobs.length,
      jobs: jobs.map((j) => ({
        id: j.id,
        internalRef: j.internalRef,
        agentRef: j.agentRef,
        agentName: j.agent?.tradeName ?? j.agent?.legalName ?? null,
        serviceDate: j.jobDate,
        serviceType: j.serviceType,
        time: j.serviceType === 'ARR' ? (j.flight?.arrivalTime ?? null) : (j.pickUpTime ?? null),
        flightNo: j.flight?.flightNo ?? null,
        priceAmount: j.priceAmount ? Number(j.priceAmount) : null,
        priceCurrency: j.priceCurrency,
        transferPrice: j.transferPrice ? Number(j.transferPrice) : null,
        transferPriceCurrency: j.transferPriceCurrency ?? null,
        status: j.status,
        repJobStatus: j.assignment?.repStatus || null,
        driverJobStatus: j.assignment?.driverStatus || null,
        repName: j.assignment?.rep?.name ?? null,
        driverName: resolveDriverName(j.assignment ?? null),
        driverEvidence: [
          ...j.noShowEvidence,
          ...j.inPlaceEvidence,
          ...j.completedEvidence,
        ],
      })),
    };
  }

  // ─────────────────────────────────────────────
  // VISA REPORT
  // ─────────────────────────────────────────────

  async visaReport(from: string, to: string) {
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
      clientName: j.clientName ?? '—',
      flightNo: j.flight?.flightNo ?? '—',
      arrivalTime: j.flight?.arrivalTime ?? j.flight?.departureTime ?? null,
      terminal: j.flight?.terminal ?? '—',
    }));

    return { from, to, count: rows.length, rows };
  }

  // ─────────────────────────────────────────────
  // SALES REPORT
  // ─────────────────────────────────────────────

  async salesReport(from: string, to: string) {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const jobs = await this.prisma.trafficJob.findMany({
      where: {
        jobDate: { gte: fromDate, lte: toDate },
        serviceType: 'ARR',
        deletedAt: null,
      },
      include: {
        flight: { select: { flightNo: true, arrivalTime: true, departureTime: true, terminal: true } },
        destinationHotel: { select: { name: true } },
        originHotel: { select: { name: true } },
      },
      orderBy: [{ jobDate: 'asc' }, { internalRef: 'asc' }],
    });

    const rows = jobs.map((j) => ({
      internalRef: j.internalRef,
      agentRef: j.agentRef ?? '—',
      flightNo: j.flight?.flightNo ?? '—',
      terminal: j.flight?.terminal ?? '—',
      arrivalTime: j.flight?.arrivalTime ?? j.flight?.departureTime ?? null,
      pax: j.paxCount,
      hotelName: j.destinationHotel?.name ?? j.originHotel?.name ?? '—',
      clientName: j.clientName ?? '—',
      clientNumber: j.clientMobile ?? '—',
    }));

    return { from, to, count: rows.length, rows };
  }

  // ─────────────────────────────────────────────
  // DEPARTURE REPORT
  // ─────────────────────────────────────────────

  async departureReport(from: string, to: string, serviceType?: string) {
    const fromDate = new Date(from);
    const toDate = new Date(to);

    const where: Record<string, unknown> = {
      jobDate: { gte: fromDate, lte: toDate },
      deletedAt: null,
    };
    if (serviceType && serviceType !== 'ALL') {
      where.serviceType = serviceType as ServiceType;
    }

    const jobs = await this.prisma.trafficJob.findMany({
      where,
      orderBy: [{ jobDate: 'asc' }, { pickUpTime: 'asc' }],
    });

    const rows = jobs.map((j) => ({
      serviceDate: j.jobDate,
      customerName: j.clientName ?? '—',
      customerNumber: j.clientMobile ?? '—',
      pax: j.paxCount,
      pickupTime: j.pickUpTime ?? null,
      serviceType: j.serviceType,
    }));

    return { from, to, count: rows.length, rows };
  }

  async flightDelayReport(from: string, to: string, repName?: string) {
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

    const seen = new Set<string>();
    const rows: Array<{
      internalRef: string;
      agentRef: string | null;
      jobDate: string | null;
      oldArrivalDate: string | null;
      oldArrivalTime: string | null;
      newArrivalDate: string;
      newArrivalTime: string;
      reportedBy: string;
      currentRepName: string | null;
      reportedAt: string;
    }> = [];

    const fmtTime = (d: Date) =>
      d.toLocaleTimeString('en-GB', { timeZone: 'Africa/Cairo', hour: '2-digit', minute: '2-digit', hour12: false });

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
        internalRef: (n.trafficJob as any)?.internalRef ?? '—',
        agentRef: (n.trafficJob as any)?.agentRef ?? null,
        jobDate: (n.trafficJob as any)?.jobDate?.toISOString().split('T')[0] ?? null,
        oldArrivalDate: oldArr ? oldArr.toISOString().split('T')[0] : null,
        oldArrivalTime: oldArr ? fmtTime(oldArr) : null,
        newArrivalDate: newArr.toISOString().split('T')[0],
        newArrivalTime: fmtTime(newArr),
        reportedBy,
        currentRepName: currentRepName && currentRepName !== reportedBy ? currentRepName : null,
        reportedAt: n.createdAt.toISOString(),
      });
    }

    return { from, to, count: rows.length, rows };
  }

  async flightDelayForJob(jobId: string) {
    const notifications = await this.prisma.userNotification.findMany({
      where: { type: 'FLIGHT_DELAY' as any, trafficJobId: jobId },
      include: {
        trafficJob: {
          select: {
            assignment: { select: { rep: { select: { name: true } } } },
          },
        },
      },
      orderBy: { createdAt: 'asc' },
    });

    const seen = new Set<string>();
    const events: Array<{
      oldArrivalDate: string | null;
      oldArrivalTime: string | null;
      newArrivalDate: string;
      newArrivalTime: string;
      reportedBy: string;
      currentRepName: string | null;
      reportedAt: string;
    }> = [];

    const fmtTime = (d: Date) =>
      d.toLocaleTimeString('en-GB', { timeZone: 'Africa/Cairo', hour: '2-digit', minute: '2-digit', hour12: false });

    for (const n of notifications) {
      const meta = n.metadata as { repName?: string; oldArrivalTime?: string | null; newArrivalTime?: string } | null;
      if (!meta?.newArrivalTime) continue;

      if (seen.has(meta.newArrivalTime)) continue;
      seen.add(meta.newArrivalTime);

      const reportedBy = meta.repName ?? '—';
      const currentRepName = (n.trafficJob as any)?.assignment?.rep?.name ?? null;
      const oldArr = meta.oldArrivalTime ? new Date(meta.oldArrivalTime) : null;
      const newArr = new Date(meta.newArrivalTime);

      events.push({
        oldArrivalDate: oldArr ? oldArr.toISOString().split('T')[0] : null,
        oldArrivalTime: oldArr ? fmtTime(oldArr) : null,
        newArrivalDate: newArr.toISOString().split('T')[0],
        newArrivalTime: fmtTime(newArr),
        reportedBy,
        currentRepName: currentRepName && currentRepName !== reportedBy ? currentRepName : null,
        reportedAt: n.createdAt.toISOString(),
      });
    }

    return { jobId, count: events.length, events };
  }

  // ─────────────────────────────────────────────
  // REVIEW REPORT
  // ─────────────────────────────────────────────

  async reviewReport(from: string, to: string, status?: string) {
    const fromDate = new Date(from);
    const toDate = new Date(to);
    toDate.setHours(23, 59, 59, 999);

    const where: Record<string, unknown> = {
      jobDate: { gte: fromDate, lte: toDate },
      deletedAt: null,
    };
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

    const rows = jobs.map((j) => ({
      internalRef: j.internalRef,
      agentName: j.agent?.tradeName ?? j.agent?.legalName ?? '—',
      agentRef: j.agentRef ?? '—',
      serviceDate: j.jobDate,
      serviceType: j.serviceType,
      status: j.status,
      pax: j.paxCount,
      clientName: j.clientName ?? '—',
      origin: j.originHotel?.name ?? j.originZone?.name ?? j.originAirport?.code ?? '—',
      destination: j.destinationHotel?.name ?? j.destinationZone?.name ?? j.destinationAirport?.code ?? '—',
      transferPrice: j.transferPrice ?? null,
      transferPriceCurrency: j.transferPriceCurrency ?? '—',
      driverName: resolveDriverName(j.assignment ?? null) ?? '—',
      repName: j.assignment?.rep?.name ?? '—',
      notes: j.notes ?? '',
    }));

    return { from, to, count: rows.length, rows };
  }
}
