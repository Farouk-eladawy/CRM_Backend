# Deploy Runbook — Topic 2 (iTourTT) + B2C standalone

**Window:** tonight 00:00 Africa/Cairo, after last live job on prod completes.
**Scope:** ship `feat/b2c-partner-seam` (iTourTT) + `feat/standalone-backend` (B2C) together.
**Status:** PLAN ONLY. Nothing here runs until you say go.

---

## 0. Why this order (non-negotiable)

iTourTT **first**, B2C **second**, same window. Reasons:

- B2C backend `partner-client` pushes pricing/jobs → iTourTT `/api/partner/*`. That seam is **not on iTourTT `main`/live yet** → B2C pushes 404 until iTourTT ships it. iTourTT must go first.
- This iTourTT release **removes** the old embedded website API (`/api/public/*`, `/api/w-api/*`). The **currently-live** B2C container calls exactly those on `fulvago.itourtt.cloud`. The moment iTourTT deploys, the live B2C site breaks — **unless** B2C is simultaneously flipped to its own standalone backend (which now serves `/api/public/*` itself). So B2C must cut over in the same window, right after iTourTT.

Net: iTourTT deploy → verify seam up → B2C cut to standalone → verify end-to-end.

---

## 1. BLOCKERS — must clear BEFORE 00:00 (do this evening, zero downtime)

These are not optional. Each one silently breaks the deploy if skipped.
Status as of prep pass 2026-07-14:

| # | Blocker | Status | Detail |
|---|---------|--------|--------|
| B1 | `deploy.sh` pulls `origin main`, work was on `feat/b2c-partner-seam` | ✅ **DONE** | Merged → `main` (ff), pushed. No CI auto-deploy fires. |
| B2 | `PARTNER_API_KEY` not in iTourTT prod k8s secret (guard fails closed → all partner calls 401) | ⏳ **VPS action** | Patch prod backend secret = B2C key, restart backend. See §5. |
| B3 | B2C compose ran only the OLD single `web` → `fulvago` | ✅ **DONE** | 3-service compose + `backend/Dockerfile` committed to B2C `main` (`b6fe2cf`). See §6. |
| B4 | B2C backend has **0 migrations** (schema is `db push`-only) | ✅ **handled** | Deploy uses `prisma db push`; Dockerfile keeps `node_modules` so it runs in-container. |
| B5 | Super-admin + custom roles/grants are local-DB-only | ✅ **DONE** | Clean `deploy/b2c_seed.sql` built + test-restored (0 errors); scope = admins-only, no bookings (§6). + `deploy/uploads-media.tgz`. scp both to VPS. |
| B6 | Host nginx routed `:80/:443 → :3000` only | ✅ **DONE** | `deploy/nginx-transferra.conf` committed (`/api`+`/uploads`→:3002). Install + reload on VPS. |

**Remaining before window:** only **B2** (partner key on iTourTT prod) + **scp the two `deploy/` artifacts** to the B2C VPS. Everything else is cleared.

**Also prep tonight (safe, no downtime):**
- Full DB backup, both systems (§7).
- Pre-build B2C images on the VPS if possible (warms cache; cuts window). iTourTT uses `--no-cache` so its build runs live.
- Rotate Gemini key; confirm JWT/DB secrets strong + distinct on both prod.
- Confirm xlsx build can reach `cdn.sheetjs.com` (both backends pin the CDN tarball).

---

## 1A. Pre-deploy verification — DONE 2026-07-15 (live prod, read-only)

Ran against both production VPS. All green.

**Backups taken (full, verified) + downloaded to local:**
- iTourTT (72.62.45.40, k3s): `/root/itour-backup-20260715-000405` (3.9G) — DB (PGDMP custom + SQL + globals), uploads 3.6G, git bundle (all history) + working tree, k8s manifests + **secrets**, running 3.6.0 images. → local `/home/gouda/iTourTT-backup/`.
- B2C (31.97.45.33): `/root/b2c-backup-20260714-211305` (150M) — B2C git bundle + working tree + old `itourtt-b2c` image + nginx + **co-located mg-licenses DB dump & image**. → local `/home/gouda/B2C-backup/`.
- Both verified (git bundle OK, gzip OK, PGDMP OK, secrets captured).

