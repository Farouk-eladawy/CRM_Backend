# iTourTT — Pre-Deploy Audit (Phase 1, read-only)

_Read-only assessment. No code was modified. Findings cite file:line evidence, ranked by risk × cost-to-fix._
_Six parallel dimension audits: security · auth/RBAC/session/license · finance/Odoo · dispatch/business-logic · performance/PII · dependencies/correctness._
_**Bugs** and **Business-logic decisions** are kept separate. Business-logic items are flagged "confirm intended" — NOT asserted wrong. No fix is applied until the sliced plan (Phase 3) is approved, and business logic is confirmed with the owner first._

Dependency totals: **backend 45 prod vulns** (1 critical, 21 high); **frontend 8 prod** (5 high).

---

## CRITICAL — fix before deploy

### C-1 · `/uploads/*` served with ZERO auth — legal/ID docs public  [security]
`backend/src/main.ts:24` `express.static` for `/uploads`, exposed via `k8s/ingress.yaml:25-31` + `nginx/nginx.conf:85`. Rep legal docs (`reps.controller.ts:173`), job attachments (`traffic-jobs.controller.ts:156`) written there; `Date.now()`-prefixed names are enumerable. → Anyone can download agent legal/ID docs. **Fix:** authenticated upload controller (ownership check) or signed URLs; drop the raw static mount + public routes.

### C-2 · 2FA fully bypassable — challenge token is a valid bearer token  [auth]  ★ regression in the 2FA just shipped (7feaed1)
`auth.service.ts:114-119` signs the 2FA challenge with the **same `JWT_SECRET`** as access tokens; `jwt.strategy.ts:34-60` never rejects `twoFactorPending`; `permissions.guard.ts` loads perms by userId ignoring the token. → An attacker with the password calls `/auth/login`, then uses `challengeToken` directly as `Authorization: Bearer` and gets full access — TOTP never required. **Fix:** sign the challenge with a distinct secret / `typ:'2fa'` claim and reject it in `JwtStrategy.validate()`.

### C-3 · Pax > vehicle capacity NOT enforced for supplier car-type assignments  [dispatch]
`dispatch.service.ts:164-181` runs the `paxCount > seatCapacity` check only inside the `dto.vehicleId` branch; the supplier-car-type branch (`:230-241`, reassign `:533-541`) does no capacity check although `supplierCarType.vehicleType.seatCapacity` exists. → 12-pax job onto a 4-seat supplier car is accepted, silently breaking the "pax must NEVER exceed capacity" rule. **Fix:** include `vehicleType` and apply the same guard. _(Enforces a documented rule — confirm.)_

### C-4 · Pax edited upward after assignment bypasses capacity  [dispatch]
`traffic-jobs.service.ts:443-445,479` recomputes `paxCount` on update with no re-validation against the assigned vehicle. → assign a 4-seat car to a 4-pax job, then PATCH pax to 10 → invariant violated, no warning. **Fix:** re-check capacity on update when an assignment exists. _(Confirm.)_

### C-5 · Vendor bills & customer payments NEVER export to Odoo  [finance]
Exports filter `isPosted:true` (`odoo-export.service.ts:389,472,569,577`) but no write path ever sets it true (`createPayment` `finance.service.ts:657-664`, `createSupplierCost` `:203-214`; schema default false). → Odoo gets customer invoices but **no AP bills and no payments** → receivables never cleared, books never balance. Defeats the core Odoo requirement. **Fix:** set `isPosted` on finalize (or export by date) + backfill.

### C-6 · protobufjs 7.5.4 — arbitrary code execution (backend prod)  [deps]
Via `firebase-admin → google-gax → @grpc/*`. GHSA-xq3m-2v4x-88gg. **Fix:** `npm audit fix` (bump ≥7.6.3), verify firebase-admin builds. _(Dev-only handlebars RCE via ts-jest is NOT shipped — noted, not deploy-blocking.)_

---

## HIGH — fix before go-live

