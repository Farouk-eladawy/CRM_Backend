/**
 * One-time backfill: clean stray flight times that don't match the job's
 * service type.
 *
 *   - DEP jobs keep `departureTime`; any `arrivalTime` is cleared.
 *   - ARR jobs keep `arrivalTime`;   any `departureTime` is cleared.
 *
 * Non-airport service types (DAY_TOUR, ONE_WAY_TRANSFER, TWO_WAY_TRANSFER,
 * CITY_TO_CITY) rarely carry a flight; they're left untouched.
 *
 * The display layer already picks the field by service type (commit 0a3d59e
 * + the dispatch detail modal). This script makes the stored data match so the
 * stray value can never resurface.
 *
 * Run from /app inside the backend container:
 *   node scripts/backfill-flight-times.mjs          # dry run (default)
 *   node scripts/backfill-flight-times.mjs --apply  # write changes
 */

import { PrismaClient } from '/app/dist/generated/prisma/client.js';
import { PrismaPg } from '@prisma/adapter-pg';
import pg from 'pg';

const APPLY = process.argv.includes('--apply');

const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });
const adapter = new PrismaPg(pool);
const prisma = new PrismaClient({ adapter });

async function main() {
  console.log(APPLY ? '── APPLY mode: writing changes ──' : '── DRY RUN (pass --apply to write) ──');

  // DEP jobs with a stray arrival time.
  const depStray = await prisma.trafficFlight.findMany({
    where: {
      arrivalTime: { not: null },
      trafficJob: { serviceType: 'DEP', deletedAt: null },
    },
    select: {
      id: true,
      arrivalTime: true,
      departureTime: true,
      trafficJob: { select: { internalRef: true } },
    },
  });

  // ARR jobs with a stray departure time.
  const arrStray = await prisma.trafficFlight.findMany({
    where: {
      departureTime: { not: null },
      trafficJob: { serviceType: 'ARR', deletedAt: null },
    },
    select: {
      id: true,
      arrivalTime: true,
      departureTime: true,
      trafficJob: { select: { internalRef: true } },
    },
  });

  console.log(`\nDEP jobs carrying a stray arrivalTime:   ${depStray.length}`);
  for (const f of depStray) {
    console.log(
      `  ${f.trafficJob.internalRef}: arrivalTime=${f.arrivalTime?.toISOString() ?? '—'} ` +
        `(kept departureTime=${f.departureTime?.toISOString() ?? 'null'})`,
    );
  }

  console.log(`\nARR jobs carrying a stray departureTime: ${arrStray.length}`);
  for (const f of arrStray) {
    console.log(
      `  ${f.trafficJob.internalRef}: departureTime=${f.departureTime?.toISOString() ?? '—'} ` +
        `(kept arrivalTime=${f.arrivalTime?.toISOString() ?? 'null'})`,
    );
  }

  if (!APPLY) {
    console.log('\nDry run complete — no changes written. Re-run with --apply to clean.');
    return;
  }

  let cleared = 0;
  if (depStray.length) {
    const r = await prisma.trafficFlight.updateMany({
      where: { id: { in: depStray.map((f) => f.id) } },
      data: { arrivalTime: null },
    });
    cleared += r.count;
  }
  if (arrStray.length) {
    const r = await prisma.trafficFlight.updateMany({
      where: { id: { in: arrStray.map((f) => f.id) } },
      data: { departureTime: null },
    });
    cleared += r.count;
  }

  console.log(`\n✓ Cleared stray times on ${cleared} flight record(s).`);
}

main()
  .catch((e) => {
    console.error('Fatal:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
    await pool.end();
  });
