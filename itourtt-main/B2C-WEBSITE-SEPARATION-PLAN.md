# B2C Website Separation Plan

Extract the public B2C booking website out of the dashboard monorepo into a
**standalone Next.js app** in its own repo, deployed on its **own VPS**.

> Status: **planning** — no code changes yet. This document is the agreed plan.

---

## 0. Locked decisions

| Topic | Decision |
|-------|----------|
| New repo | `https://github.com/mg-gouda/iTourTT-B2CSite` (already created) |
| Hosting | **New dedicated VPS** `31.97.45.33` (standalone Docker, *not* the k3s cluster) |
| Domain | `transferra.ae` — **DNS not pointed yet** (will A-record to `31.97.45.33` later) |
| Backend API | B2C calls the **existing** backend at `https://fulvago.itourtt.cloud/api` (add CORS) |
| Backend changes | **None** except adding the new origin to `CORS_ORIGINS` |
| Brand | **Single brand** — `transferra.ae` only. No multi-brand B2C for now. |
| Payments | **PAY_ON_ARRIVAL only** for launch. Online card payment is **deferred** to a later phase. |

---

## 1. Architecture

**Before** — one Next.js app serves both dashboard and `/w` B2C routes:
```
fulvago.itourtt.cloud (k3s, VPS 72.62.45.40)
  ├── /            dashboard
  ├── /w/**        B2C site         ← to be extracted
  └── /api/**      backend (NestJS)
```

**After**:
```
fulvago.itourtt.cloud (k3s, VPS 72.62.45.40)   ← unchanged
  ├── /            dashboard (no /w routes)
  └── /api/**      backend  (CORS now allows transferra.ae)

transferra.ae  (VPS 31.97.45.33, standalone Docker)   ← NEW
  └── iTourTT-B2CSite  →  fetches https://fulvago.itourtt.cloud/api/**
```

Auth note: the B2C portal uses its own `b2c_token` in `localStorage` and the
`/api/w-api/*` endpoints — completely independent of the dashboard session, so
cross-origin tokens are not a concern (Bearer header, not cookies).

---

## 2. Inventory — what moves to the new repo

### Routes (`frontend/src/app/w/**` → new `src/app/**`, dropping the `w` segment)
```
w/layout.tsx              → app/layout.tsx (merge with root layout: fonts, theme)
w/website-shell.tsx       → app/website-shell.tsx
w/page.tsx                → app/page.tsx                 (landing)
w/landing-client.tsx      → app/landing-client.tsx
w/book/**                 → app/book/**                 (vehicle → flight → details)
w/booking/lookup/**       → app/booking/lookup/**        (track booking)
w/login/**                → app/login/**                (B2C client login)
w/account/**              → app/account/**              (account + bookings + amend)
```

### Components (`frontend/src/components/website/**` → `src/components/**`)
`site-header.tsx`, `site-footer.tsx`, `hero-section.tsx`, `features-section.tsx`, `booking-widget.tsx`

### Shared libs/stores
`lib/site-settings.ts`, `lib/website-i18n.tsx`, `lib/utils.ts` (`cn`), `stores/booking-store.ts`

### shadcn/ui primitives needed
`input, label, button, select, popover, card, badge`

---

## 3. Backend API surface consumed (NO backend code changes)

`/api/public/*` (public-api controller):
- `GET  website-settings`, `GET google-maps-key`, `GET locations`
- `GET  vehicle-types`, `POST vehicle-quotes`, `POST quote`
- `GET  extras`
- `POST bookings`  (create guest booking)

`/api/w-api/*` (b2c controller — client portal):
- `POST login`, `POST change-password`
- `GET  bookings`, `GET bookings/:ref`, `PATCH bookings/:ref`, `DELETE bookings/:ref`

---

## 4. Required code changes during the port (the real work)

1. **Strip the `/w` prefix everywhere.** Standalone serves at root.
   - Route folders: `app/w/book` → `app/book`, etc.
   - Every `href="/w/..."`, `router.push('/w/...')`, `router.replace('/w/...')`,
     nav-link `href`, footer quick-links, and the redirect targets in
     `account-client` / `login-client`.
   - Note: `site-header` Logo already links `/` and Book Now `/book` — those
     become *correct* at root; only the `/w/...` ones need rewriting.

2. **Make `/uploads/` image URLs absolute.** Images (vehicle photos, site logo,
   favicon) come back as bare paths like `/uploads/x.jpg`. On `transferra.ae`
   those resolve to the wrong host. Add a resolver that prefixes
   `NEXT_PUBLIC_API_URL` and apply it to: vehicle-card images, `siteLogoUrl`,
   `siteFaviconUrl`, and any other rendered `/uploads/...`.

3. **API base URL.** Add `src/lib/api.ts` (thin client) and confirm
   `site-settings.ts` SSR path: it currently does
   `INTERNAL_API_URL ?? NEXT_PUBLIC_API_URL ?? localhost`. On the new VPS
   `INTERNAL_API_URL` is unset, so SSR falls back to `NEXT_PUBLIC_API_URL` —
   which must be set **both at build time** (client bundle) **and runtime** (SSR).

4. **Root layout merge.** The new app needs a real root `app/layout.tsx`
   (`<html><body>`, `Toaster`, `globals.css` with the theme tokens) combined
   with the dynamic-font / theming logic currently in `w/layout.tsx`.

---

