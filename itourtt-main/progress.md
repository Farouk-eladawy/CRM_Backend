# Progress – iTour Transport & Traffic

Tracks completion status of every module and function in the project.

---

## Legend
- [ ] Not started
- [~] In progress
- [x] Completed

---

## Phase 1: Project Setup
- [x] Initialize monorepo structure
- [x] Docker + Docker Compose setup
- [x] PostgreSQL container configuration
- [x] Backend (NestJS) scaffolding
- [x] Frontend (Next.js) scaffolding
- [x] Prisma ORM setup & initial schema

## Phase 2: Database Schema (Prisma)
- [x] Location tree (countries, airports, cities, zones, hotels)
- [x] Vehicles & vehicle types
- [x] Drivers + driver-vehicle mapping
- [x] Reps
- [x] Agents + credit terms + documents + invoice cycles
- [x] Suppliers + supplier trip prices
- [x] Traffic jobs + flights + assignments
- [x] Finance tables (driver fees, rep fees, supplier costs)
- [x] Agent invoices + invoice lines + payments
- [x] Accounting tables (accounts, journal entries, journal lines)
- [x] Users + roles (RBAC)
- [x] Database migration applied

## Phase 3: NestJS Modules & Services
- [x] Auth module (JWT + refresh tokens)
- [x] Users & RBAC module
- [x] Locations module (full tree CRUD)
- [x] Vehicles module
- [x] Drivers module
- [x] Reps module
- [x] Agents module (CRUD + credit + documents)
- [x] Suppliers module
- [x] Traffic jobs module
- [x] Dispatch module
- [x] Finance module
- [x] Odoo export module (6 XLSX exports)
- [x] Reports module (4 report types)

## Phase 4: Dispatch API
- [x] GET /dispatch/day – fetch day view
- [x] POST /dispatch/assign – assign vehicle/driver/rep
- [x] PATCH /dispatch/reassign – reassign resources
- [x] DELETE /dispatch/unassign – remove assignment
- [x] GET /dispatch/available-vehicles – availability check
- [x] GET /dispatch/available-drivers – availability check
- [x] GET /dispatch/available-reps – availability check
- [x] Conflict validation logic (pax vs capacity, vehicle double-booking)

## Phase 5: Dispatch UI
- [x] DispatchPage layout (split ARR/DEP)
- [x] DateToolbar component
- [x] ArrivalGrid component
- [x] DepartureGrid component
- [x] Color-coded status rows
- [x] SummaryFooter component (sticky footer with job stats, pax count, assignment rate)
- [x] Inline editing + keyboard navigation (click-to-edit cells, Tab/Arrow keys, Enter/Escape)
- [x] Optimistic UI with rollback (instant state update, auto-rollback on API failure)

## Phase 6: Finance & Odoo Exports
- [x] Post job financials
- [x] Job P&L calculation
- [x] Agent invoice generation
- [x] Driver trip fee calculation
- [x] Rep fee calculation
- [x] Supplier cost tracking
- [x] Odoo customer export (XLSX)
- [x] Odoo supplier export (XLSX)
- [x] Odoo invoice export (XLSX)
- [x] Odoo vendor bill export (XLSX)
- [x] Odoo payment export (XLSX)
- [x] Odoo journal entry export (XLSX)

## Phase 7: Reporting
- [x] Daily dispatch summary (API + UI)
- [x] Driver trip report (API + UI)
- [x] Agent statement (API + UI)
- [x] Revenue report (API + UI)

## Phase 8: UI Pages
- [x] Login page (glass effect, black abstract bg)
- [x] Dashboard
- [x] Locations management
- [x] Vehicles management
- [x] Drivers management
- [x] Reps management
- [x] Agents management
- [x] Suppliers management
- [x] Traffic jobs management
- [x] Finance overview (invoices table + 6 Odoo export cards)
- [x] Reports page (4 tabbed reports with date filters)
- [x] Dispatch console

## Phase 9: System Parameters
### Database
- [x] SystemSettings model (theme, colors, font, language)
- [x] CompanySettings model (name, logo, favicon, report headers/footers)
- [x] RolePermission model (role × module → canView/canCreate/canEdit/canDelete)
- [x] Migration `20260131173559_add_settings_and_permissions` applied

### Backend: Settings Module
- [x] SettingsModule registered in AppModule (15 modules total)
- [x] GET /settings/system – fetch system settings (theme, colors, font, language)
- [x] PATCH /settings/system – upsert system settings (ADMIN)
- [x] GET /settings/company – fetch company settings
- [x] PATCH /settings/company – upsert company settings (ADMIN)
- [x] POST /settings/company/logo – upload logo file (multer, ADMIN)
- [x] POST /settings/company/favicon – upload favicon file (multer, ADMIN)
- [x] Static file serving for /uploads directory

### Backend: Role Permissions
- [x] RolePermissionsService (findAll, findByRole, bulkUpdate, seedDefaults)
- [x] GET /users/permissions – full permission matrix (all roles × 11 modules)
- [x] PUT /users/permissions – bulk update permissions (ADMIN)
- [x] GET /users/permissions/:role – permissions for specific role
- [x] GET /users/permissions/seed – seed default permissions (55 rows: 5 roles × 11 modules)
- [x] Default permission seeds (ADMIN=full, DISPATCHER/ACCOUNTANT/AGENT_MANAGER=role-specific, VIEWER=view-only)

### Frontend: Theme Provider
- [x] ThemeProvider context component (fetches settings, applies globally)
- [x] Dark/Light mode class toggle on <html>
- [x] Dynamic Google Font loading via <link> injection
- [x] CSS variable application (--primary-hex, --accent-hex, --font-geist-sans)
- [x] Language attribute on <html>
- [x] Dashboard layout wrapped with ThemeProvider

### Frontend: Styling Page
- [x] /dashboard/styling route
- [x] Dark/Light mode toggle (shadcn Switch)
- [x] Display Font picker (11 Google Fonts with preview)
- [x] Display Language selector (13 languages)
- [x] System Colors – Primary & Accent color pickers
- [x] Save Changes → PATCH /settings/system + ThemeProvider update