**Rule: no data loss (iTourTT).** Diffed live prod schema vs the schema `db push --accept-data-loss` will enforce (pushed the new schema to a scratch DB, compared column-by-column):
- **DROPS: NONE.** Deploy is **purely additive**: `+user_sessions` table (9 cols), `+users.two_factor_*` (3 cols), + finance indexes.
- Live data preserved: `guest_bookings=38`, `b2c_invoices=19`, `users=69`, all ops tables intact.

**Rule: don't change iTourTT usernames/passwords.** Audited `src/prisma/seed.js` (runs on deploy):
- Admin upserts (`admin@itour.local`, `mggouda@gmail.com`) use **`update: {}` (empty)** → existing rows untouched; `passwordHash` only in the `create` branch (new users only).
- `user.updateMany` (line 567) sets **`roleId` only** — no password/email/name.
- Seed **never references** `system_settings`/`email_settings`. Migrations are DDL-only (ADD COLUMN / CREATE TABLE / CREATE INDEX). → **No credential changes.**

**Rule: integrations preserved.** All are DB- or secret-resident; `kubectl set image` touches neither:
- Google Maps → `system_settings.google_maps_api_key` (populated, len 39). Brevo email → `email_settings` (`smtp-relay.brevo.com`, user+pass set). AI → `backend-secret.GEMINI_API_KEY`. Payments → `backend-secret.GETPAYIN_*`.
- Nothing to move. Only deploy-time DB write (brand-color `UPDATE`) hits color columns only.

**New deploy-time concern found (B2C):** the B2C VPS `git fetch origin` did **not** advance to `8507955` (stuck at old `d5fc502`) — the box may lack GitHub pull access. **Verify B2C→GitHub before the window**; if it can't pull, push code via `rsync`/bundle from local or the iTourTT box. (My local↔origin are in sync; this is VPS-side only.)

**Access:** local↔iTourTT via password SSH (root@72.62.45.40); iTourTT→B2C via `/root/.ssh/b2c_vps`. ⚠️ **Rotate the iTourTT root password + that key after deploy** — both were shared in-session.

---

## 2. Time estimates

Downtime is small on both — the wall-clock is **build-dominated**. Pre-build where noted to shrink it.

### iTourTT (k3s VPS, `deploy.sh`)
| Step | Est. | Notes |
|------|------|-------|
| Merge→main + `git pull` | 1 min | done pre-window (B1) |
| Backend image build `--no-cache` | 6–10 min | live on VPS, unavoidable |
| Frontend image build `--no-cache` | 6–10 min | live on VPS |
| `docker save \| ctr import` ×2 | 2–3 min | |
| set image + rollout backend | ~2 min | replicas=2, rolling — near-zero user downtime |
| `migrate deploy` + `db push` | 1–2 min | 3 new migrations |
| seed | ~30 s | perms/params skipped |
| rollout frontend | ~2 min | |
| one-off SQL (§7) | ~1 min | |
| cleanup | ~2 min | |
| **iTourTT total** | **~25–35 min** | actual user-facing cutover ≈ 1–2 min |

### B2C (VPS 31.97.45.33)
| Step | Est. | Notes |
|------|------|-------|
| `git pull` | ~20 s | |
| compose build (backend + web) | 8–15 min | **halve if pre-built tonight** |
| compose up (pg+backend+web) | ~1 min | |
| `prisma db push` (create b2c_db) | ~30 s | B4 |
| recreate super-admin | ~2 min | B5 |
| nginx `/api` route + reload | ~2 min | B6 |
| **B2C total** | **~15–25 min** (~8–12 if pre-built) | |

### End-to-end connectivity tests (§8): **5–10 min**

**Grand total window: ~45–70 min** live-build, **~30–40 min** if B2C pre-built.
Recommend starting builds the moment the last live job closes.

---

## 3. iTourTT deploy — runbook (Phase 1)

Pre-window (B1) done → on the k3s VPS:

```bash
# 3.1 sanity: on prod VPS, main has the seam
cd /opt/itour && git fetch origin && git log origin/main --oneline | grep -i partner   # expect the partner-seam commits

# 3.2 backup FIRST (see §7)

# 3.3 run the deploy (builds, imports, sets image, migrates, seeds, rolls out)
./deploy.sh production
```