**Auth/RBAC**
- **H-A1 · `RolesGuard` roleId escape hatch makes `@Roles` a no-op.** `roles.guard.ts:21-23` `if (user?.roleId) return true`. Driver/rep/supplier portal controllers rely on `@Roles` alone with no `PermissionsGuard` (`driver-portal.controller.ts:69`, `rep:108`, `supplier:31`); only saved by service self-scoping (and `getJobStampMeta(jobId)` `driver-portal.controller.ts:156` takes no userId). **Fix:** add `PermissionsGuard`+`@Permissions` to the portals, or don't blanket-return-true.
- **H-A2 · Logout / password-reset does not revoke office-role access tokens.** `sid` is DB-checked only for REP/DRIVER (`jwt.strategy.ts:47-50`); an Admin/Accountant token stays valid ~15m after logout/reset. **Fix:** enforce the `sid` check for all roles (sid already in payload) or a token-version bump.

**Security / secrets**
- **H-S1 · Live Gemini API key in git history + working tree** (`.env:24`, `backend/.env:9`), same key still in use. **Fix:** revoke+rotate, inject via secret, purge history.
- **H-S2 · Placeholder JWT secrets** (`backend/.env:2,4` `...change-in-production`). No code fallback (good), but risk if copied to prod. **Fix:** confirm k8s Secret uses 64-byte random distinct values.
- **H-S3 · Committed default DB password** `docker-compose.yml:10,30` (`:-itour_secure_2026`). **Fix:** remove the default.

**Finance/Odoo** _(integration-strategy sensitive — confirm mapping with the Odoo instance)_
- **H-F1 · Odoo tax mapping wrong; no `account.tax` reference** — raw percent fed to `tax_ids/amount` (`odoo-export.service.ts:180,208,617`), vendor bills hardcode tax 0 (`:424,445`). → VAT mis/under-reported.
- **H-F2 · Multi-currency exchange rate hardcoded `1`** everywhere (`finance.service.ts:391,889,931`; scheduler `:220`; Payment default). → USD/EUR booked 1:1. Violates "exchange rate stored per transaction."
- **H-F3 · Payment currency defaults EGP regardless of invoice currency** (`createPayment` `finance.service.ts:657-664`). → wrong balances/reconciliation. **Fix:** `payment.currency = invoice.currency` + validate in-currency.

**Dispatch**
- **H-D1 · Booking-ref generator collides past 9,999 + races.** Text-sort `ORDER BY internal_ref DESC` (`traffic-jobs.service.ts:797-816`), generated outside the txn (`:290`), `@unique`. At `PREFIX-10000`, `'9' > '1'` → always recomputes 10000 → `P2002` → **all job creation fails** (guaranteed outage). **Fix:** numeric max (`CAST(split_part(...))`) or DB sequence + `P2002` retry inside the txn.
- **H-D2 · `unassignJob` has no terminal-status guard** (`dispatch.service.ts:688-723`) → flips COMPLETED/CANCELLED back to PENDING and orphans `DriverTripFee`/`RepFee`. **Fix:** reject on terminal status (or reverse fees).
- **H-D3 · Driver fee is 0 / skipped on portal completions** — dispatcher path does a tariff lookup (`traffic-jobs.service.ts:645-676`), but the driver/rep portal paths (`driver-portal.service.ts:510-526`, `rep-portal.service.ts:682-698`) write `amount:0`, no lookup, gated on `fromZoneId && toZoneId` (airport legs → no fee). `recalculateDriverFees` skips jobs that already have a fee. → drivers systematically underpaid on the primary channel. **Fix:** call the airport-aware `driverTariffsService.lookup` in the portal paths. _(Touches fee logic — confirm.)_

**Performance / PII**
- **H-P1 · Audit interceptor writes raw PII to an exportable log table.** `audit.interceptor.ts` redacts only 6 keys and snapshots the full pre-update record → agent taxId/address, driver/customer phone/email in plaintext in `activity_logs` (90-day, XLSX-exportable). **Fix:** per-entity allowlist; don't snapshot full records.
- **H-P2 · Reports load entire result sets and aggregate in JS** (`reports.service.ts` many `findMany`, no `take`/`groupBy`). → OOM/latency at volume. **Fix:** SQL `groupBy`/`aggregate`; cap ranges.
- **H-P3 · Missing indexes on finance hot paths** — `JournalLine` has **zero** indexes (not even the FK), `Payment` no `paymentDate`, `AgentInvoice` no `dueDate`. **Fix:** add the indexes (low cost, high payoff).