### Frontend: Company Page
- [x] /dashboard/company route
- [x] Company name input
- [x] Logo upload with 120×120 preview
- [x] Favicon upload with 48×48 preview
- [x] Report header & footer HTML textareas
- [x] Save Changes → PATCH /settings/company

### Frontend: Users Page
- [x] /dashboard/users route
- [x] Tab 1: Users table (name, email, role, status, created) + Add/Edit/Deactivate
- [x] Tab 2: Permission Matrix grid (5 roles × 11 modules × 4 flags) + Save/Seed buttons
- [x] Tab 3: User Roles reference cards (5 roles with descriptions)

### Sidebar
- [x] 3 new nav items under System Parameters (Styling, Company, Users)

### Infrastructure Fix
- [x] ESM/CJS compatibility fix – added "type": "module" to backend package.json

---

## Phase 10: Traffic Assign

### Summary

Redesign the "New Traffic Job" modal from a single form into a **two-tab dialog** (Online / B2B),
with expanded fields, searchable location dropdowns (airport/zone/hotel), split pax counts,
flight-specific conditional fields, extras checkboxes, and a new **Customer** entity for B2B bookings.

---

### 10.1 CURRENT STATE (What Exists)

**Traffic Job Modal** (`frontend/src/app/(dashboard)/dashboard/traffic-jobs/page.tsx` lines 342–522):
- Single form, no tabs
- Fields: Agent (required), Agent Ref (optional), Service Type (ARR/DEP/CITY),
  Date, Pax Count (single number), From Zone, To Zone, Hotel, Flight No, Carrier, Notes
- Zone-only dropdowns (no airport/hotel selection)
- No client name, no extras, no adult/child split

**Prisma TrafficJob model** (`backend/prisma/schema.prisma` lines 439–475):
- `agentId` (required FK → Agent)
- `paxCount` (single Int)
- `fromZoneId` / `toZoneId` (optional, zone-only FKs)
- `hotelId` (optional FK → Hotel)

**TrafficFlight model** (lines 477–491):
- `flightNo`, `carrier`, `terminal`, `arrivalTime`, `departureTime`

**No Customer model exists** – only Agent.

---

### 10.2 TARGET STATE (What We Are Building)

#### A. New Traffic Job Modal – Two Tabs

**Tab 1: Online**
| # | Field | Type | Required | Condition |
|---|-------|------|----------|-----------|
| 1 | Transfer Provider (Agent) | Select dropdown | Yes | — |
| 2 | Agent Ref | Text input | **Yes (Mandatory)** | — |
| 3 | Service Type | Select (Arrival / Departure / Excursion) | Yes | — |
| 4 | Service Date | Date picker | Yes | — |
| 5 | Adult Count | Number input | Yes | — |
| 6 | Child Count | Number input | Yes (default 0) | — |
| 7 | Origin | Searchable combobox (airports + zones + hotels) | Yes | — |
| 8 | Destination | Searchable combobox (airports + zones + hotels) | Yes | — |
| 9 | Arrival Flight Number | Text input | No | Service Type = Arrival |
| 10 | Flight Arrival Time | Time input | No | Service Type = Arrival |
| 11 | Flight Arrival Terminal | Text input | No | Service Type = Arrival |
| 12 | Pick Up Time | Time input | No | Service Type = Departure |
| 13 | Departure Flight Number | Text input | No | Service Type = Departure |
| 14 | Departure Flight Terminal | Text input | No | Service Type = Departure |
| 15 | Client Name (Lead Name) | Text input | No | — |
| 16 | Extras: Booster Seat | Checkbox | No | — |
| 17 | Extras: Baby Seat | Checkbox | No | — |
| 18 | Extras: Wheel Chair | Checkbox | No | — |

**Tab 2: B2B**
| # | Field | Type | Required | Condition |
|---|-------|------|----------|-----------|
| 1 | Transfer Customer | Select dropdown (from Customers list) | Yes | — |
| 2 | Service Type | Select (Arrival / Departure / Excursion) | Yes | — |
| 3 | Service Date | Date picker | Yes | — |
| 4 | Adult Count | Number input | Yes | — |
| 5 | Child Count | Number input | Yes (default 0) | — |
| 6 | Origin | Searchable combobox (airports + zones + hotels) | Yes | — |
| 7 | Destination | Searchable combobox (airports + zones + hotels) | Yes | — |
| 8 | Arrival Flight Number | Text input | No | Service Type = Arrival |
| 9 | Flight Arrival Time | Time input | No | Service Type = Arrival |
| 10 | Flight Arrival Terminal | Text input | No | Service Type = Arrival |
| 11 | Pick Up Time | Time input | No | Service Type = Departure |
| 12 | Departure Flight Number | Text input | No | Service Type = Departure |
| 13 | Departure Flight Terminal | Text input | No | Service Type = Departure |

**Key differences:** B2B tab does NOT have Agent Ref, Client Name, or Extras checkboxes.
B2B uses `customerId` instead of `agentId`.

#### B. New Customer Entity (for B2B)

A "Customer" represents another travel agency requesting our transfer service.
Separate from "Agent" which represents online transfer providers.

Customer fields:
- Legal Name (required)
- Trade Name
- Tax ID
- Address, City, Country
- Phone, Email
- Currency (EGP default)
- Credit Limit, Credit Days
- Contact Person Name
- isActive, audit fields, soft delete

Full CRUD management page at `/dashboard/customers`.

---

### 10.3 DETAILED IMPLEMENTATION PLAN

#### Step 1: Database Schema Changes

**File:** `backend/prisma/schema.prisma`

**1a. Add `LocationType` enum:**
```
enum LocationType {
  AIRPORT
  ZONE
  HOTEL
}
```

**1b. Add `BookingChannel` enum:**
```
enum BookingChannel {
  ONLINE
  B2B
}
```

**1c. Rename ServiceType enum value CITY → EXC (Excursion):**
- Option A: Rename enum value `CITY` → `EXC` (requires migration + data update for existing rows)
- Option B: Keep `CITY` internally, display as "Excursion" on frontend only (no migration needed)
- **Decision needed from user** – recommend Option B for safety unless clean rename is preferred.