`deploy.sh` does: pull main → build backend+frontend `--no-cache` → `ctr import` → `set image` (both) → scale 2 → **rollout backend first** → `prisma migrate deploy` → `prisma db push --accept-data-loss` → seed (perms/params skipped) → rollout frontend → prune.

> ⚠️ **`db push --accept-data-loss` (line 67).** Backup (§7) covers you. Schema still declares every model (strip removed code, not tables) → no drops expected. If you want zero risk, comment line 67 for this run — `migrate deploy` is sufficient.

**Verify migrations actually applied** (steps are `|| true` → they don't fail the script):
```bash
NS=itour-production
kubectl exec -n $NS deployment/backend -- npx prisma migrate status | tail -20
# expect applied: 20260713_user_2fa, 20260713_user_sessions, 20260713_finance_indexes
```

Then run one-off SQL (§7), then the smoke checks (§8.1).

---

## 4. B2C deploy — runbook (Phase 2, after iTourTT verified)

On the B2C VPS (`31.97.45.33`, `/opt/iTourTT-B2CSite`). The 3-service stack, backend
Dockerfile, nginx conf, and env template are now **committed to `main`** (see §6).

```bash
cd /opt/iTourTT-B2CSite
git fetch origin && git checkout main && git pull   # main carries the standalone stack

# prod env (partner key MUST equal iTourTT prod §5):
cp backend/.env.production.example backend/.env.production && "$EDITOR" backend/.env.production
# root .env for compose interpolation:
printf 'B2C_DB_PASSWORD=<strong>\nNEXT_PUBLIC_API_URL=https://transferra.ae\n' > .env

# build + start all 3 services
docker compose up -d --build
docker compose ps                     # b2c-postgres, b2c-backend(:3002), itourtt-b2c(:3000) Up

# create schema on the fresh b2c_db (no migrations exist → db push)
docker compose exec backend npx prisma db push

# load the CLEAN B2C seed (built + test-restored locally; see §6). scp it up first:
#   scp deploy/b2c_seed.sql root@31.97.45.33:/opt/iTourTT-B2CSite/deploy/
docker compose exec -T postgres psql -U b2c -d b2c_db < deploy/b2c_seed.sql

# copy uploaded website media into the backend uploads volume (else images 404):
#   scp deploy/uploads-media.tgz root@31.97.45.33:/opt/iTourTT-B2CSite/deploy/
tar -xzf deploy/uploads-media.tgz -C /tmp/uploads-media
docker cp /tmp/uploads-media/. b2c-backend:/app/uploads/

# nginx: install site config + reload
sudo cp deploy/nginx-transferra.conf /etc/nginx/sites-available/transferra
sudo ln -sf /etc/nginx/sites-available/transferra /etc/nginx/sites-enabled/transferra
sudo nginx -t && sudo systemctl reload nginx
docker compose logs -f backend        # confirm boot + "B2C Backend running on ... 3002"
```

---

## 5. iTourTT prod PARTNER_API_KEY (B2)

Guard: `PartnerKeyGuard` compares `X-Partner-Key` header vs `process.env.PARTNER_API_KEY`, timing-safe, **fails closed if unset**. Must be in the prod backend secret and identical on both sides.

```bash
NS=itour-production
# inspect current secret keys (find the backend env secret name)
kubectl get secret -n $NS
# add/patch PARTNER_API_KEY (base64), then restart backend to pick it up
kubectl patch secret <backend-secret> -n $NS \
  --type merge -p "{\"data\":{\"PARTNER_API_KEY\":\"$(printf %s '<THE-KEY>' | base64 -w0)\"}}"
kubectl rollout restart deployment/backend -n $NS
```
`<THE-KEY>` = the value in B2C `backend/.env` `PARTNER_API_KEY`. **Copy it verbatim; do not regenerate one side only.**

---

## 6. B2C standalone stack — DONE (committed to `main`) + DB replication

**Infra artifacts now committed** (B2C repo `main`, commit `b6fe2cf`):
- `backend/Dockerfile` — was **missing**; Nest build → `node dist/src/main.js` on :3002, keeps `node_modules` so `prisma db push` runs in-container.
- `docker-compose.yml` — rewritten to **3 services**: `postgres`(b2c_db) + `backend`(:3002) + `web`(:3000), `b2c-uploads` + `b2c-pgdata` volumes.
- `deploy/nginx-transferra.conf` — `/`→:3000, `/api` + `/uploads`→:3002, `client_max_body_size 25m`.
- `backend/.env.production.example` — full env template (JWT, CORS_ORIGINS, PARTNER_API_KEY, ITOURTT_API_URL, AI/SMTP optional).

### DB replication — ⚠️ do NOT restore the raw local b2c_db
Local `b2c_db` is a **fork of iTourTT's data**: it carries iTourTT ops tables
(`agent_price_items` ~347k rows, `traffic_jobs`, `rep_fees`, notifications,
`activity_logs`) and 74 users that are mostly **iTourTT reps/drivers/fleet ops**
(21 DRIVER, 18 REP, 15 B2C_CLIENT, 14 VIEWER, 5 ADMIN, 1 SUPPLIER). Restoring it
wholesale would push iTourTT operational PII onto the **public** B2C server.

**Approach:** `prisma db push` (empty 86-table schema) → load the **clean selective seed**.
Both artifacts are **BUILT + VALIDATED** (in `deploy/`, gitignored):

- **`deploy/b2c_seed.sql`** (798K) — FK-closed, self-contained. Test-restored into a
  scratch schema clone with **zero errors**. Contents (verified counts):
  - config: `roles`(3), `role_permissions_v2`(101), `system_settings`(1), `website_settings`(1)
  - reference (FK closure, safe lookup): `countries`(1), `airports`(8), `cities`(18), `vehicle_types`(9)
  - content: `blog_posts`(24)+`blog_post_translations`(78), `city_pages`(12)+trans(30),
    `static_pages`(5)+trans(24), `page_seo`(8)+trans(48), `blog_categories`(3), `b2c_extras`(7)+`b2c_extra_vehicle_types`(51)
  - users: **4 ADMIN only** — `mggouda@gmail.com` (super-admin), `admin@itour.local`,
    `agency@transferra.ae`, `marwa.eladawy@fulvago.com`. Super-admin rides in here → **no
    separate create-superadmin script needed.**
  - Scope per go/no-go: **excluded** — non-admin users (21 driver/18 rep/15 client/14 viewer/1 supplier),
    the `test-2fa@transferra.ae` dev account, `guest_bookings`/`b2c_invoices`, and all iTourTT
    ops data (`agent_price_items` 347k, `traffic_jobs`, notifications, `activity_logs`).
    Verified post-restore: `guest_bookings=0`, `agent_price_items=0`, `non_admin_users=0`.

- **`deploy/uploads-media.tgz`** (9.2M, 30 files) — all **27** DB-referenced images.
  ⚠️ **Finding:** 19 of them were NOT in the B2C repo — they lived in **iTourTT's** uploads
  (`/home/gouda/iTourTT/backend/uploads`), because the OLD B2C served `/uploads` from
  `fulvago`. They're now merged into the tarball (incl. `iTour Logo.svg`, `Transfera-Logo`,
  `Favicon-Yellow`, all blog/city images). Space-safe verified: every seed ref resolves.

