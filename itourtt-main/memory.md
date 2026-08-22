# Memory – iTour Transport & Traffic

This file tracks **all user instructions, decisions, and session progress** throughout the development journey.

---

## Session 1 – 2026-01-29

### Instructions Received
1. Read all spec files before starting development.
2. Create `memory.md` to track instructions and session progress.
3. Create `progress.md` to track project progress per completed function.
4. Utilize Claude agents/cowork for parallel development.
5. Start development following the mandated build order from CLAUDE.md.

### Decisions Made
- Project starts from scratch (no existing code, only spec .md files).
- Build order follows CLAUDE.md: Prisma schema -> NestJS modules -> Dispatch API -> Dispatch UI -> Finance & Odoo -> Reporting.
- Using parallel agents for independent tasks (e.g., frontend + backend scaffolding).

### Standing Instructions (from CLAUDE.md & user)
- Login form: compact, glass effect, black abstract background with 10% blur.
- No MVP shortcuts. Production-grade code only.
- Tech stack is locked. No substitutions.
- Zones are the pricing unit. Location tree is strict hierarchy.
- Assignment order: Vehicle -> Driver -> Rep.
- Pax must never exceed vehicle capacity.
- Financial records immutable after posting.
- All exports must be Odoo-ready (no Odoo customization).
- If conflicts in specs appear, ask before changing.

---

---

## Session 2 – 2026-02-06

### Phase 10 Refactor – Design Decisions
User chose the following for the Traffic Assign redesign:

1. **ServiceType CITY → EXCURSION**: Rename enum value (remove CITY entirely)
2. **Origin/Destination storage**: 6 separate FK columns (originAirportId, originZoneId, originHotelId, destinationAirportId, destinationZoneId, destinationHotelId)
3. **hotelId field**: Keep deprecated (nullable FK preserved)
4. **Customer invoicing**: Reuse AgentInvoice (nullable agentId + customerId)
5. **Notes field**: Keep on both Online and B2B tabs

### Work Completed
- Updated Prisma schema: removed CITY enum, added 6 origin/dest FKs, made AgentInvoice.agentId nullable, added customerId, removed CustomerInvoice/CustomerInvoiceLine/CustomerPayment models
- Synced DB via `prisma db push` + baseline migration
- Updated all backend services: traffic-jobs, dispatch, finance, export, reports, customers DTOs
- Updated all frontend: types, traffic-jobs page (12 service types, separate FK form fields), dispatch page, finance page, rep portal pages
- Zero TypeScript errors in both frontend and backend

### Remaining Phase 10 Work
- ~~Rep flight-aware validation~~ (already implemented)
- ~~Driver time-aware validation~~ (already implemented)
- ~~Available drivers/reps rewrite with jobId param~~ (already implemented)
- ~~Block rep assignment on Excursion jobs~~ (already implemented)
- ~~Add "customers" to role permission seeds~~ (completed)

**Phase 10 is 100% complete.**

---

## Session 2 (continued) – 2026-02-06

### Phase 11: Driver Extranet + No Show Evidence

User requested:
1. **Driver Extranet** — mirrors the Rep Extranet so drivers can log in, see jobs, update statuses, view trip fee history, and receive notifications
2. **No Show Evidence** — both driver and rep extranets require 2 photo uploads + GPS location capture when marking a job as NO_SHOW

### Design Decisions
- No Show evidence stored in separate `NoShowEvidence` model (not on TrafficJob)
- GPS coordinates + Google Maps link stored per evidence record
- `submittedBy` field tracks whether DRIVER or REP submitted the evidence
- NO_SHOW removed from simple status update endpoints — must go through evidence endpoint
- COMPLETED and CANCELLED still use simple confirmation
- Driver portal at `/driver`, mirrors rep portal at `/rep`

### Work Completed
- Schema: DRIVER role, Driver.userId FK, DriverNotification model, NoShowEvidence model
- Backend: auth driverId resolution, driver account management (create/reset password), driver-portal module (8 endpoints), rep-portal no-show endpoint
- Frontend: DRIVER type, login redirect, NoShowEvidenceDialog shared component, driver portal (layout + dashboard + history), rep portal modified to use evidence dialog
- Zero TypeScript errors in both frontend and backend

---

## Session 4 – 2026-02-08

### Work Completed

#### Vehicle Compliance & Deposits
- Added vehicle compliance tracking (insurance, license, inspection dates)
- Vehicle detail page with compliance history
- New vehicle form page
- Deposit payment DTO and endpoint

#### Dispatch Export & Client Sign PDF
- Implemented bulk PDF generation for client pickup signs using `pdf-lib`
- Signs include company logo (90% page width), "Mr/Mrs" text, and large bold client name
- Print Signs button on traffic jobs page generates PDF for tomorrow's date
- Jobs with `printSign=true` and non-null `clientName` are included

#### WYSIWYG Rich Text Editor (TipTap)
- Replaced raw HTML textareas for report header/footer with TipTap WYSIWYG editor
- Created `frontend/src/components/rich-text-editor.tsx` with full toolbar:
  - Bold, Italic, Underline, H1/H2/H3, Bullet/Ordered List, Align L/C/R
  - Table support (insert, add/delete rows/columns, delete table)
  - Company logo insertion with size slider (10-100%)
  - Shortcode buttons: {{reportName}}, {{dateTime}}, {{user}}
- Packages: @tiptap/react, @tiptap/starter-kit, @tiptap/extension-text-align, @tiptap/extension-underline, @tiptap/extension-image, @tiptap/extension-table (+ row/cell/header)

#### Reports Page UI
- Made stat cards compact (reduced padding, font sizes)
- All stats in single row using grid layout
- Service type cards on same line as stats (8 equal-width cards)
- Fixed duplicate React key warning in compliance table

#### Other Fixes
- Fixed dispatch page customer rep fields display
- Updated driver portal and rep portal pages
- Updated B2B traffic jobs page
- Updated i18n translations (en + ar)

---

## Change Log

| Date | Change | Requested By |
|------|--------|-------------|
| 2026-01-29 | Project initialized, memory.md and progress.md created | User |
| 2026-02-06 | Phase 10 schema refactor: CITY→EXCURSION, 6 FK columns, AgentInvoice consolidation | User |
| 2026-02-06 | Phase 10 backend+frontend updates for refactored schema | User |
| 2026-02-06 | Phase 10 completed: all dispatch validations confirmed, customers added to role permissions | User |
| 2026-02-06 | Phase 11: Driver Extranet + No Show Evidence (schema, backend, frontend) | User |
| 2026-02-08 | Session 4: Customer rep fields, dispatch export, client sign PDF, WYSIWYG editor, reports UI | User |