## 5. Phased steps

### Phase 1 — Scaffold the new repo (local)
```bash
git clone git@github.com:mg-gouda/iTourTT-B2CSite.git
cd iTourTT-B2CSite
npx create-next-app@latest . --ts --tailwind --app --src-dir --no-eslint --import-alias "@/*"
npx shadcn@latest init
npx shadcn@latest add input label button select popover card badge
```

### Phase 2 — Port code
- Copy routes, components, libs, store per §2.
- Apply the four changes in §4 (prefix strip, absolute uploads, api.ts, layout).
- Add `.env.example`:
  ```
  NEXT_PUBLIC_API_URL=https://fulvago.itourtt.cloud
  NEXT_PUBLIC_GOOGLE_MAPS_KEY=...        # if maps used in selectors
  ```
- `npm run build` until clean; smoke-test locally against the live API.

### Phase 3 — Backend CORS — ✅ DONE
`CORS_ORIGINS` is read at runtime from the `backend-secret` Secret (via
`envFrom`), **not** from the repo. Applied to **production only** (B2C calls the
production backend):
```bash
kubectl patch secret backend-secret -n itour-production --type merge \
  -p '{"stringData":{"CORS_ORIGINS":"https://fulvago.itourtt.cloud,https://transferra.ae,https://www.transferra.ae,http://31.97.45.33"}}'
kubectl rollout restart deployment/backend -n itour-production
```
Verified: `transferra.ae` and `31.97.45.33` reflected in `access-control-allow-origin`;
unknown origins rejected. The `http://31.97.45.33` entry is temporary for
pre-DNS testing — drop it once `transferra.ae` is live on HTTPS.

> ⚠️ This is a **live, out-of-repo** secret edit. If `backend-secret` is ever
> recreated, the new origins must be re-added. Not captured by `deploy.sh`.
>
> ⚠️ Gotcha hit during this step: `deploy.sh`'s image-cleanup had pruned
> `itourtt-backend:3.4.0` from k3s containerd (running pods kept their snapshot,
> but new pods got `ErrImageNeverPull`). Fixed by re-importing:
> `docker save itourtt-backend:3.4.0 | k3s ctr images import -`. Self-heals on the
> next full `./deploy.sh`, but ad-hoc pod restarts can fail until then.

### Phase 4 — Containerize
- `Dockerfile` mirroring `frontend/Dockerfile` (Next standalone output).
  Pass `NEXT_PUBLIC_API_URL` as a **build-arg** (baked into client) and also as a
  **runtime env** (for SSR).
- `docker-compose.yml` (app on :3000) for the new VPS.

### Phase 5 — New VPS (`31.97.45.33`)
- Install Docker + Docker Compose.
- nginx reverse proxy `:80/:443` → app `:3000`; proxy `/uploads` is **not**
  needed (images use absolute backend URLs per §4.2).
- TLS via certbot/Let's Encrypt — **after** DNS points (until then test over
  `http://31.97.45.33`).
- Deploy: build image, `docker compose up -d`.

### Phase 6 — Remove `/w` from the dashboard (only AFTER new site verified)
- Delete `app/w/**`, `components/website/**`, and now-unused `site-settings.ts`,
  `website-i18n.tsx`, `booking-store.ts` from `frontend/`.
- Remove `/w` links from the dashboard.
- `./deploy.sh all`.

### Phase 7 — DNS cutover
- A-record `transferra.ae` + `www` → `31.97.45.33`.
- Issue TLS, smoke-test full flow (search → quote → extras → book → confirmation;
  login → account → bookings → amend/cancel).

---

## 6. Resolved decisions & remaining checks

**Resolved:**
- **Online payments — deferred.** Launch is PAY_ON_ARRIVAL only (current `/w`
  behavior). Do **not** port the `(public)` payment flow now. See §8 (Future).
- **Multi-brand — no.** Single brand `transferra.ae`. Global `site-settings`
  is fine as-is; no per-host settings work needed.

**Still to check during execution:**
1. **Google Maps key** exposure on the new origin (add `transferra.ae` to the
   key's HTTP-referrer allowlist).
2. **`app/(public)/**` in the dashboard repo** — leave untouched for now; it is
   the reference we port from when online payment is added later (§8). Do not
   delete it in Phase 6.

---

## 7. Rollback

Until Phase 6, the `/w` site stays live on `fulvago` — the new site is purely
additive. If anything fails, just don't cut over DNS; nothing in production is
touched except the additive CORS origin (harmless).

---

## 8. Future phase — online card payment (deferred)

Not in scope for launch, but the path is known so we don't paint ourselves into
a corner:
- Keep the booking-store `paymentMethod` field and the `/api/public/bookings`
  contract (it already accepts `ONLINE` + `paymentGateway`).
- When needed, port the payment pages from the dashboard repo's
  `app/(public)/**` group (`book/payment`, `payment/success`, `payment/cancel`)
  into the B2C app and switch `details-client` from hardcoded `PAY_ON_ARRIVAL`
  to a method choice.
- Confirm gateway redirect/return URLs use the `transferra.ae` origin.
- This is why `app/(public)/**` is **not** deleted from the dashboard repo in
  Phase 6 — it stays as the reference implementation.

---

## What does NOT change
- Backend API code (only a CORS origin added).
- Dashboard app and all its routes.
- The `/dashboard/website` admin panel that edits site settings.