> Both files contain emails + bcrypt hashes → **gitignored, never committed**. scp them to
> the VPS `deploy/` dir before running §4. To regenerate: `scratchpad/gen_b2c_seed.sh`.

---

## 7. Data steps — backups + one-off SQL

**Backups (before any deploy):**
```bash
# iTourTT prod
kubectl exec -n itour-production deployment/postgres -- \
  pg_dump -U <user> itour_db | gzip > itour_db_$(date +%F).sql.gz
# B2C (if a prior DB exists; first standalone deploy starts empty)
```

**iTourTT one-off SQL (after migrate, via `kubectl exec ... psql`):**
```sql
-- Brand reset (slate/sky) — else old purple persists (branding is DB-driven)
UPDATE system_settings
SET primary_color='#0ea5e9', accent_color='#06b6d4', sidebar_color='#0f172a';

-- Backfill isPosted on rows created before the immutability fix
UPDATE payments       SET is_posted = true WHERE is_posted = false;
UPDATE supplier_costs SET is_posted = true WHERE is_posted = false;
```
> Verify exact table/column names against schema before running (`is_posted` on `payments` + `supplier_costs`).

---

## 8. API connectivity tests — partner seam

Run after **both** sides are up. `KEY` = the shared `PARTNER_API_KEY`. All read-only (safe on prod).

