# iTourTT - Transport & Traffic Management System — v3.4.0

> **PROPRIETARY SOFTWARE** — This project is **not open source**. All rights reserved. Viewing the source code does not grant permission to use, copy, modify, or distribute it. See [LICENSE](LICENSE) for details. Unauthorized use will be prosecuted.

A production-grade, full-stack enterprise transport, traffic, and accounting system built for Egypt-based transfer operations. Fully compatible with Odoo ERP — no customization required on the Odoo side.

## Live Environments

| Environment | URL |
|---|---|
| Production (Fulvago) | https://fulvago.itourtt.cloud |

## Overview

iTourTT manages the complete lifecycle of transport operations: from booking traffic jobs and dispatching vehicles, to invoicing agents and exporting Odoo-ready accounting data. The system supports multiple user roles, real-time dispatch, multi-currency finance, and bilingual (English/Arabic) interfaces.

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| **Backend** | NestJS, TypeScript, REST APIs, JWT + Refresh Tokens |
| **Database** | PostgreSQL 16, Prisma ORM, UUID primary keys |
| **Infrastructure** | k3s (Kubernetes), Docker, cert-manager + Let's Encrypt SSL |
| **Timezone** | Africa/Cairo |

## Key Features

### Dispatch Console
- Daily view with ARR (arrival) jobs on the left, DEP (departure) on the right
- Excel-like inline editing grid with keyboard navigation
- Real-time conflict validation (capacity, double-booking)
- **Split assignment logic**: dispatchers assign vehicle + driver independently; online operators assign rep independently — neither side needs to wait for the other
- **Vehicle Fleet Overview**: visual card strip per vehicle showing all day's assignments with automatic conflict detection (🔴 confirmed time overlap within 2h, 🟡 missing time data)
- **Rep Overview**: same visual cards grouped by rep — visible to online operators
- 48-hour dispatcher time-lock with manual unlock per job
- Excel export

### Traffic Jobs
- B2B (agent) and Online (direct) booking management
- Service types: ARR, DEP, CITY, ROUND_TRIP, EXCURSION, and more
- Auto-generated internal booking references (ITT-XXXX)
- Pax count validated against vehicle capacity
- Collection amount support (multi-currency)

### Finance & Invoicing
- Multi-currency support with exchange rates stored per transaction
- Egyptian tax compliance
- Invoice lifecycle: Draft -> Posted (immutable) -> Paid
- Odoo ERP-compatible Excel exports (res.partner, account.move, account.payment, account.tax)

### Location Hierarchy
- Country -> Airport -> City -> Zone -> Hotel
- Zones as the fundamental pricing unit
- All route pricing is zone-to-zone
- **Google Maps verified coordinates** on all locations (lat/lng/placeId)
- Google Places autocomplete for location creation and editing
- Batch geocode tool for resolving existing locations without coordinates
- Full CRUD: create, edit (rename, update coordinates), and soft-delete
- Pre-seeded with 7 Egyptian airports, 12 cities, 32 zones, 107 hotels

### Geofencing
- **500m radius geofence enforcement** on driver and rep portal status changes
- Drivers must be within 500m of the airport (ARR) or hotel/zone (DEP/CITY) to complete/cancel/no-show
- Reps must be within 500m of the airport to submit status updates
- Clear error messages when outside geofence or when location coordinates are missing
- Haversine distance calculation for accurate GPS proximity checks

### Fleet Management
- Vehicle types with seat capacity enforcement
- Compliance document tracking with expiry alerts
- Driver and rep management with portal access

### Agent Management
- Full legal profile with document storage
- Credit limits and credit days
- Customizable price lists per agent (zone-to-zone, per vehicle type)
- Configurable invoice cycles

### Supplier Portal
- External transport providers with their own vehicles, drivers, and price lists
- Self-service portal for supplier resource management

### No-Show Evidence
- Submitted by driver or rep via their portal
- Up to 10 geo-tagged photos per submission
- Clickable badge on traffic jobs table opens evidence modal
- Submitter label shows `ROLE-UserName`

### Permissions & Security
- Role-Based Access Control (RBAC) with granular permission tree
- 13 system roles: Admin, Dispatcher, Accountant, Agent Manager, Viewer, Rep, Driver, Online Operator, Dispatch Operator, Online Manager, Dispatch Manager, FC, Transportation Accountant
- **Permission-based dispatch**: Online Operators can only assign reps; Dispatch Operators can only assign vehicles/drivers — enforced at both API and UI level
- Permission-based UI rendering (sidebar, pages, actions, columns)
- JWT authentication with refresh token rotation

