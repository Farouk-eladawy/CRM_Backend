import { Injectable, Logger } from '@nestjs/common';
import type { Prisma } from '../../../generated/prisma/client.js';
import { DriverTariffsService } from '../../driver-tariffs/driver-tariffs.service.js';
import { calcRepScore, scoreToFeeAndEval } from '../utils/rep-score.util.js';

const TERMINAL_PORTAL_STATUSES = ['COMPLETED', 'CANCELLED', 'NO_SHOW'];
// A job already parked in one of these overall states is never auto-flipped to
// COMPLETED — cancelling / no-showing a job is a deliberate dispatch decision.
const TERMINAL_JOB_STATUSES = ['CANCELLED', 'NO_SHOW'];

export interface ReconcileResult {
  completed: boolean;
  statusChanged: boolean;
  driverFeeCreated: boolean;
  repFeeCreated: boolean;
}

const NO_CHANGE: ReconcileResult = {
  completed: false,
  statusChanged: false,
  driverFeeCreated: false,
  repFeeCreated: false,
};

/**
 * Single source of truth for "is this job finished?".
 *
 * `TrafficJob.status` is a stored column, not a derived one, so every write that
 * can move a portal leg to COMPLETED must call this afterwards. Before it
 * existed the roll-up was duplicated inline in the two `/completed` handlers
 * only, which left jobs stranded at ASSIGNED — with both legs COMPLETED and no
 * driver/rep fees — whenever the final COMPLETED write arrived through the
 * generic PATCH status endpoints or admin Force Control.
 *
 * Idempotent by design: safe to call on every write and from the backfill script.
 */
@Injectable()
export class JobCompletionService {
  private readonly logger = new Logger(JobCompletionService.name);

  constructor(private readonly driverTariffsService: DriverTariffsService) {}

  async reconcileJobStatus(
    tx: Prisma.TransactionClient,
    jobId: string,
  ): Promise<ReconcileResult> {
    const job = await tx.trafficJob.findUnique({
      where: { id: jobId },
      include: { assignment: true },
    });

    if (!job || job.deletedAt) return NO_CHANGE;
    if (TERMINAL_JOB_STATUSES.includes(job.status as string)) return NO_CHANGE;

    const assignment = job.assignment;
    if (!assignment) return NO_CHANGE;

    // DEP legs have no rep work once the car has run: completing the driver
    // closes the rep leg too. Kept here (rather than in the driver portal) so
    // every path that completes a DEP driver behaves the same way.
    let repStatus = assignment.repStatus as string;
    if (
      job.serviceType === 'DEP' &&
      assignment.driverId &&
      (assignment.driverStatus as string) === 'COMPLETED' &&
      assignment.repId &&
      !TERMINAL_PORTAL_STATUSES.includes(repStatus)
    ) {
      await tx.trafficAssignment.update({
        where: { id: assignment.id },
        data: { repStatus: 'COMPLETED' as any },
      });
      repStatus = 'COMPLETED';
    }

    // A supplier-sourced car has no own driver (driverId null); its leg is not
    // a gate on job completion, matching the existing rep-portal roll-up.
    const driverAssigned = !!assignment.driverId;
    const repAssigned = !!assignment.repId;
    const driverDone = (assignment.driverStatus as string) === 'COMPLETED';
    const repDone = repStatus === 'COMPLETED';

    const driverLegClear = !driverAssigned || driverDone;
    const repLegClear = !repAssigned || repDone;
    // Guard against completing a job nobody has actually worked yet.
    const anyLegDone = (driverAssigned && driverDone) || (repAssigned && repDone);

    if (!(driverLegClear && repLegClear && anyLegDone)) return NO_CHANGE;

    let statusChanged = false;
    if ((job.status as string) !== 'COMPLETED') {
      await tx.trafficJob.update({
        where: { id: jobId },
        data: { status: 'COMPLETED' as any },
      });
      statusChanged = true;
    }

    const driverFeeCreated = await this.ensureDriverTripFee(tx, job, assignment);
    const repFeeCreated = await this.ensureRepFee(tx, job, assignment);

    return { completed: true, statusChanged, driverFeeCreated, repFeeCreated };
  }

  /** Auto-generate the driver's trip fee from the airport-aware tariff table. */
  private async ensureDriverTripFee(
    tx: Prisma.TransactionClient,
    job: any,
    assignment: any,
  ): Promise<boolean> {
    if (!assignment.driverId) return false;

    const existing = await tx.driverTripFee.findFirst({
      where: { driverId: assignment.driverId, trafficJobId: job.id },
    });
    if (existing) return false;

    const feeData = await this.driverTariffsService.resolveJobTripFee(
      job,
      assignment.vehicleId,
    );
    if (!feeData) return false;

    await tx.driverTripFee.create({
      data: { driverId: assignment.driverId, trafficJobId: job.id, ...feeData },
    });
    return true;
  }

  /** Rep fees exist for ARR jobs only. A scored job uses its score-derived fee. */
  private async ensureRepFee(
    tx: Prisma.TransactionClient,
    job: any,
    assignment: any,
  ): Promise<boolean> {
    if (job.serviceType !== 'ARR' || !assignment.repId) return false;

    const existing = await tx.repFee.findFirst({
      where: { repId: assignment.repId, trafficJobId: job.id },
    });
    if (existing) return false;

    const score = await tx.repJobScore.findUnique({
      where: { trafficJobId: job.id },
    });

    let amount: number;
    if (score) {
      amount = scoreToFeeAndEval(
        calcRepScore({
          attendance: score.attendance,
          appearance: score.appearance,
          work: score.work,
          survey: score.survey,
          review: score.review,
        }),
      ).fee;
    } else {
      const rep = await tx.rep.findUniqueOrThrow({ where: { id: assignment.repId } });
      amount = rep.feePerFlight as any;
    }

    await tx.repFee.create({
      data: {
        repId: assignment.repId,
        trafficJobId: job.id,
        amount,
        currency: 'EGP',
      },
    });
    return true;
  }
}