### 8.1 iTourTT seam reachable + auth correct
```bash
KEY='<PARTNER_API_KEY>'
BASE='https://fulvago.itourtt.cloud'

# positive — reference data
curl -sS -o /dev/null -w "reference: %{http_code}\n" -H "X-Partner-Key: $KEY" $BASE/api/partner/reference        # expect 200

# negative — wrong key (guard fails closed)
curl -sS -o /dev/null -w "wrong-key: %{http_code}\n" -H "X-Partner-Key: nope" $BASE/api/partner/reference        # expect 401

# negative — no key
curl -sS -o /dev/null -w "no-key:    %{http_code}\n" $BASE/api/partner/reference                                 # expect 401

# job status read (empty refs ok)
curl -sS -H "X-Partner-Key: $KEY" "$BASE/api/partner/jobs?refs=" | head -c 200; echo
```

### 8.2 B2C standalone self-check
```bash
BASE='https://transferra.ae'
curl -sS -o /dev/null -w "b2c public/pages: %{http_code}\n" $BASE/api/public/pages          # expect 200 (served by NEW backend, not fulvago)
curl -sSI $BASE/ | head -1                                                                   # site 200
```

### 8.3 End-to-end (real push) — preferred over synthetic POST
Do a live B2C quote/booking through the site UI, then confirm it landed:
```bash
# after a test booking on transferra.ae, its ref should appear:
curl -sS -H "X-Partner-Key: $KEY" "$BASE_ITOUR/api/partner/jobs?refs=<REF>" | jq .
docker compose logs backend | grep -i partner    # B2C side: push succeeded, no 401/timeout
```
> Synthetic `POST /api/partner/pricing` / `POST /api/partner/jobs` exist but **mutate prod** — prefer the real B2C flow above. If you must POST synthetically, use throwaway data and clean up. Bodies: `UpsertPublicPricesDto` (pricing), `PartnerJobDto` (jobs).

**Pass criteria:** 8.1 all expected codes · 8.2 both 200 (B2C served by its own backend) · 8.3 ref visible on iTourTT + no 401/timeout in B2C logs.

---

## 9. Rollback

**iTourTT** (images tagged per VERSION, prior kept until prune):
```bash
NS=itour-production
kubectl rollout undo deployment/backend  -n $NS
kubectl rollout undo deployment/frontend -n $NS
# migrations: additive (2FA cols, sessions table, indexes) — safe to leave. Restore from §7 dump only if data corrupted.
```
**B2C**: revert compose to prior commit + `docker compose up -d --build`; restore nginx site; the OLD single-container flow returns (but needs the old fulvago `/api/public/*` — which iTourTT no longer serves, so a B2C rollback implies an iTourTT rollback too). **Roll back both or neither.**

---

## 10. Post-deploy checklist
- [ ] iTourTT: login works; sidebar slate/sky (not purple); footer = ResLite format
- [ ] 2FA setup/verify round-trips; recovery codes show
- [ ] Rep/driver single-device lock: 2nd device → 409 + manager modal
- [ ] `/uploads` private doc needs auth; login branding still public
- [ ] Job Control appears in permission matrix; admins have it
- [ ] Finance: new payment posts `is_posted=true`, currency = invoice currency
- [ ] Email smoke test (nodemailer 9) sends
- [ ] xlsx export downloads (CDN reachable)
- [ ] §8 all green
- [ ] B2C: site loads; hero container has the 25% overlay; admin = ResLite light+dark
- [ ] B2C super-admin login works; roles/permissions replicated
- [ ] Local == origin on both repos (no commit drift)

---
*Prepared 2026-07-13. Execute at your go tonight 00:00. Deploy iTourTT → verify → B2C → verify end-to-end.*