**1d. Add `Customer` model:**
```prisma
model Customer {
  id            String    @id @default(uuid()) @db.Uuid
  legalName     String    @map("legal_name")
  tradeName     String?   @map("trade_name")
  taxId         String?   @map("tax_id")
  address       String?
  city          String?
  country       String?
  phone         String?
  email         String?
  contactPerson String?   @map("contact_person")
  currency      Currency  @default(EGP)
  creditLimit   Decimal?  @map("credit_limit") @db.Decimal(15,2)
  creditDays    Int?      @map("credit_days")
  isActive      Boolean   @default(true) @map("is_active")
  createdAt     DateTime  @default(now()) @map("created_at") @db.Timestamptz
  updatedAt     DateTime  @updatedAt @map("updated_at") @db.Timestamptz
  deletedAt     DateTime? @map("deleted_at") @db.Timestamptz

  trafficJobs   TrafficJob[]

  @@map("customers")
}
```

**1e. Modify `TrafficJob` model:**

New/changed fields:
```
  bookingChannel  BookingChannel  @default(ONLINE) @map("booking_channel")
  agentId         String?         @map("agent_id") @db.Uuid          // Now OPTIONAL (null for B2B)
  customerId      String?         @map("customer_id") @db.Uuid       // NEW – FK to Customer (for B2B)
  agentRef        String?         @map("agent_ref")                   // Mandatory for ONLINE (validated in service, not schema)
  clientName      String?         @map("client_name")                 // NEW – Lead name (Online only)
  adultCount      Int             @map("adult_count") @db.SmallInt    // NEW – replaces paxCount
  childCount      Int             @default(0) @map("child_count") @db.SmallInt  // NEW
  paxCount        Int             @map("pax_count") @db.SmallInt      // KEEP – auto-computed as adultCount + childCount
  originType      LocationType    @map("origin_type")                 // NEW
  originId        String          @map("origin_id") @db.Uuid          // NEW – polymorphic (airport/zone/hotel UUID)
  destinationType LocationType    @map("destination_type")             // NEW
  destinationId   String          @map("destination_id") @db.Uuid     // NEW – polymorphic
  fromZoneId      String?         @map("from_zone_id") @db.Uuid       // KEEP – auto-resolved for pricing
  toZoneId        String?         @map("to_zone_id") @db.Uuid         // KEEP – auto-resolved for pricing
  boosterSeat     Boolean         @default(false) @map("booster_seat")  // NEW
  babySeat        Boolean         @default(false) @map("baby_seat")     // NEW
  wheelChair      Boolean         @default(false) @map("wheel_chair")   // NEW
  pickUpTime      DateTime?       @map("pick_up_time") @db.Timestamptz  // NEW – for Departure type
```

Remove: `hotelId` (subsumed by origin/destination system)

Add relation: `customer Customer? @relation(fields: [customerId], references: [id])`

Add index: `@@index([customerId])`

