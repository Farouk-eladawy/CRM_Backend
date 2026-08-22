# iTour Performance Audit — 2026-04-19

## Status
- [x] Phase 1 — **COMPLETED** (2026-04-19, deployed to production)
- [x] Phase 2 — **COMPLETED** (2026-04-19, deployed to production)
- [ ] Phase 3 — Pending

---

## DATABASE AUDIT FINDINGS

### CRITICAL

#### 1. N+1 in invoice generation
- **File:** `backend/src/finance/finance.service.ts:816`
- **Problem:** Individual `trafficJob.update()` inside a for-loop over jobs. 100 jobs = 100 round trips.
- **Fix:** Collect updates, run `Promise.all()` or `this.prisma.$transaction([...updates])` after loop.

#### 2. Missing FK indexes on ~15 tables
- **File:** `backend/prisma/schema.prisma`
- **Tables affected:** `traffic_assignments`, `rep_fees`, `driver_trip_fees`, `supplier_costs`, `driver_vehicles`, `vehicles`, `drivers`, `airports`, `cities`, `zones`, `hotels`, `invoice_lines`, `payments`, `driver_price_tariffs`
- **Problem:** Prisma does NOT auto-create FK indexes → full table scans on joins.
- **Fix:** Add `@@index` for every FK column (see Phase 1a below).

#### 3. Export service full table scans
- **File:** `backend/src/export/export.service.ts:98–342`
- **Methods:** `exportCustomers`, `exportSuppliers`, `exportInvoices`, `exportVendorBills`, `exportPayments`, `exportJournalEntries`, `exportCollections`
- **Problem:** No date filter, no limit — scans entire tables.
- **Fix:** Add date range params + `take: 50000`.

---

### HIGH

#### 4. Connection pool at default (10 connections)
- **File:** `backend/src/prisma/prisma.service.ts:12`
- **Fix:** `max: 20, min: 5, idleTimeoutMillis: 30000, connectionTimeoutMillis: 5000`

#### 5. Unbounded findMany on list endpoints
- **Files:** Multiple services
- **Fix:** Add `take/skip`, enforce max limit of 500.

#### 6. Missing indexes on TrafficJob filter columns
- **Columns:** `serviceType`, `fromZoneId`, `toZoneId`, `requestedVehicleTypeId`, `deletedAt`, `createdAt`
- **Fix:** Add `@@index` + composite `[jobDate, status]`, `[jobDate, deletedAt]`.

---

### MEDIUM

#### 7. Deep 4-level nested includes in portal services
- **Files:** `driver-portal.service.ts:36`, `rep-portal.service.ts:32`
- **Fix:** Split into summary vs detail includes.

#### 8. Composite indexes missing for compound WHERE clauses
- **Fix:** `@@index([repId, trafficJobId])`, `@@index([driverId, trafficJobId])` on `traffic_assignments`.

#### 9. Unbounded growth of activity_logs + whatsapp_notification_logs
- **Fix:** Add `@@index([createdAt])`, add weekly cleanup cron.

---

## SYSTEM PERFORMANCE AUDIT FINDINGS

### CRITICAL

#### 1. Massive over-fetching in traffic-jobs list queries
- **File:** `backend/src/traffic-jobs/traffic-jobs.service.ts:42`
- **Problem:** `jobInclude` loads 12+ full related objects on every list call. Responses can be 20–50 MB.
- **Fix:** Create `jobSelectLight` with only needed fields for `findAll()`. Keep full include for `findOne()`.

#### 2. Dispatch day view — no pagination, full includes
- **File:** `backend/src/dispatch/dispatch.service.ts:68`
- **Problem:** Fetches ALL jobs for a date with massive include tree.
- **Fix:** Add `take/skip`, use slim include with selected fields only.

#### 3. Every-minute cron with N+1 (supplier auto-complete)
- **File:** `backend/src/driver-portal/supplier-auto-complete.service.ts:14`
- **Problem:** `@Cron('* * * * *')` = 1,440 runs/day. Loops assignments with individual DB writes per item.
- **Fix:** Change to `@Cron('0 * * * *')`. Use `updateMany`/`createMany(skipDuplicates: true)`.

#### 4. Every-minute WhatsApp cron
- **File:** `backend/src/whatsapp-notifications/whatsapp-notifications.service.ts:208`
- **Problem:** `@Cron(CronExpression.EVERY_MINUTE)` = 1,440 runs/day. Full job includes per run.
- **Fix:** Change to `@Cron('0 */6 * * *')`. Select only needed fields. Skip already-sent jobs.

---

### HIGH

#### 5. No gzip/brotli compression on API responses
- **File:** `backend/src/main.ts`
- **Fix:** `npm i compression && npm i -D @types/compression` → `app.use(compression())`.

#### 6. Unbatched audit log writes
- **File:** `backend/src/common/interceptors/audit.interceptor.ts:73`
- **Problem:** One INSERT per API write. No cleanup.
- **Fix:** Queue + flush every 5s with `createMany`. Add 90-day cleanup cron.

