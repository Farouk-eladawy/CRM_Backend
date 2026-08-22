/**
 * One-time backfill: close jobs whose driver and rep legs are both COMPLETED
 * but whose overall `TrafficJob.status` was never rolled up.
 *
 * `TrafficJob.status` is a stored column. Until JobCompletionService landed, the
 * roll-up lived inline in the two `/completed` portal handlers only — so a job
 * whose final COMPLETED write arrived through `PATCH /{driver,rep}-portal/jobs/
 * :id/status` or admin Force Control stayed stranded at ASSIGNED, and never got
 * its DriverTripFee / RepFee either.
 *
 * This runs the *same* JobCompletionService.reconcileJobStatus() the live code
 * now calls, so there is no second copy of the rules to drift. It is idempotent:
 * jobs already consistent are read and skipped.
 *
 * Candidates = non-deleted jobs that are not CANCELLED/NO_SHOW/COMPLETED, have
 * an assignment, and have at least one leg at COMPLETED.
 *
 * `--include-completed` widens the sweep to jobs that are ALREADY COMPLETED but
 * are missing a driver / rep fee. That is deliberately opt-in: it is a financial
 * write against historical, possibly already-settled periods, not a status fix.
 *
 * Run from /app inside the backend container:
 *   node scripts/backfill-stuck-job-status.mjs          # dry run (default)
 *   node scripts/backfill-stuck-job-status.mjs --apply  # write changes
 *   node scripts/backfill-stuck-job-status.mjs --include-completed  # + fee gap
 */

import { PrismaClient } from '/app/dist/generated/prisma/client.js';
import { PrismaPg } from '@prisma/adapter-pg';
import pg from 'pg';
import { DriverTariffsService } from '/app/dist/src/driver-tariffs/driver-tariffs.service.js';
import { JobCompletionService } from '/app/dist/src/common/services/job-completion.service.js';

const APPLY = process.argv.includes('--apply');
const INCLUDE_COMPLETED = process.argv.includes('--include-completed');

// Never re-open a job that dispatch deliberately parked in a terminal state.
const SKIP_STATUSES = INCLUDE_COMPLETED
  ? ['CANCELLED', 'NO_SHOW']
  : ['CANCELLED', 'NO_SHOW', 'COMPLETED'];

const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });
const adapter = new PrismaPg(pool);
const prisma = new PrismaClient({ adapter });

// The services are plain classes — Nest DI is not needed to construct them.
const jobCompletion = new JobCompletionService(new DriverTariffsService(prisma));

async function main() {
  console.log(APPLY ? '── APPLY mode: writing changes ──' : '── DRY RUN (pass --apply to write) ──');
  console.log(
    INCLUDE_COMPLETED
      ? '── Scope: stuck statuses + missing fees on already-COMPLETED jobs ──\n'
      : '── Scope: stuck job statuses only (pass --include-completed for the historical fee gap) ──\n',
  );

  const candidates = await prisma.trafficJob.findMany({
    where: {
      deletedAt: null,
      status: { notIn: SKIP_STATUSES },
      assignment: {
        is: {
          OR: [{ driverStatus: 'COMPLETED' }, { repStatus: 'COMPLETED' }],
        },
      },
    },
    select: {
      id: true,
      internalRef: true,
      jobDate: true,
      status: true,
      serviceType: true,
      assignment: {
        select: { driverId: true, repId: true, driverStatus: true, repStatus: true },
      },
    },
    orderBy: { jobDate: 'asc' },
  });

  console.log(`Scanning ${candidates.length} candidate job(s)…\n`);

  const changed = [];
  let statusFixed = 0;
  let driverFees = 0;
  let repFees = 0;
  let failed = 0;

  for (const job of candidates) {
    const a = job.assignment;
    const before = `job=${job.status} driver=${a.driverStatus} rep=${a.repStatus}`;

    try {
      // A dry run still needs the real decision, so reconcile inside a
      // transaction that is always rolled back unless --apply was passed.
      const result = await prisma.$transaction(async (tx) => {
        const r = await jobCompletion.reconcileJobStatus(tx, job.id);
        if (!APPLY) throw new DryRunRollback(r);
        return r;
      });
      record(result);
    } catch (err) {
      if (err instanceof DryRunRollback) {
        record(err.result);
      } else {
        failed++;
        console.error(`  ✗ ${job.internalRef}: ${err?.message ?? err}`);
      }
    }

    function record(r) {
      if (!r.statusChanged && !r.driverFeeCreated && !r.repFeeCreated) return;
      if (r.statusChanged) statusFixed++;
      if (r.driverFeeCreated) driverFees++;
      if (r.repFeeCreated) repFees++;
      const fixes = [
        r.statusChanged ? `status ${job.status} → COMPLETED` : null,
        r.driverFeeCreated ? 'driver trip fee created' : null,
        r.repFeeCreated ? 'rep fee created' : null,
      ].filter(Boolean);
      changed.push(job.internalRef);
      console.log(
        `  ${job.internalRef} (${job.jobDate.toISOString().slice(0, 10)}, ${job.serviceType})` +
          `\n      was: ${before}\n      fix: ${fixes.join(' · ')}`,
      );
    }
  }

  console.log('\n── Summary ──');
  console.log(`  candidates scanned : ${candidates.length}`);
  console.log(`  jobs changed       : ${changed.length}`);
  console.log(`  job status fixed   : ${statusFixed}`);
  console.log(`  driver fees created: ${driverFees}`);
  console.log(`  rep fees created   : ${repFees}`);
  if (failed) console.log(`  FAILED             : ${failed}`);
  if (!APPLY && changed.length) console.log('\n  Nothing was written. Re-run with --apply.');
}

class DryRunRollback extends Error {
  constructor(result) {
    super('dry-run rollback');
    this.result = result;
  }
}

main()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
    await pool.end();
  });
