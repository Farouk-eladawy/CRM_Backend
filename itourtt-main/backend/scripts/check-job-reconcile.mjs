// Offline logic check for JobCompletionService.reconcileJobStatus, covering the
// exact status combinations seen in production. Uses an in-memory fake tx — no
// database needed. Run after `npm run build`:  node scripts/check-job-reconcile.mjs
import { JobCompletionService } from '../dist/src/common/services/job-completion.service.js';

const svc = new JobCompletionService({
  resolveJobTripFee: async () => ({ amount: 150, currency: 'EGP', tariffId: null }),
});

function makeTx(job) {
  const writes = [];
  const tx = {
    trafficJob: {
      findUnique: async () => job,
      update: async ({ data }) => {
        writes.push(`job.status=${data.status}`);
        job.status = data.status;
      },
    },
    trafficAssignment: {
      update: async ({ data }) => {
        writes.push(`assignment.repStatus=${data.repStatus}`);
        job.assignment.repStatus = data.repStatus;
      },
    },
    driverTripFee: {
      findFirst: async () => (job._driverFee ? { id: 'f' } : null),
      create: async () => writes.push('driverTripFee'),
    },
    repFee: {
      findFirst: async () => (job._repFee ? { id: 'r' } : null),
      create: async ({ data }) => writes.push(`repFee(${data.amount})`),
    },
    repJobScore: { findUnique: async () => job._score ?? null },
    rep: { findUniqueOrThrow: async () => ({ feePerFlight: 45 }) },
  };
  return { tx, writes };
}

const job = (o) => ({
  id: 'j1',
  deletedAt: null,
  status: 'ASSIGNED',
  serviceType: 'ARR',
  ...o,
  assignment: {
    id: 'a1',
    driverId: 'd1',
    repId: 'r1',
    vehicleId: 'v1',
    driverStatus: 'PENDING',
    repStatus: 'PENDING',
    ...o.assignment,
  },
});

const CASES = [
  ['both legs COMPLETED (ARR)', job({ assignment: { driverStatus: 'COMPLETED', repStatus: 'COMPLETED' } }),
    ['job.status=COMPLETED', 'driverTripFee', 'repFee(45)']],

  ['both legs COMPLETED, job already scored', job({ assignment: { driverStatus: 'COMPLETED', repStatus: 'COMPLETED' }, _score: { attendance: true, appearance: true, work: true, survey: true, review: false } }),
    ['job.status=COMPLETED', 'driverTripFee', 'repFee(30)']],

  ['driver COMPLETED, rep PENDING', job({ assignment: { driverStatus: 'COMPLETED' } }), []],
  ['driver COMPLETED, rep IN_PLACE', job({ assignment: { driverStatus: 'COMPLETED', repStatus: 'IN_PLACE' } }), []],
  ['driver PENDING, rep COMPLETED', job({ assignment: { repStatus: 'COMPLETED' } }), []],
  ['driver CANCELLED, rep COMPLETED', job({ assignment: { driverStatus: 'CANCELLED', repStatus: 'COMPLETED' } }), []],

  ['supplier car (no driverId), rep COMPLETED', job({ assignment: { driverId: null, vehicleId: null, driverStatus: 'COMPLETED', repStatus: 'COMPLETED' } }),
    ['job.status=COMPLETED', 'repFee(45)']],
  ['supplier car (no driverId), rep still PENDING', job({ assignment: { driverId: null, vehicleId: null, driverStatus: 'COMPLETED' } }), []],
  ['supplier car, no rep at all — cron-only signal, left alone', job({ assignment: { driverId: null, repId: null, vehicleId: null, driverStatus: 'COMPLETED' } }), []],

  ['DEP, own driver COMPLETED, rep PENDING → rep auto-closed, no rep fee', job({ serviceType: 'DEP', assignment: { driverStatus: 'COMPLETED' } }),
    ['assignment.repStatus=COMPLETED', 'job.status=COMPLETED', 'driverTripFee']],
  ['DEP, supplier car COMPLETED, rep PENDING → untouched', job({ serviceType: 'DEP', assignment: { driverId: null, vehicleId: null, driverStatus: 'COMPLETED' } }), []],

  ['job CANCELLED is never reopened', job({ status: 'CANCELLED', assignment: { driverStatus: 'COMPLETED', repStatus: 'COMPLETED' } }), []],
  ['job NO_SHOW is never reopened', job({ status: 'NO_SHOW', assignment: { driverStatus: 'COMPLETED', repStatus: 'COMPLETED' } }), []],
  ['soft-deleted job', job({ deletedAt: new Date(), assignment: { driverStatus: 'COMPLETED', repStatus: 'COMPLETED' } }), []],
  ['nothing done yet', job({}), []],

  ['already COMPLETED with fees → idempotent no-op', job({ status: 'COMPLETED', _driverFee: true, _repFee: true, assignment: { driverStatus: 'COMPLETED', repStatus: 'COMPLETED' } }), []],
  ['already COMPLETED missing fees → fees only', job({ status: 'COMPLETED', assignment: { driverStatus: 'COMPLETED', repStatus: 'COMPLETED' } }),
    ['driverTripFee', 'repFee(45)']],
];

let failed = 0;
for (const [name, j, expected] of CASES) {
  const { tx, writes } = makeTx(j);
  await svc.reconcileJobStatus(tx, 'j1');
  const ok = JSON.stringify(writes) === JSON.stringify(expected);
  if (!ok) failed++;
  console.log(`${ok ? '  ok  ' : '  FAIL'} ${name}`);
  if (!ok) console.log(`         expected: ${JSON.stringify(expected)}\n         actual:   ${JSON.stringify(writes)}`);
}

// Idempotency: running twice must not double-write.
const { tx, writes } = makeTx(job({ assignment: { driverStatus: 'COMPLETED', repStatus: 'COMPLETED' } }));
await svc.reconcileJobStatus(tx, 'j1');
const after1 = writes.length;
await svc.reconcileJobStatus(tx, 'j1');
// second pass still creates fees only because the fake findFirst is static; assert no second status write
const statusWrites = writes.filter((w) => w.startsWith('job.status')).length;
if (statusWrites !== 1) { console.log(`  FAIL idempotent status write (${statusWrites})`); failed++; }
else console.log(`  ok   second pass does not rewrite job status (${after1} writes on first pass)`);

console.log(failed ? `\n${failed} FAILURE(S)` : '\nAll reconcile cases pass');
process.exit(failed ? 1 : 0);