**Dependencies**
- **H-Dep1 · xlsx (SheetJS) 0.18.5 — proto-pollution + ReDoS, NO npm fix** (frontend + backend). Attacker spreadsheet via job import. **Fix:** SheetJS CDN 0.20.x, or switch backend to `exceljs` (already a dep).
- **H-Dep2 · Next.js 16.1.6 — request smuggling / CSRF bypass / middleware bypass / SSRF.** **Fix:** `next@16.2.10` (minor bump). _Single most important frontend fix._
- **H-Dep3 · axios ≤1.15.2 — auth-bypass + SSRF + proto-pollution** (both apps). **Fix:** bump ≥1.16.
- **H-Dep4 · NestJS core/platform-express ≤11.1.17 injection + multer DoS + form-data CRLF + grpc-js crash** (firebase chain). All non-breaking. **Fix:** `npm audit fix`.
- **H-Dep5 · nodemailer 8.0.1** — fix needs major 8→9. **Fix:** bump + email smoke test.

---

## MEDIUM

- **M-1 · Permission cache never invalidated** — `permissions.guard.ts:16` 5-min TTL, `invalidateCache()` has zero callers → up to 5-min privilege lag after role/permission change. **Fix:** call it on role/permission mutations.
- **M-2 · `activate-license` has no role guard** — `settings.controller.ts:140-142` only `JwtAuthGuard`; any authenticated user (DRIVER/B2C) can overwrite the company license key. **Fix:** `@Roles('ADMIN')` + `@Permissions('company.editSettings')` on the 3 license routes.
- **M-3 · Dispatch field-perm gap in `reassignJob`** — `supplierCarTypeId` / `externalDriverName/Phone` written without the permission checks `assignJob` applies (`dispatch.service.ts:433-446,547-551,584-585`). **Fix:** mirror `assignJob` gating.
- **M-4 · Duplicate fees under concurrency + path divergence** — no `@@unique(driverId,trafficJobId)`/`(repId,trafficJobId)`; `findFirst` in Read-Committed races; `forceControl`→COMPLETED creates no fees, `unassign` doesn't remove them. **Fix:** `@@unique` + `upsert`; centralize fee creation; reverse on de-complete.
- **M-5 · `getAvailableReps` dead `blocked` var** (`dispatch.service.ts:915-937`) → returns all reps ignoring conflicts, contradicting `validateRepAvailability` (assign 409s). **Fix:** mirror the validation in the availability list.
- **M-6 · Assign/invoice/booking check-then-create races surface as 500** not 409/retry (`dispatch.service.ts:157,257`; invoice `finance.service.ts:292-298,364-371`; booking-ref H-D1). Same `P2002`-catch pattern fixes all.
- **M-7 · Customer-invoice generation not atomic** — transfer + driver-tip invoices are separate creates, no shared txn (`finance.service.ts:877,919`). **Fix:** wrap in `$transaction`.
- **M-8 · No CSP; app-layer helmet absent** (`main.ts`); ingress sets HSTS/nosniff but no CSP. **Fix:** add CSP at Traefik+nginx (+ helmet defense-in-depth).
- **M-9 · CORS reflects any `http://localhost` origin with credentials in prod** (`main.ts:32,41`). **Fix:** gate behind `NODE_ENV!=='production'`.
- **M-10 · Refresh token in JSON body, not httpOnly cookie** (`auth-response.dto.ts:17`). Hashed at rest (good). **Fix:** httpOnly/Secure/SameSite cookie.
- **M-11 · Exception filter leaks Prisma internals** for unmapped errors (`http-exception.filter.ts:45-47`). **Fix:** generic message in prod.
- **M-12 · Public booking endpoints over-return** full `GuestBooking` incl. `paymentReference`, `b2cClientId`, and `accountPassword` in plaintext on create (`public-api.service.ts:1007-1015,1059`). **Fix:** explicit guest-facing `select`; drop password/internal fields.
- **M-13 · `api.ts` SESSION_DISPLACED branch unreachable** (`frontend/src/lib/api.ts:45,93-105`) — generic 401 handler consumes it first; "displaced" reason never shown. **Fix:** move the check above the refresh block.
- **M-14 · Odoo `account.move` forced `state='posted'` via dead ternary** + supplies computed totals (`odoo-export.service.ts:214`). **Fix:** import draft→post or drop computed columns; remove dead ternary. _(Confirm import strategy.)_
- **M-15 · No row-level createdBy/postedBy on financial tables** (schema). userId available but not persisted. **Fix:** add + populate. _(Confirm audit.interceptor coverage.)_
- **M-16 · Enum status writes cast `as any`** (`driver-portal.service.ts`, 180 total) — a typo'd status compiles clean. **Fix:** cast to the Prisma enum type.
- **M-17 · Partner `/reference` returns the whole location tree per poll, no cache**; hotels auto-created unboundedly (`partner.service.ts:33-106`; `public-api.service.ts:319`). Has a `version` it never uses. **Fix:** honor `version` (304/empty) or cache+invalidate.