### Activity Log
- Automatic audit trail for all create/update/delete actions
- Filterable by user, action type, entity, and date range
- Detailed request data captured per action
- Excel export for compliance and auditing

### Portals
- **Driver Portal** - View assignments, update trip status with GPS tracking
- **Rep Portal** - Track assignments, update status with live GPS location
- **Supplier Portal** - Manage vehicles, drivers, and pricing

### Reports & Exports
- Operational and financial reporting
- Configurable date ranges and filters
- Excel export across all modules
- Odoo-ready accounting export format

### Driver & Rep Detail Pages
- Full profile page per driver: Profile, Vehicles (assign/unassign + primary), Trip Fees (date-filtered history), Account (portal login / password reset)
- Full profile page per rep: Profile, Zones (assign/unassign coverage areas), Fees (date-filtered history), Account
- Trip fee and rep fee history endpoints with date-range filtering and total summaries

### WhatsApp Notifications (3-Template System)
- Three independent message templates, each with its own trigger:
  - **Booking Confirmation** — fires immediately when a traffic job is created
  - **Driver Assigned** — fires when a driver is assigned in the Dispatch Console
  - **Day-Before Reminder** — fires on a configurable schedule (days before + hour + minute, Cairo time)
- Each template independently enabled/disabled with body editor, variable chips, and live preview
- Per-minute cron ensures minute-accurate scheduled delivery
- Deduplication: same template never sent twice to same phone for same job
- Shared media attachment (image/PDF) sent with every message

### Odoo ERP Exports
- Five one-click Excel exports directly importable into Odoo with no customization:
  - Partners (res.partner) — agents and suppliers
  - Customer Invoices (account.move)
  - Vendor Bills (account.move)
  - Payments (account.payment)
  - All-in-One combined export
- External ID system (`itour_agent_<id>`, `itour_inv_<id>`) for idempotent re-imports
- Optional date-range filtering for invoice/payment exports

### Invoice Scheduler
- Automatic draft invoice generation per agent based on their configured invoice cycle
- Supports WEEKLY (day of week), BIWEEKLY (every even ISO week), MONTHLY (day of month)
- Runs daily at 01:00 Cairo time

### Password Reset
- Forgot Password flow: email link with time-limited SHA-256 hashed token (60-minute expiry)
- Reset Password page with show/hide password toggle and auto-redirect on success
- Integrated with email notification system

### Built-in Help Center
- Comprehensive user manual for all 19 system modules (including Guest Bookings and Public Prices)
- Searchable documentation with step-by-step instructions and tips in English and Arabic
- Accessible via the header help icon

### Internationalization
- Full English and Arabic language support
- RTL layout support for Arabic

## Project Structure

```
iTourTT/
├── backend/                  # NestJS API server
│   ├── prisma/               # Database schema & migrations
│   ├── src/
│   │   ├── auth/             # JWT authentication & refresh tokens
│   │   ├── permissions/      # RBAC permission system
│   │   ├── users/            # User management
│   │   ├── locations/        # Location hierarchy (Country->Hotel)
│   │   ├── vehicles/         # Fleet & vehicle types
│   │   ├── drivers/          # Driver management
│   │   ├── reps/             # Representative management
│   │   ├── agents/           # Agent profiles & price lists
│   │   ├── customers/        # Customer records
│   │   ├── suppliers/        # Supplier management
│   │   ├── traffic-jobs/     # Booking management
│   │   ├── dispatch/         # Dispatch console API
│   │   ├── finance/          # Invoicing & Odoo exports
│   │   ├── reports/          # Report generation
│   │   ├── activity-logs/    # Audit trail
│   │   ├── job-locks/        # Concurrent editing protection
│   │   ├── settings/         # Company settings
│   │   ├── driver-portal/    # Driver portal API
│   │   ├── rep-portal/       # Rep portal API
│   │   ├── supplier-portal/  # Supplier portal API
│   │   └── whatsapp-notifications/  # WhatsApp templates
│   └── Dockerfile
├── frontend/                 # Next.js application
│   ├── src/
│   │   ├── app/
│   │   │   ├── (dashboard)/  # Main dashboard pages
│   │   │   ├── (driver-portal)/   # Driver portal
│   │   │   ├── (rep-portal)/      # Rep portal
│   │   │   ├── (supplier-portal)/ # Supplier portal
│   │   │   └── login/        # Authentication
│   │   ├── components/       # Reusable UI components
│   │   ├── lib/              # Utilities, i18n, API client
│   │   ├── stores/           # Zustand state management
│   │   └── hooks/            # Custom React hooks
│   └── Dockerfile
└── docker-compose.yml        # Full stack orchestration
```

## Getting Started

### Prerequisites

