# CLAUDE.md
## iTour Transport & Traffic – AI Coding Instructions

This file defines **mandatory instructions** for Claude (or any AI coding agent) working on the
**iTour Transport & Traffic** project.  
These rules override all default behaviors.

---

## 1. PROJECT OVERVIEW

Project Name:
iTour Transport & Traffic

Purpose:
A full-stack enterprise transport, traffic, and accounting system for Egypt-based transfer operations,
fully compatible with Odoo ERP (no customization required on Odoo side).

This is **NOT an MVP**.  
This is a **production-grade system**.

---

## 2. TECH STACK (LOCKED)

Frontend:
- Next.js (latest, App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui

Backend:
- NestJS (latest)
- TypeScript
- REST APIs
- JWT + Refresh Tokens
- RBAC

Database:
- PostgreSQL
- Prisma ORM
- UUID primary keys
- Timezone: Africa/Cairo

Infrastructure:
- Docker
- Docker Compose

---

## 3. CORE BUSINESS RULES (NON-NEGOTIABLE)

### Location Tree
Country → Airport → City → Zone → Hotel

- Zones are the pricing unit
- Hotels must be cascaded by zone
- No flat or free-text locations

---

### Traffic Jobs
- Internal booking reference must be auto-generated
- Agent reference is optional
- Service types: ARR, DEP, CITY
- Pax count must never exceed vehicle capacity
- Assignment order:
  Vehicle → Driver → Rep

---

### Dispatch Console
- One window per day
- ARR jobs on the left, DEP jobs on the right
- Excel-like grid behavior
- Inline editing
- Keyboard navigation
- Real-time conflict validation

---

### Drivers
- Paid per trip
- Trip fees depend on route / zone
- Trips counted per period

---

### Reps
- Assigned after driver & vehicle
- Fee paid only if job is completed
- Full lifecycle tracking required

---

### Agents
- Full legal profile required
- Credit limit (amount)
- Credit days
- Invoice cycles
- Legal documents storage

---

### Finance
- No commission logic
- Taxes applied per Egyptian law
- Multi-currency supported
- Exchange rate stored per transaction

---

## 4. ODOO ERP COMPATIBILITY (CRITICAL)

Claude MUST ensure:
- All accounting exports import directly into Odoo
- No Odoo customization is allowed
- Correct mapping to:
  - res.partner
  - account.move
  - account.payment
  - account.tax

Exports must be:
- CSV or XLSX
- Odoo-ready format

---

## 5. DATABASE RULES

- Prisma ORM only
- No business logic in database
- Soft deletes where applicable
- Financial records immutable after posting
- Audit fields on all tables

---

## 6. API DESIGN RULES

- REST only
- Stateless endpoints
- Clear DTO validation
- Role guards on every endpoint
- Audit logging on create/update/delete

---

## 7. FRONTEND RULES

- No heavy modals for dispatch
- Grid-based layouts preferred
- Optimistic UI with rollback
- Role-based access rendering

---

## 8. WHAT CLAUDE SHOULD DO FIRST

Execution order:
1. Implement Prisma schema
2. Generate NestJS modules & services
3. Implement Dispatch API
4. Implement Dispatch UI
5. Implement Finance & Odoo exports
6. Add reporting

Claude must NOT:
- Skip modules
- Simplify workflows
- Introduce MVP shortcuts
- Change business rules

---

## 9. SINGLE SOURCE OF TRUTH

The following files must be treated as authoritative:
- 01-database-schema.md
- 02-api-contracts.md
- 03-odoo-accounting.md
- 04-dispatch-ui.md
- CLAUDE.md

If conflicts appear, **ask before changing anything**.

---

## 10. VERSION CONTROL & DEPLOYMENT WORKFLOW (MANDATORY)

Applies to **this system (`/opt/itour`) AND the B2C site repo/VPS** (iTourTT-B2CSite,
transfera.ae / 31.97.45.33).

After **every** edit, modification, addition, or deletion to the software, Claude MUST run this
sequence — never leave work uncommitted or unpushed (this is what caused the July 2026 commit-drift /
"GitHub missing commits" incident):

1. **Commit** — stage the change and commit with a clear, conventional message.
2. **Push** — push to the correct GitHub remote/branch immediately (keep local == origin, no drift).
3. **Verify** — confirm the change actually works:
   - For code with a runtime surface: build/typecheck, and drive the affected flow.
   - **Rebuild the image and run `deploy.sh` to production when the change needs to go live**
     (backend needs `NODE_OPTIONS=--max-old-space-size=5120`; after any deploy/restart, re-import the
     image into k3s containerd if pods hit `ErrImageNeverPull`, then verify pods Running + migrations
     applied). Skip the deploy for docs/notes with no runtime effect, but still commit + push.

Never end a task with uncommitted or unpushed changes to tracked files.

---

END OF FILE