---

## LOW

- **L-1 · No structured logging / error monitoring** (no Sentry/pino) — 401/403/500 only to stdout.
- **L-2 · `deploy.sh:67` runs `prisma db push --accept-data-loss` against prod** every deploy. **Fix:** drop it; use `migrate deploy` only.
- **L-3 · B2C client password = phone number** + 30-day token on shared secret (`b2c.service.ts:49,55-59,68,71-73`). _(B2C being split out.)_
- **L-4 · TOTP replay within its ~30-60s window** — codes not single-use (recovery codes are). **Fix:** track last-consumed counter.
- **L-5 · Partner-key length short-circuit leaks key length**; broad blast radius (bulk pricing overwrite, job create), one static key, no throttle.
- **L-6 · Bulk Odoo/XLSX exports load all rows, no streaming**; **money as JS float** (mitigated by `Decimal(15,2)`); **PII emails/phones logged at INFO**; **traffic-jobs default sort on un-indexed `createdAt`**; **bulk import per-row create** (bounded 500).

---

## BUSINESS-LOGIC — CONFIRM INTENDED (owner decision, not asserted wrong)

**Dispatch**
- **B-1 · Vehicle & driver double-booking is intentionally NOT enforced** (`validateVehicle/DriverAvailability` are no-ops `dispatch.service.ts:1036-1054`; `getAvailableDrivers` returns all). Only reps get conflict validation. Contradicts the "real-time conflict validation" line in CLAUDE.md/04-dispatch-ui. **Confirm:** should vehicle/driver overlap at least warn?
- **B-2 · Assignment order Vehicle→Driver→Rep is not enforced** (`assignJob` accepts `repId` alone; dedicated FE rep-only path). The permission split (Online Operator = assignRep only) implies independent rep assignment is intended. **Confirm** which rule governs.
- **B-3 · Rep fee is ARR-only; DEP reps are auto-completed but never paid** (`traffic-jobs.service.ts:682-684` + portals). Consistent everywhere → reads deliberate. **Confirm.**
- **B-4 · Flat rep fee / zero-default driver tariffs** (already listed deferred in project memory). **Confirm still intended.** _(Separate from H-D3, which is a channel-inconsistency bug.)_

**Finance**
- **B-5 · Immutability is app-layer only** — no delete endpoints; edits gated to DRAFT; status only DRAFT→POSTED/CANCELLED. **No DB constraint**, so a raw SQL write bypasses it. **Confirm** app-level enforcement is sufficient for "immutable after posting."
- **B-6 · Credit-limit check** counts DRAFT+POSTED at full total, does not subtract payments received, and runs outside the create txn (TOCTOU) (`finance.service.ts:234-243`). **Confirm** the intended definition of "outstanding."
- **B-7 · Transfer / driver-tip / cycle invoices are always tax-free**; only agent invoices carry tax (`finance.service.ts:887-899,929-941`; scheduler). **Confirm.**
- **B-8 · Soft-deleted B2C invoices drop from the Odoo export** (`odoo-export.service.ts:252`). No code sets `deletedAt` today. **Confirm** posted B2C invoices should never be soft-deletable.

---

## Notes — verified GOOD (not issues)
Global `JwtAuthGuard` deny-by-default; refresh tokens hashed+compared; REP/DRIVER session displacement works; Stripe/GetPayIn webhooks signature-verified; `assignJob` field-perms correct; partner-key guard timing-safe + fail-closed; Ed25519 license verify sound (signature-first, clamps attacker input); `users.service` `SAFE_USER_OMIT` everywhere; portals scoped selects; N+1 largely absent; token keys consistent (no mismatch bug); no TODO/debugger/empty-catch/orphan/no-op-handler in src; Egypt/Dubai bank gateways return a clean 501 and aren't exposed in the UI.