#### 7. Dispatch page loads ALL vehicles/drivers/reps
- **File:** `frontend/src/app/(dashboard)/dashboard/dispatch/page.tsx:1729`
- **Fix:** Server-side search autocomplete. Paginate dropdown sources.

#### 8. Permission DB lookup on every dispatch action — not cached
- **File:** `backend/src/dispatch/dispatch.controller.ts:45`
- **Fix:** In-memory cache with 5-min TTL.

#### 9. Activity logs unbounded growth
- **Fix:** Weekly cron `deleteMany({ where: { createdAt: { lt: 90daysAgo } } })`.

---

### MEDIUM

#### 10. `deletedAt` used in every query but has no index
- **Fix:** `@@index([deletedAt])`, `@@index([jobDate, deletedAt])` on `traffic_jobs`.

#### 11. Unused Tiptap rich-text editor bundle (~100 KB)
- **File:** `frontend/package.json:28–36`
- **Fix:** `npm uninstall @tiptap/react @tiptap/starter-kit @tiptap/extension-*`

#### 12. Export endpoints load full dataset into memory
- **Fix:** Stream exports in batches of 1,000.

#### 13. No rate limiting on public API
- **Fix:** Apply `@Throttle()` decorator — package already installed.

---

## PHASED IMPLEMENTATION PLAN

### Phase 1 — CRITICAL + quick wins (target: same session)

| # | Task | File | Status |
|---|------|------|--------|
| 1a | Add missing indexes to schema.prisma | `prisma/schema.prisma` | ✅ Done — 42 indexes applied directly to production DB via psql |
| 1b | Add gzip compression middleware | `main.ts` | ✅ Done — `compression` package installed, added before all middleware |
| 1c | Fix cron jobs (interval + batch ops) | `supplier-auto-complete.service.ts`, `whatsapp-notifications.service.ts` | ✅ Done — supplier auto-complete: 1m→5m; WhatsApp JOB_INCLUDE changed to select |
| 1d | Configure Prisma connection pool | `prisma.service.ts` | ✅ Done — max:20, min:5, idle:30s, timeout:5s |
| 1e | Lightweight select for list queries | `traffic-jobs.service.ts`, `dispatch.service.ts` | ✅ Done — `jobSelectLight` for findAll(); slim include for dispatch day view |
| 1f | Apply indexes to production DB | CLI + psql | ✅ Done — 42 indexes created; `migrate diff` confirmed zero drift |

> **Note on WhatsApp cron:** frequency kept at every-minute (by design — must fire at exact sendHour:sendMinute). Optimized the JOB_INCLUDE from full object loads to targeted selects instead.
> **Note on supplier auto-complete:** changed from every-minute to every-5-minutes (not hourly) to avoid extending auto-complete delay from 80min max to 140min max.

### Phase 2 — HIGH priority (next session)

| # | Task | File |
|---|------|------|
| 2a | Fix N+1 in invoice generation — batch updates | `finance.service.ts` | ✅ Done — `pendingPriceUpdates[]` collected in loop, flushed via `$transaction([...])` after |
| 2b | Batch audit log writes with queue + flush | `audit.interceptor.ts` | ✅ Done — in-memory queue, flush every 5s or every 200 items via `createMany` |
| 2c | Add date range filters to all export methods | `export.service.ts` + `export.controller.ts` | ✅ Done — `dateFrom`/`dateTo` query params on invoices, vendor-bills, payments, journals; `take:50_000` cap |
| 2d | Cache permission lookups | `permissions.guard.ts` | ✅ Done — cache already existed; extended TTL from 60s → 5 min |
| 2e | Add 90-day activity log cleanup cron | `activity-logs.service.ts` | ✅ Done — `@Cron('0 3 * * 0')` every Sunday 03:00 Cairo, `deleteMany({ createdAt: { lt: cutoff } })` |

### Phase 3 — MEDIUM/LOW (future session)

| # | Task | File |
|---|------|------|
| 3a | Server-side search for dispatch dropdowns | `dispatch/page.tsx` + backend endpoint |
| 3b | Remove unused Tiptap dependency | `frontend/package.json` |
| 3c | Add Prisma slow query logging (>1000ms) | `prisma.service.ts` |
| 3d | Apply `@Throttle()` to public API controller | `public-api/` |
| 3e | Stream large exports in 1k-row batches | `export.service.ts` |
| 3f | Split portal includes into summary vs detail | `driver-portal.service.ts`, `rep-portal.service.ts` |

---

## Expected Performance Gains (after all phases)

| Area | Expected Improvement |
|------|---------------------|
| Driver/Rep portals | 60–80% faster |
| Dispatch day view | 50–60% faster |
| Invoice generation | 90%+ faster |
| Export operations | 70–80% faster |
| Connection stability | Eliminates "too many connections" |
| API response size | 80% smaller (compression) |
| Background DB pressure | ~95% reduction (cron fixes) |
