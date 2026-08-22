# Plan — Admin "B2C Invoices" page

## Context

B2C guest invoices (`B2CInvoice`, `INV-B2C-NNNNN`) are created when a guest booking
is paid and the PDF is emailed + downloadable from the guest's own account. There
is currently **no admin-area view** of them: the only admin touchpoints are the
two **Finance → Odoo Exports** CSV buttons (`account.move — B2C Invoices`,
`res.partner — B2C Guests`) and the **Guest Bookings** page (which shows payment
status, not invoices). The B2B `Finance → Invoices` screens are a different system
(`AgentInvoice`). This plan adds a browsable, filterable admin list of B2C
invoices with per-row PDF download.

Reuses the existing `B2CInvoiceService` (`backend/src/b2c/b2c-invoice.service.ts`)
and the established finance controller / permission / admin-page patterns.

## Scope (basic version)

Admin list of B2C invoices with date-range + search filters and per-row PDF
download. Read-only (no edit/void/resend in v1 — see "Optional extras").

---

## Backend

### 1. Service methods — `backend/src/b2c/b2c-invoice.service.ts`
Add admin (non-ownership-scoped) methods alongside the existing
`listForClient` / `getOwnedPdf`:

- `listAll({ page, limit, search, dateFrom, dateTo, status })` — paginated, newest
  first. `where: { deletedAt: null, ... }`; `search` matches `invoiceNumber` or
  `guestBooking.bookingRef` / `guestBooking.guestName` / `guestBooking.guestEmail`
  (insensitive); `dateFrom/dateTo` filter `issuedAt`; optional `status`. Select:
  number, issuedAt, currency, subtotal, taxAmount, total, status, and
  `guestBooking { bookingRef, guestName, guestEmail, jobDate, serviceType }`.
  Return shape like other paginated finance lists (`PaginatedResponse`).
- `getPdfById(invoiceId)` — admin download; just `return this.generatePdf(invoiceId)`
  (no ownership check, since access is gated by the admin permission).

### 2. Controller routes — `backend/src/finance/finance.controller.ts`
The controller already injects services and is guarded by
`JwtAuthGuard, RolesGuard, PermissionsGuard`. Inject `B2CInvoiceService`
(via `FinanceModule` importing `B2CModule`, which already exports it) and add:

- `@Get('b2c-invoices')` `@Permissions('finance.b2cInvoices')` →
  `listAll(query)` (query DTO: page, limit, search, dateFrom, dateTo, status).
- `@Get('b2c-invoices/:id/pdf')` `@Permissions('finance.b2cInvoices')` →
  stream `getPdfById(id)` with
  `Content-Type: application/pdf` + `Content-Disposition: attachment`
  (mirror the existing `invoices/:id/pdf` route at finance.controller.ts:262).

### 3. Permission — `finance.b2cInvoices`
- Add to backend registry `backend/src/permissions/permission-registry.ts` under
  the `finance` node's `children` (sibling of `finance.invoices`).
- Add to frontend registry `frontend/src/lib/permission-registry.ts` (same tree,
  with `crudType: 'R'`).
- Add i18n label `permissions.finance.b2cInvoices` (en + any other locales used by
  the permission matrix).
- Grant to the relevant roles in `backend/src/prisma/seed.ts` (the role permission
  arrays near lines 85–93 / 364 — add `'finance.b2cInvoices'`).

### Module wiring
`FinanceModule` must import `B2CModule` to inject `B2CInvoiceService`
(B2CModule already `exports` it). Watch for a circular import — B2CModule does not
import FinanceModule, so this is one-directional and safe.

---

## Frontend

### Page — `frontend/src/app/(dashboard)/dashboard/finance/b2c-invoices/page.tsx` (new)
- Table: Invoice #, Date, Guest (name/email), Booking Ref, Service, Amount
  (currency+total), Status badge.
- Filters: date-range (from/to), search box, optional status dropdown; server-side
  via the list endpoint query params. Pagination control.
- Per-row **Download PDF** button → `api.get('/finance/b2c-invoices/:id/pdf',
  { responseType: 'blob' })` then blob-download (same approach as the Odoo export
  handler in `finance/page.tsx` and the guest InvoicesTab).
- Reuse existing admin table / card / button components and the `api` client.
- Gate the page + nav entry on `finance.b2cInvoices`.

### Navigation — `frontend/src/components/sidebar.tsx`
Add a link (e.g. under Finance) `{"B2C Invoices", href:"/dashboard/finance/b2c-invoices",
permissionKey:"finance.b2cInvoices"}`. (Alternatively a tab/section inside the
existing finance page — but a dedicated route is cleaner and matches guest-bookings.)

---

## Files touched
- `backend/src/b2c/b2c-invoice.service.ts` (add `listAll`, `getPdfById`)
- `backend/src/finance/finance.controller.ts` (2 routes) + `finance.module.ts` (import B2CModule)
- `backend/src/permissions/permission-registry.ts`, `backend/src/prisma/seed.ts`
- `frontend/src/lib/permission-registry.ts`, i18n files
- `frontend/src/app/(dashboard)/dashboard/finance/b2c-invoices/page.tsx` (new)
- `frontend/src/components/sidebar.tsx`

## Verification
1. `tsc` clean (backend + frontend).
2. As a finance user: page lists B2C invoices; filters + search + pagination work;
   PDF download returns a valid `INV-B2C-NNNNN.pdf`.
3. A user without `finance.b2cInvoices` sees neither the nav entry nor the page
   (403 on the API).
4. Deploy via `./deploy.sh production` (backend image + frontend build; seed grants
   the new permission).

## Optional extras (not in basic scope)
- **Resend invoice email** to the guest (reuse email + `generatePdf`). +~5 min.
- **Void / mark refunded / regenerate** an invoice (status transitions). +~10 min.
- Surface the invoice number + PDF link directly on the existing **Guest Bookings**
  detail row.

## Estimate
~20–30 min total; most of the elapsed time is the deploy cycle since the logic
reuses existing infrastructure.