- Node.js 20+
- PostgreSQL 16+ (or use Docker)
- npm

### Quick Start with Docker

```bash
# Clone the repository
git clone https://github.com/mg-gouda/itourtt.git
cd itourtt

# Create environment file
cp .env.example .env
# Edit .env with your JWT secrets

# Start all services
docker compose up -d

# The application will be available at:
# Frontend: http://localhost:3000
# Backend:  http://localhost:3001
```

### Manual Setup

**Backend:**

```bash
cd backend
npm install
npx prisma db push
npx prisma db seed
npm run start:dev
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

### Default Admin Credentials

```
Email:    admin@itour.local
Password: Admin@123
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `POSTGRES_USER` | Database user | `itour` |
| `POSTGRES_PASSWORD` | Database password | `itour_secure_2026` |
| `POSTGRES_DB` | Database name | `itour_db` |
| `JWT_SECRET` | JWT signing secret | Required |
| `JWT_EXPIRES_IN` | Access token TTL | `15m` |
| `JWT_REFRESH_SECRET` | Refresh token secret | Required |
| `JWT_REFRESH_EXPIRES_IN` | Refresh token TTL | `7d` |
| `BACKEND_PORT` | Backend port | `3001` |
| `FRONTEND_PORT` | Frontend port | `3000` |

## API Documentation

All endpoints follow REST conventions with JWT authentication:

- `POST /auth/login` - Authenticate and receive tokens
- `POST /auth/refresh` - Refresh access token
- `GET/POST/PATCH/DELETE /api/{resource}` - CRUD operations
- All mutating endpoints are audit-logged automatically

## Changelog

### v3.3.0 — 2026-03-17
- **Geofencing**: 500m radius enforcement on driver and rep portal status changes (complete, cancel, no-show, in-place) — must be physically near the job's location
- **Google Maps verified locations**: All location models (Country, Airport, City, Zone, Hotel) now store latitude, longitude, and Google Place ID
- **Google Places autocomplete**: Integrated into all location creation and editing dialogs — search Google Maps, pick a result, coordinates auto-filled
- **Location editing**: Full edit support for all location levels (rename, update code, change coordinates via Google Places)
- **Batch geocode**: Admin tool to auto-resolve coordinates for existing locations without GPS data, with manual review for ambiguous results
- **Egypt location seed**: Comprehensive seed with 7 airports, 12 cities, 32 zones, and 107 hotels — all with verified Google Maps coordinates
- Haversine distance utility for accurate geofence calculations
- Deploy script now runs database seed on every deployment

### v3.1.1 — 2026-03-09
- Removed 3-hour gap rule for rep assignment — reps can now be assigned to multiple jobs on different flights without time restrictions

### v3.1.0 — 2026-03-09
- **Permission-based dispatch**: Separated rep assignment from vehicle/driver assignment with granular permission enforcement — Online Operators assign reps only, Dispatch Operators assign vehicles/drivers only
- Switched dispatch controller from role-based guards (`@Roles`) to permission-based guards (`@Permissions`)
- 6 new system roles: Online Operator, Dispatch Operator, Online Manager, Dispatch Manager, FC, Transportation Accountant
- Fixed no_show_evidence table schema (image_urls array, decimal GPS, NOT NULL constraints)
- Infrastructure migrated to k3s (Kubernetes) with cert-manager + Let's Encrypt SSL
- Separate production and training namespaces on single-node k3s cluster

### v3.0.0 — 2026-03-08
- Bump to v3.0.0
- Login page version reads from package.json (`NEXT_PUBLIC_APP_VERSION`)
- Added missing i18n keys (forgotPassword)
- Added missing DB tables (device_tokens, customer_import_templates, job_import_logs)
- Help documentation expanded for all 19 modules

### v2.1.0 — 2026-03-06
- Split assignment: dispatchers assign vehicle+driver, online operators assign rep independently
- Vehicle Fleet Overview panel with red/amber conflict detection above dispatch table
- Rep Overview panel for online operators with same conflict detection
- No-show evidence: up to 10 images, `ROLE-UserName` submitted-by label, clickable badge
- 7 new RBAC roles with granular permission-registry keys
- Agent reference shown in rep & driver portal job cards
- Production deployment: Nginx reverse proxy + SSL (Let's Encrypt) for both domains
- CORS fix for training domain

### v2.0.0
- Core system: traffic jobs, dispatch console, driver/rep/supplier portals
- JWT authentication with refresh token rotation
- Prisma schema with full location tree (Country → Airport → City → Zone → Hotel)
- Docker Compose full-stack infrastructure

---

## License

UNLICENSED - Proprietary software.

## Author

Developed by **Mohamed Gouda**