**1f. Zone auto-resolution logic (in service, not schema):**
- If originType = ZONE → fromZoneId = originId
- If originType = HOTEL → lookup hotel.zoneId → fromZoneId = hotel.zoneId
- If originType = AIRPORT → fromZoneId = null (airport doesn't map to a single zone)
- Same logic for destination → toZoneId

**1g. Run Prisma migration:**
- `npx prisma migrate dev --name traffic_job_redesign_and_customers`
- Handle existing data: set `bookingChannel = ONLINE`, `adultCount = paxCount`, `childCount = 0`,
  `originType = ZONE`, `originId = fromZoneId`, `destinationType = ZONE`, `destinationId = toZoneId`
  for all existing rows

---

#### Step 2: Backend – Customer Module (NEW)

**Directory:** `backend/src/customers/`

**Files to create:**
- [ ] `customers.module.ts` – NestJS module
- [ ] `customers.controller.ts` – REST controller
- [ ] `customers.service.ts` – business logic
- [ ] `dto/create-customer.dto.ts` – validation DTO
- [ ] `dto/update-customer.dto.ts` – partial update DTO

**API Endpoints:**
| Method | Path | Description | Roles |
|--------|------|-------------|-------|
| GET | `/customers` | List customers (paginated, search) | All authenticated |
| GET | `/customers/:id` | Get single customer | All authenticated |
| POST | `/customers` | Create customer | ADMIN, AGENT_MANAGER |
| PATCH | `/customers/:id` | Update customer | ADMIN, AGENT_MANAGER |
| DELETE | `/customers/:id` | Soft-delete customer | ADMIN |

Register module in `app.module.ts`.

---

#### Step 3: Backend – Location Search Endpoint (NEW)

**File:** `backend/src/locations/locations.controller.ts` & `locations.service.ts`

**New endpoint:**
```
GET /locations/search?q=<search_term>&types=airport,zone,hotel
```

Returns a flat list of location items:
```json
[
  { "id": "uuid", "type": "AIRPORT", "name": "Cairo International Airport", "code": "CAI", "path": "Egypt > Cairo International" },
  { "id": "uuid", "type": "ZONE",    "name": "Nasr City", "path": "Egypt > Cairo > Cairo > Nasr City" },
  { "id": "uuid", "type": "HOTEL",   "name": "Hilton Cairo", "path": "Egypt > Cairo > Cairo > Nasr City > Hilton Cairo" }
]
```

This powers the searchable combobox on the frontend. Searches across airport names/codes,
zone names, and hotel names. Returns grouped results with breadcrumb paths.

---

#### Step 4: Backend – Update Traffic Jobs Module

**Files to modify:**
- [ ] `backend/src/traffic-jobs/dto/create-job.dto.ts` – add all new fields, make agentId optional,
      add customerId, bookingChannel, adultCount, childCount, originType, originId, destinationType,
      destinationId, clientName, boosterSeat, babySeat, wheelChair, pickUpTime
- [ ] `backend/src/traffic-jobs/traffic-jobs.service.ts`:
  - Update `create()` to handle both ONLINE and B2B channels
  - Validate: ONLINE requires agentId + agentRef; B2B requires customerId
  - Auto-resolve fromZoneId/toZoneId from originType/originId & destinationType/destinationId
  - Compute paxCount = adultCount + childCount
  - Store pickUpTime on TrafficFlight or TrafficJob
  - Pass extras (boosterSeat, babySeat, wheelChair) through
- [ ] `backend/src/traffic-jobs/traffic-jobs.controller.ts` – no structural changes needed
- [ ] Update `jobInclude` to include customer relation

---

#### Step 5: Backend – Update Dispatch Module

**Files to modify:**
- [ ] `backend/src/dispatch/dispatch.service.ts`
- [ ] `backend/src/dispatch/dispatch.controller.ts`

**5a. General dispatch updates:**
- Update `getDayView()` query includes to load origin/destination info
- Update pax validation to use adultCount + childCount (or paxCount which is pre-computed)
- Include customer relation in query results

**5b. Rep Assignment Rules (NEW BUSINESS LOGIC):**

Current behavior (overly restrictive): a rep assigned to ANY job on a date is blocked from all
other jobs that day. This is wrong.

**New rules:**
1. A rep CAN be assigned to **multiple jobs** on the same day IF those jobs share the
   **same flight number AND same flight time**.
2. A rep CANNOT be assigned to a job with a **different flight number/time** UNLESS there is
   a **minimum 3-hour gap** between the new job's flight time and ALL existing assignments'
   flight times for that rep on that date.

**Validation logic for `assignJob()` and `reassignJob()` (when dto.repId is provided):**

```
function validateRepAvailability(repId, targetJob, targetFlight):
  1. Fetch all active assignments for this repId on targetJob.jobDate
     (where job status NOT IN ['CANCELLED', 'COMPLETED'] and job.deletedAt IS NULL)
     Include each assignment's trafficJob + trafficJob.flight

  2. If no existing assignments → ALLOW (rep is free)

  3. For each existing assignment:
     existingFlight = assignment.trafficJob.flight

     a. If targetJob is ARR:
        targetFlightNo   = targetFlight.flightNo
        targetFlightTime = targetFlight.arrivalTime

     b. If targetJob is DEP:
        targetFlightNo   = targetFlight.flightNo
        targetFlightTime = targetFlight.departureTime (or pickUpTime)

     c. If existing job is ARR:
        existingFlightNo   = existingFlight.flightNo
        existingFlightTime = existingFlight.arrivalTime

     d. If existing job is DEP:
        existingFlightNo   = existingFlight.flightNo
        existingFlightTime = existingFlight.departureTime (or pickUpTime)

     e. SAME FLIGHT CHECK:
        If targetFlightNo == existingFlightNo AND targetFlightTime == existingFlightTime
        → ALLOW (same flight, rep can handle multiple jobs on same flight)
        → continue to next assignment

     f. DIFFERENT FLIGHT – 3-HOUR GAP CHECK:
        gap = |targetFlightTime - existingFlightTime|
        If gap < 3 hours → REJECT with error:
          "Rep is assigned to flight {existingFlightNo} at {existingFlightTime}.
           Minimum 3-hour gap required. Next available: {existingFlightTime + 3h}."
        → continue to next assignment

  4. If all existing assignments pass → ALLOW
```

**Update `getAvailableReps()` to be flight-aware:**

Current signature: `getAvailableReps(date: string)`
New signature: `getAvailableReps(date: string, jobId?: string)`

When `jobId` is provided:
- Load the target job's flight info (flightNo + arrivalTime/departureTime)
- For each active rep, check their assignments on this date
- Rep is available if:
  - Has NO active assignments on this date, OR
  - ALL existing assignments share the same flightNo + flightTime as the target job, OR
  - ALL existing assignments have a 3+ hour gap from the target job's flight time

When `jobId` is NOT provided (legacy/fallback):
- Return all active reps (no filtering, let the assign endpoint validate)

**Update dispatch controller:**
- `GET /dispatch/available-reps?date=YYYY-MM-DD&jobId=<uuid>` – add optional `jobId` query param

**Excursion (CITY) type handling:**
- **No rep assignment allowed on Excursion jobs.** Reps are only for ARR and DEP types.
- `assignJob()` and `reassignJob()` must REJECT `dto.repId` if job serviceType is CITY/Excursion
  with error: "Rep assignment is not available for Excursion jobs."
- `getAvailableReps()` should return empty list when target job is Excursion type.
- Dispatch UI: hide/disable rep cell for Excursion rows in the grid.

**Where rep validation runs:**
| Method | File | Lines (current) | Change |
|--------|------|-----------------|--------|
| `assignJob()` | dispatch.service.ts | 159–169 | Replace simple existence check with flight-aware validation |
| `reassignJob()` | dispatch.service.ts | 298–307 | Same validation when dto.repId is provided |
| `getAvailableReps()` | dispatch.service.ts | 454–483 | Rewrite with flight-aware filtering |

**5c. Driver Assignment Rules (NEW BUSINESS LOGIC):**

Current behavior (overly restrictive): a driver assigned to ANY job on a date is blocked from
all other jobs that day. No time-based logic.

**New rules:**
1. A driver can only handle **ONE job at a time** — unlike reps, drivers CANNOT share the same
   flight (one driver = one vehicle = one job).
2. After a job's flight time, the driver needs a **minimum 3-hour gap** before being available
   for another job on the same day.

**Key difference from reps:** Reps can share same-flight jobs. Drivers cannot — ever.

**Validation logic for `assignJob()` and `reassignJob()` (when dto.driverId is provided):**

```
function validateDriverAvailability(driverId, targetJob, targetFlight):
  1. Fetch all active assignments for this driverId on targetJob.jobDate
     (where job status NOT IN ['CANCELLED', 'COMPLETED'] and job.deletedAt IS NULL)
     Include each assignment's trafficJob + trafficJob.flight

  2. If no existing assignments → ALLOW (driver is free)

  3. Determine target job's reference time:
     - If targetJob is ARR → targetTime = targetFlight.arrivalTime
     - If targetJob is DEP → targetTime = targetFlight.departureTime (or pickUpTime)
     - If targetJob is Excursion → targetTime = null (see Excursion handling below)

  4. For each existing assignment:
     Determine existing job's reference time:
     - If existing job is ARR → existingTime = existingFlight.arrivalTime
     - If existing job is DEP → existingTime = existingFlight.departureTime (or pickUpTime)
     - If existing job is Excursion → existingTime = null

     a. If EITHER time is null (Excursion involved):
        → REJECT: "Driver is already assigned to job {existingRef} on this date."
        (Excursion has no time reference, so driver is blocked for the day)

     b. TIME GAP CHECK:
        gap = |targetTime - existingTime|
        If gap < 3 hours → REJECT with error:
          "Driver is assigned to job {existingRef} (flight {existingFlightNo} at
           {existingTime}). Minimum 3-hour gap required.
           Next available: {existingTime + 3h}."

  5. If all existing assignments pass → ALLOW
```

**Update `getAvailableDrivers()` to be time-aware:**

Current signature: `getAvailableDrivers(date: string)`
New signature: `getAvailableDrivers(date: string, jobId?: string)`

When `jobId` is provided:
- Load the target job's flight info
- For each active driver, check their assignments on this date
- Driver is available if:
  - Has NO active assignments on this date, OR
  - ALL existing assignments have a 3+ hour gap from the target job's flight time
- If target job is Excursion: only drivers with zero assignments on the date are available

When `jobId` is NOT provided (legacy/fallback):
- Return all active drivers (no filtering, let the assign endpoint validate)

**Update dispatch controller:**
- `GET /dispatch/available-drivers?date=YYYY-MM-DD&jobId=<uuid>` – add optional `jobId` query param

**Excursion (CITY) + Drivers:**
- Drivers CAN be assigned to Excursion jobs (unlike reps who cannot).
- Since Excursion has no flight time, the driver is blocked for the **full day** when on an
  Excursion job. Conversely, a driver already on a flight-based job cannot take an Excursion job
  (no way to guarantee 3-hour gap without a time reference).

**Where driver validation runs:**
| Method | File | Lines (current) | Change |
|--------|------|-----------------|--------|
| `assignJob()` | dispatch.service.ts | 148–157 | Replace simple existence check with time-aware validation |
| `reassignJob()` | dispatch.service.ts | 286–296 | Same validation when dto.driverId is provided |
| `getAvailableDrivers()` | dispatch.service.ts | 420–449 | Rewrite with time-aware filtering |

---

#### Step 6: Frontend – Searchable Location Combobox Component (NEW)

**File:** `frontend/src/components/location-combobox.tsx`

A reusable searchable combobox that:
- Fetches from `GET /locations/search?q=...` (debounced, 300ms)
- Displays results grouped by type (Airports / Zones / Hotels)
- Shows breadcrumb path for each item (e.g., "Egypt > Cairo > Nasr City")
- Type icons: Plane for airports, MapPin for zones, Building for hotels
- Returns `{ type: LocationType, id: string, name: string }` on selection
- Uses shadcn/ui Popover + Command (combobox pattern)

---

#### Step 7: Frontend – Redesign Traffic Job Modal

**File:** `frontend/src/app/(dashboard)/dashboard/traffic-jobs/page.tsx`

**Changes:**
- [ ] Replace single-form dialog with tabbed dialog (shadcn Tabs: "Online" / "B2B")
- [ ] Widen dialog to `max-w-2xl` to accommodate the richer form
- [ ] **Online Tab form fields:**
  - Transfer Provider (Agent) – existing Select dropdown
  - Agent Ref – Input (now mandatory, add asterisk)
  - Service Type – Select (Arrival / Departure / Excursion)
  - Service Date – date input
  - Adult Count – number input (min 1)
  - Child Count – number input (min 0, default 0)
  - Origin – LocationCombobox component
  - Destination – LocationCombobox component
  - Conditional Arrival fields (visible when type = Arrival):
    - Arrival Flight Number – text input
    - Flight Arrival Time – time input
    - Flight Arrival Terminal – text input
  - Conditional Departure fields (visible when type = Departure):
    - Pick Up Time – time input
    - Departure Flight Number – text input
    - Departure Flight Terminal – text input
  - Client Name (Lead Name) – text input
  - Extras group (3 checkboxes in a row): Booster Seat, Baby Seat, Wheel Chair

- [ ] **B2B Tab form fields:**
  - Transfer Customer – Select dropdown (fetched from GET /customers)
  - Service Type through Departure fields – same as Online
  - NO Agent Ref, Client Name, or Extras

- [ ] **Form state management:**
  - Add `activeTab` state ('online' | 'b2b')
  - Add states for all new fields (adultCount, childCount, originType, originId,
    destinationType, destinationId, clientName, boosterSeat, babySeat, wheelChair,
    pickUpTime, customerId, arrivalFlightNo, arrivalTime, arrivalTerminal,
    departureFlightNo, departureTerminal)
  - Update `resetForm()` to clear all new fields
  - Update `handleCreate()` to build correct payload based on active tab

- [ ] **Validation:**
  - Online: agentId + agentRef + origin + destination required
  - B2B: customerId + origin + destination required
  - Both: serviceType + serviceDate + adultCount required

- [ ] Update `TrafficJob` TypeScript interface to include new fields
- [ ] Update jobs table to show booking channel (Online/B2B badge) and customer name for B2B jobs

---

#### Step 8: Frontend – Customer Management Page (NEW)

**File:** `frontend/src/app/(dashboard)/dashboard/customers/page.tsx`

**Features:**
- [ ] Page header: "Customers" with "New Customer" button
- [ ] Search bar + active/inactive filter
- [ ] Customers table with columns:
  - Legal Name, Trade Name, Tax ID, Contact Person, Phone, Email, Currency, Credit Limit, Status, Actions
- [ ] Add Customer dialog with fields:
  - Legal Name (required), Trade Name, Tax ID, Address, City, Country,
    Phone, Email, Contact Person, Currency, Credit Limit, Credit Days
- [ ] Edit Customer (inline or dialog)
- [ ] Deactivate/Activate toggle
- [ ] Follows existing page patterns (same as Agents page structure)

---

#### Step 9: Frontend – Update Sidebar Navigation

**File:** `frontend/src/components/sidebar.tsx`

- [ ] Add "Customers" nav item under System Parameters group
- [ ] Icon: `Handshake` from lucide-react (or `Users2`)
- [ ] Path: `/dashboard/customers`
- [ ] Position: after "Agents" in the group

---

#### Step 10: Frontend – Update Dispatch Console

**File:** `frontend/src/app/(dashboard)/dashboard/dispatch/page.tsx`

- [ ] Update grid to show origin/destination names (resolved from type + name) instead of zone-only
- [ ] Show booking channel indicator (Online/B2B) in job rows
- [ ] Show customer name for B2B jobs (where agent name currently shows)
- [ ] Update pax display to show "Adults + Children" format or total
- [ ] Show extras icons (booster/baby/wheelchair) if applicable

---

#### Step 11: Ripple Effects – Other Modules

**Finance & Odoo exports:**
- [ ] Update Odoo customer export to include Customers (B2B) as res.partner entries
- [ ] Update invoice generation to support Customer invoices (not just Agent invoices)
- [ ] Verify paxCount references throughout finance module use adultCount + childCount correctly

**Reports:**
- [ ] Update agent statement to also support customer statements
- [ ] Update daily dispatch summary to show Online/B2B breakdown
- [ ] Verify pax count displays use adultCount + childCount

**Backend role permissions:**
- [ ] Add "customers" module to RolePermission seed defaults
- [ ] ADMIN: full access, AGENT_MANAGER: full access, others: view-only

---

### 10.4 DECISIONS (RESOLVED)

1. **ServiceType CITY → Excursion:** **DECIDED: Rename to EXCURSION.** Removed CITY from enum entirely. All code updated.

2. **Origin/Destination:** **DECIDED: 6 separate FK columns.** originAirportId, originZoneId, originHotelId, destinationAirportId, destinationZoneId, destinationHotelId — preserves referential integrity.

3. **Existing `hotelId` field:** **DECIDED: Keep deprecated.** Nullable FK preserved for backward compatibility.

4. **Customer invoicing:** **DECIDED: Reuse AgentInvoice.** Made agentId nullable, added customerId FK. Single invoice model for both agents and customers.

5. **Notes field:** **DECIDED: Keep on both tabs.** Notes available for both Online and B2B bookings.

6. ~~**Rep + Excursion jobs:**~~ **RESOLVED** – No rep assignment on Excursion jobs. Reps are ARR/DEP only.

---

### 10.5 FILE CHANGE SUMMARY

| Layer | File | Action |
|-------|------|--------|
| Schema | `backend/prisma/schema.prisma` | Modify (add Customer, LocationType, BookingChannel, update TrafficJob) |
| Migration | `backend/prisma/migrations/...` | New migration |
| Backend | `backend/src/customers/` (entire dir) | **Create** – module, controller, service, DTOs |
| Backend | `backend/src/locations/locations.controller.ts` | Modify (add search endpoint) |
| Backend | `backend/src/locations/locations.service.ts` | Modify (add search method) |
| Backend | `backend/src/traffic-jobs/dto/create-job.dto.ts` | Modify (new fields, optional agentId) |
| Backend | `backend/src/traffic-jobs/traffic-jobs.service.ts` | Modify (dual-channel create, zone resolution) |
| Backend | `backend/src/dispatch/dispatch.service.ts` | Modify (include customer, origin/dest, rep flight-aware validation) |
| Backend | `backend/src/dispatch/dispatch.controller.ts` | Modify (add jobId param to available-reps endpoint) |
| Backend | `backend/src/app.module.ts` | Modify (register CustomersModule) |
| Frontend | `frontend/src/components/location-combobox.tsx` | **Create** – searchable location picker |
| Frontend | `frontend/src/app/(dashboard)/dashboard/traffic-jobs/page.tsx` | Modify (complete modal redesign) |
| Frontend | `frontend/src/app/(dashboard)/dashboard/customers/page.tsx` | **Create** – customer management page |
| Frontend | `frontend/src/components/sidebar.tsx` | Modify (add Customers nav item) |
| Frontend | `frontend/src/app/(dashboard)/dashboard/dispatch/page.tsx` | Modify (origin/dest display, B2B support) |
| Backend | `backend/src/finance/` | Modify (Customer invoice support) |
| Backend | `backend/src/reports/` | Modify (Online/B2B breakdown) |
| Backend | `backend/src/export/` | Modify (Odoo Customer export) |

**Total: ~6 new files, ~12 modified files**

---

### 10.6 IMPLEMENTATION ORDER

1. Schema changes + migration (Step 1)
2. Customer backend module (Step 2)
3. Location search endpoint (Step 3)
4. Traffic jobs backend updates (Step 4)
5. Dispatch backend updates (Step 5)
6. Location combobox component (Step 6)
7. Traffic job modal redesign (Step 7)
8. Customer management page (Step 8)
9. Sidebar update (Step 9)
10. Dispatch console updates (Step 10)
11. Finance, reports, export ripple effects (Step 11)

---

### 10.7 TASK CHECKLIST

- [x] Add LocationType enum to schema
- [x] Add BookingChannel enum to schema
- [x] Add Customer model to schema
- [x] Update TrafficJob model (6 separate origin/dest FKs, optional agentId, customer FK, extras, pax split)
- [x] Create & run Prisma migration (schema synced via db push + baseline migration)
- [x] Create CustomersModule (module + controller + service + DTOs + price list + Excel import/export)
- [x] Register CustomersModule in AppModule
- [x] Add GET /locations/search endpoint
- [x] Update CreateJobDto with all new fields (6 FK fields, booking channel, extras, pax split)
- [x] Update TrafficJobsService.create() for dual-channel + zone resolution from separate FKs
- [x] Update TrafficJobsService.findAll/findOne includes (6 origin/dest relations)
- [x] Update DispatchService includes for new fields (origin/dest + customer)
- [x] Implement rep flight-aware validation in assignJob()
- [x] Implement rep flight-aware validation in reassignJob()
- [x] Rewrite getAvailableReps() with flight-aware filtering + jobId param
- [x] Update GET /dispatch/available-reps endpoint to accept jobId query param
- [x] Block rep assignment on Excursion jobs (backend reject + frontend hide rep cell)
- [x] Implement driver time-aware validation in assignJob() (3-hour gap rule)
- [x] Implement driver time-aware validation in reassignJob()
- [x] Rewrite getAvailableDrivers() with time-aware filtering + jobId param
- [x] Update GET /dispatch/available-drivers endpoint to accept jobId query param
- [x] Create LocationCombobox frontend component
- [x] Redesign traffic job modal with Online/B2B tabs (separate FK fields, all 12 service types)
- [x] Create /dashboard/customers page (CRUD + price list management + Excel template)
- [x] Add Customers to sidebar navigation
- [x] Update dispatch console grid for new fields (excursion tab, customer display)
- [x] Update finance module for Customer invoicing (AgentInvoice reused with nullable agentId + customerId)
- [x] Update reports for Online/B2B breakdown (nullable agent, customer fallback)
- [x] Update Odoo exports for Customer data (nullable agent, customer fallback in partner name)
- [x] Add "customers" to role permission seeds
- [x] Rename ServiceType CITY → EXCURSION across entire codebase (schema, backend, frontend)
- [x] Update frontend types (ServiceType, TrafficJob, AgentInvoice, DispatchDayView)
- [x] Update rep portal pages (CITY → EXCURSION in service type colors)

## Phase 11: Driver Extranet + No Show Evidence

### 11.1 Schema Changes
- [x] Add DRIVER to UserRole enum
- [x] Add userId (optional, unique FK → User) to Driver model
- [x] Add driver relation on User model
- [x] Create DriverNotification model (mirrors RepNotification)
- [x] Create NoShowEvidence model (trafficJobId, 2 image URLs, GPS lat/lng, Google Maps link, submittedBy)
- [x] Add reverse relations on TrafficJob (driverNotifications, noShowEvidence)
- [x] Run prisma db push + regenerate client

### 11.2 Backend – Auth + Driver Account Management
- [x] Update auth service: resolve driverId on DRIVER login
- [x] Add createUserAccount() to drivers service (mirrors reps pattern)
- [x] Add resetPassword() to drivers service
- [x] Add POST /drivers/:id/account endpoint
- [x] Add PATCH /drivers/:id/account/password endpoint
- [x] Include user relation in drivers findOne

### 11.3 Backend – Driver Portal Module (NEW)
- [x] Create driver-portal.module.ts
- [x] Create driver-portal.service.ts (resolveDriverId, getMyJobs, getJobHistory, updateJobStatus, submitNoShow, notifications CRUD, getProfile)
- [x] Create driver-portal.controller.ts (8 endpoints: jobs, history, status, no-show, notifications x3, profile)
- [x] Register DriverPortalModule in app.module.ts
- [x] File upload support for no-show images (Multer, /uploads/no-show/)

### 11.4 Backend – No Show Evidence on Rep Portal
- [x] Add submitNoShow() to rep-portal.service.ts
- [x] Add POST /rep-portal/jobs/:jobId/no-show endpoint with FilesInterceptor
- [x] Remove NO_SHOW from simple status update (force evidence endpoint)
- [x] Add file upload support to rep-portal controller

### 11.5 Frontend – Types & Login
- [x] Add DRIVER to UserRole type
- [x] Add driverId to AuthUser interface
- [x] Update login page redirect: DRIVER → /driver

### 11.6 Frontend – NoShowEvidenceDialog (shared component)
- [x] Create no-show-evidence-dialog.tsx
- [x] Two file inputs with camera capture (accept="image/*" capture="environment")
- [x] Image preview thumbnails
- [x] GPS capture via navigator.geolocation.getCurrentPosition on dialog open
- [x] Google Maps link display
- [x] Permission denied / timeout error handling
- [x] Submit as FormData to portal-specific endpoint

### 11.7 Frontend – Driver Portal Pages (NEW)
- [x] Create (driver-portal)/layout.tsx (auth guard for DRIVER role, nav, notifications polling)
- [x] Create (driver-portal)/driver/page.tsx (today's jobs, active/completed sections, Complete/No Show/Cancel actions, notifications panel)
- [x] Create (driver-portal)/driver/history/page.tsx (date picker, trip fee history, total fees)
- [x] No Show button opens NoShowEvidenceDialog (not simple confirm)

### 11.8 Frontend – Rep Portal Modification
- [x] Import and use NoShowEvidenceDialog in rep/page.tsx
- [x] No Show button now opens evidence dialog instead of simple confirmation
- [x] Complete and Cancel still use simple confirmation dialog

---

## Phase 12: Vehicle Compliance & Deposits
- [x] Vehicle compliance tracking (insurance, license, inspection dates)
- [x] Upsert vehicle compliance DTO
- [x] Vehicle detail page (`/dashboard/vehicles/[id]`)
- [x] New vehicle form page (`/dashboard/vehicles/new`)
- [x] Deposit payment DTO and endpoint

## Phase 13: Client Sign PDF Generation
- [x] Install pdf-lib in backend
- [x] `generateClientSigns()` method in ExportService (landscape A4 PDF)
- [x] Company logo at 90% page width in PDF
- [x] "Mr/Mrs" text + large bold client name per page
- [x] GET /export/odoo/client-signs?date= endpoint
- [x] Print Signs button on traffic jobs page (generates for tomorrow's date)
- [x] i18n translations for sign generation (en + ar)

## Phase 14: WYSIWYG Report Header/Footer Editor
- [x] Install TipTap packages (@tiptap/react, starter-kit, text-align, underline, image, table extensions)
- [x] Create RichTextEditor component (`frontend/src/components/rich-text-editor.tsx`)
- [x] Toolbar: Bold, Italic, Underline, H1/H2/H3, Bullet/Ordered List, Align L/C/R
- [x] Table support (insert, add/delete rows/columns, delete table)
- [x] Company logo insertion with size slider (10-100%)
- [x] Shortcode buttons: {{reportName}}, {{dateTime}}, {{user}}
- [x] Replace raw HTML textareas in company settings page
- [x] SSR fix: `immediatelyRender: false` for Next.js compatibility
- [x] Updated i18n: removed "HTML" from report header/footer labels

## Phase 15: Reports Page UI Improvements
- [x] Compact stat cards (reduced padding, font sizes)
- [x] All stats in single row (grid layout, equal width)
- [x] Service type cards on same line as stats (8-column grid)
- [x] Fixed duplicate React key warning in compliance table

## Phase 16: V2 B2B AI-Powered Job Import System

### Overview
Operators receive traffic job files from B2B customers in various formats (PDF, Excel, image screenshots). Previously, operators had to manually re-type every job. This feature adds AI-powered document parsing using Google Gemini to extract jobs automatically, with human review before import.

### 16.1 Database
- [x] Add `CustomerImportTemplate` model (stores sample templates per customer/service type)
- [x] Add `JobImportLog` model (audit trail for import sessions)
- [x] Add `importTemplates` reverse relation on Customer model
- [x] Run prisma db push to create new tables

### 16.2 Backend – Import Templates Module (`backend/src/import-templates/`)
- [x] Create import-templates.module.ts
- [x] Create import-templates.controller.ts (GET list, POST upload, DELETE)
- [x] Create import-templates.service.ts (upsert, Excel sample extraction)
- [x] Create dto/create-template.dto.ts
- [x] Multer file upload with disk storage to `uploads/templates/`
- [x] Upsert behavior (one template per customer + service type)

### 16.3 Backend – AI Parser Module (`backend/src/ai-parser/`)
- [x] Create ai-parser.module.ts
- [x] Create ai-parser.controller.ts (POST /ai-parser/extract-jobs)
- [x] Create ai-parser.service.ts with Google Gemini 2.5 Flash integration
- [x] Support PDF, Excel (.xlsx/.xls), and image files (.png/.jpg)
- [x] Deterministic location matching against database (airports, zones, hotels)
- [x] Template context used as few-shot examples for better accuracy
- [x] ~~Auto-creation of missing locations~~ (removed — replaced by inline creation in LocationCombobox)
- [x] AI prompt extracts location type hints and zone hints for matching
- [x] AI prompt extracts customerJobId (customer booking references) from documents

### 16.4 Backend – Bulk Create Endpoint
- [x] Create dto/bulk-create-jobs.dto.ts
- [x] Add POST /traffic-jobs/bulk endpoint
- [x] Add bulkCreate() service method (iterative, partial success allowed)

### 16.5 Backend – Permissions
- [x] Add `customers.detail.importTemplates` (upload, delete) to permission registry
- [x] Add `traffic-jobs.b2b.importJobs` to permission registry
- [x] Mirror permission changes in frontend registry

### 16.6 Backend – Module Registration
- [x] Register ImportTemplatesModule in app.module.ts
- [x] Register AiParserModule in app.module.ts

### 16.7 Frontend – Import Template Manager (`frontend/src/components/import-template-manager.tsx`)
- [x] Grid showing templates per service type with file type icons
- [x] Upload dialog with service type dropdown + file picker
- [x] Delete functionality
- [x] Empty state message

### 16.8 Frontend – Customer Detail Integration
- [x] Add "Import Templates" tab to customer detail page (third tab)

### 16.9 Frontend – B2B Job Import Modal (`frontend/src/components/b2b-job-import-modal.tsx`)
- [x] Step 1: Select customer + upload file + extract jobs via AI
- [x] Step 2: Review & edit extracted jobs in editable table with confidence scoring
- [x] Step 3: Confirm import + view results
- [x] Inline editing with LocationCombobox for location correction
- [x] Confidence badges (green >= 80%, yellow 50-80%, red < 50%)
- [x] Row selection for partial import

### 16.10 Frontend – B2B Page Integration
- [x] Add "Import Jobs" button to B2B traffic jobs toolbar
- [x] Wire up B2BJobImportModal with customer list and refresh callback

### 16.11 Frontend – i18n
- [x] Add English translations for importTemplates.* and jobImport.* keys
- [x] Add Arabic translations for importTemplates.* and jobImport.* keys

### 16.12 Infrastructure
- [x] Add GEMINI_API_KEY to docker-compose.yml backend environment
- [x] Configure Gemini API key in backend/.env and root .env
- [x] Docker rebuild and deployment

## Phase 17: Production Deployment & Hardening

### 17.1 Deployment
- [x] Create deploy.md with 4-step VPS deployment commands
- [x] Fix production path from `/root/iTourTT` to `/opt/iTourTT`

### 17.2 Infrastructure Fixes
- [x] Fix 502 Bad Gateway: reconnect orphan nginx container to docker-compose network
- [x] Fix `/uploads/` serving: proxy through backend instead of local nginx alias
- [x] Fix CORS: use relative API URLs (`NEXT_PUBLIC_API_URL` empty for production)
- [x] Fix CORS: add `CORS_ORIGINS` env var for `https://fulvago.itourtt.cloud`
- [x] Fix 504 Gateway Timeout: increase nginx `proxy_read_timeout` to 300s for AI parser
- [x] Fix frontend axios timeout: increase to 300s (5 min) for AI extraction

## Phase 18: Location Management Enhancements

### 18.1 Searchable Location Filter
- [x] Add search input to locations page with real-time tree filtering
- [x] Auto-expand matching branches when searching
- [x] Empty state for no search results
- [x] i18n support (English + Arabic)

### 18.2 Inline Location Creation (ERP-style)
- [x] Add "Add New Location" button to all LocationCombobox dropdowns
- [x] Modal dialog to create Hotel (under a zone) or Zone (under a city)
- [x] Pre-fill name from current search query
- [x] Auto-select newly created location after creation
- [x] Load location tree (zones/cities) dynamically when modal opens
- [x] i18n support (English + Arabic)

### 18.3 Remove Auto-Create from AI Parser
- [x] Remove `autoCreateMissingLocations()` method from ai-parser.service.ts
- [x] Remove `findBestZone()` helper method
- [x] AI parser now only matches existing locations (no side effects)

## Phase 19: B2B Customer Job ID

- [x] Add `customerJobId` column to TrafficJob schema (nullable string)
- [x] Add field to CreateJobDto and UpdateJobDto
- [x] Handle in traffic-jobs service (create, update, changedFields tracking)
- [x] Add Customer Job ID input to B2B form (Row 1, after Customer dropdown)
- [x] Add "Cust. Job ID" column to B2B jobs table
- [x] Include customerJobId in B2B search filter
- [x] Update AI parser prompt to extract customer booking references
- [x] Add customerJobId to B2B import modal (ParsedJob interface + payload)
- [x] Add i18n keys (English + Arabic)
- [x] Prisma client regenerated

---

## Version History

| Version | Date | Summary |
|---------|------|---------|
| v1.0.0 | 2026-02-18 | Production release — Phases 1-15 complete. Full transport system with dispatch, finance, Odoo exports, reports, driver/rep portals, vehicle compliance, WYSIWYG editor. |
| v2.0.0 | 2026-02-20 | AI-powered B2B job import (Gemini), inline location creation, Customer Job ID, production deployment hardening, location search filter. |
