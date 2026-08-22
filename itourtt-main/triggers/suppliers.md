# Trigger: Suppliers

## Summary

Enhance the Supplier module with per-supplier vehicle management, an Excel-like price list UI,
and cascading supplier-to-vehicle selection in the Dispatch console.

---

## Requirements

1. **Supplier Vehicles** - Each supplier manages their own fleet of vehicles (same as the
   global Vehicles page, but scoped per supplier and **without the Compliance tab**).
2. **Supplier Price List** - Each supplier has their own price list (same structure as Customer
   price list) with an **Excel-like editable grid** instead of form fields.
3. **Dispatch Cascade** - In the Dispatch console, the dispatcher must first choose a Supplier,
   then the available vehicles dropdown filters to only that supplier's vehicles.
4. **Price List UI Overhaul** - Both Supplier and Customer price list UIs should use an Excel-like
   inline-editable grid (not individual form fields).

---

## Phase 1: Supplier Detail Page with Tabs

### Current State
- `/dashboard/suppliers` is a flat table with create/edit dialogs and account management.
- Clicking a supplier has no detail page (no `/dashboard/suppliers/[id]`).

### Changes

**Create** `frontend/src/app/(dashboard)/dashboard/suppliers/[id]/page.tsx`

Tabbed layout with 3 tabs:

#### Tab 1: Overview
- Read-only display of supplier info (legal name, trade name, tax ID, address, phone, email).
- Account management section (create account / reset password) - move from list page dialogs.

#### Tab 2: Vehicles
- Reuse the same pattern from the global Vehicles page (`/dashboard/vehicles`).
- Show only vehicles where `vehicle.supplierId === supplier.id`.
- Support: create, edit, delete, status toggle, import/export Excel.
- **Exclude the Compliance tab** from the vehicle edit sub-page.
- Vehicle create/edit form fields: plate number, vehicle type, ownership, color, car brand,
  car model, make year, luggage capacity.
- When creating a vehicle here, auto-set `supplierId` to the current supplier.

#### Tab 3: Price List (Excel-like Grid)
- See Phase 2 below for the grid UI spec.

---

## Phase 2: Excel-like Price List UI

### Current Customer Price List Pattern (to replace)
The customer price list at `/dashboard/customers/[id]` currently uses:
- A form-based "Add Route" section (service type + from zone + to zone dropdowns).
- An inline editable table with vehicle type columns (Price + Tip sub-columns per vehicle type).
- Separate read-only "Current Prices" section below.

### New Excel-like Grid Design

Replace the current form-based approach with a single editable spreadsheet-style grid.

#### Grid Structure
| Service Type | From Zone | To Zone | {Vehicle Type 1} Price | {Vehicle Type 1} Tip | {Vehicle Type 2} Price | ... | Actions |
|---|---|---|---|---|---|---|---|

- **Columns** are dynamically generated from all active VehicleTypes.
- **Rows** represent route + service type combinations.
- **Cells** are directly editable (click to type, Tab to move between cells).
- Empty cells indicate no price set for that combination.

#### Behaviors
- **Add Row**: A "+" button at the bottom adds a new row with dropdowns for Service Type,
  From Zone, and To Zone. Once the route is selected, price cells become editable.
- **Delete Row**: Trash icon on each row removes all prices for that route.
- **Inline Editing**: Click any price/tip cell to edit. No modal, no separate form.
- **Keyboard Navigation**: Tab moves right, Shift+Tab moves left, Enter moves down,
  Escape cancels edit.
- **Dirty State**: Changed cells highlight with a subtle background color.
- **Bulk Save**: A single "Save All" button commits all changes in one API call.
- **Import/Export**: Keep existing Excel template download + file upload import.
- **No separate read-only section**: The grid IS the current state; edits happen in-place.

#### Apply to Both
- **Supplier Price List** (`/dashboard/suppliers/[id]` Tab 3) - uses `SupplierTripPrice` model.
- **Customer Price List** (`/dashboard/customers/[id]` Tab 2) - uses `CustomerPriceItem` model.
- Extract the grid into a shared component: `frontend/src/components/price-list-grid.tsx`.

---

## Phase 3: Backend Changes

### 3a. Supplier Vehicles Endpoints

Extend `backend/src/suppliers/suppliers.controller.ts`:

```
GET    /suppliers/:id/vehicles                    - List supplier's vehicles (paginated, filterable)
POST   /suppliers/:id/vehicles                    - Create vehicle under this supplier
PATCH  /suppliers/:id/vehicles/:vehicleId          - Update a supplier's vehicle
DELETE /suppliers/:id/vehicles/:vehicleId          - Soft-delete a supplier's vehicle
PATCH  /suppliers/:id/vehicles/:vehicleId/status   - Toggle vehicle active/inactive
GET    /suppliers/:id/vehicles/export/excel        - Export supplier's vehicles to Excel
GET    /suppliers/:id/vehicles/import/template     - Download import template
POST   /suppliers/:id/vehicles/import/excel        - Import vehicles from Excel
```

**Service logic:**
- All vehicle operations scoped to `supplierId`.
- Validate vehicle belongs to supplier before update/delete.
- Auto-set `supplierId` on create.
- Reuse existing vehicle validation logic (unique plate number, valid vehicle type, etc.).

### 3b. Supplier Price List Endpoints

Current `SupplierTripPrice` endpoints exist but are basic. Enhance to match customer pattern:

```
GET    /suppliers/:id/price-list                   - Get all price items (grouped by route)
POST   /suppliers/:id/price-list                   - Bulk upsert price items
DELETE /suppliers/:id/price-list/:priceItemId       - Delete a specific price item
GET    /suppliers/price-list/template               - Download Excel import template
POST   /suppliers/:id/price-list/import             - Import price list from Excel
```

**Schema change** - Add `serviceType` and `driverTip` fields to `SupplierTripPrice`:
```prisma
model SupplierTripPrice {
  id            String      @id @default(uuid())
  supplierId    String
  serviceType   ServiceType               // NEW - add service type
  fromZoneId    String
  toZoneId      String
  vehicleTypeId String
  price         Decimal     @db.Decimal(15, 2)
  driverTip     Decimal     @db.Decimal(15, 2) @default(0)  // NEW
  currency      Currency    @default(EGP)
  effectiveFrom DateTime?   @db.Date
  effectiveTo   DateTime?   @db.Date
  createdAt     DateTime    @default(now())
  updatedAt     DateTime    @updatedAt

  supplier    Supplier    @relation(fields: [supplierId], references: [id])
  fromZone    Zone        @relation("SupplierPriceFromZone", fields: [fromZoneId], references: [id])
  toZone      Zone        @relation("SupplierPriceToZone", fields: [toZoneId], references: [id])
  vehicleType VehicleType @relation(fields: [vehicleTypeId], references: [id])

  @@unique([supplierId, serviceType, fromZoneId, toZoneId, vehicleTypeId])
}
```

### 3c. Dispatch Changes

Modify `backend/src/dispatch/dispatch.service.ts`:

**`getAvailableVehicles(date, supplierId?)`**:
- Accept optional `supplierId` query parameter.
- When provided, filter vehicles to `WHERE vehicle.supplierId = supplierId`.
- When not provided, return all available vehicles (backward compatible).

**`assignJob()` / `reassignJob()`**:
- Validate that the selected vehicle belongs to the specified supplier.
- Store `supplierId` on the assignment if needed for reporting.

Modify `backend/src/dispatch/dispatch.controller.ts`:
```
GET /dispatch/available-vehicles?date=YYYY-MM-DD&supplierId=UUID
```

### 3d. Dispatch Endpoint: List Active Suppliers

```
GET /dispatch/available-suppliers   - List active suppliers with vehicle count
```

Returns: `{ id, legalName, tradeName, vehicleCount }[]`
(Only suppliers who have at least one active vehicle.)

---

## Phase 4: Frontend Dispatch Changes

### Current Flow
1. Click vehicle cell in dispatch grid.
2. Dropdown shows ALL available vehicles for the day.
3. Select vehicle, assignment is created.

### New Flow
1. Click vehicle cell in dispatch grid.
2. **Step 1**: Dropdown/combobox shows available suppliers (only those with active vehicles).
3. **Step 2**: Once supplier is selected, a second dropdown shows only that supplier's
   available vehicles for the day.
4. Select vehicle, assignment is created as normal.

### UI Implementation
In `EditableVehicleCell` component (`dispatch/page.tsx`):
- Replace the single vehicle `<Select>` with a two-step cascading select:
  - First select: Supplier (combobox with search).
  - Second select: Vehicle (filtered by selected supplier + day availability).
- If a vehicle is already assigned, show both the supplier name and vehicle plate.
- Allow clearing supplier to re-select.

### State Changes
- Add `suppliers` to the dispatch page state (fetched on page load).
- `availableVehicles` becomes filtered by selected supplier.
- Track `selectedSupplierId` per editing cell.

---

## Phase 5: Shared Price List Grid Component

### Component: `frontend/src/components/price-list-grid.tsx`

```typescript
interface PriceListGridProps {
  entityId: string;                    // supplierId or customerId
  entityType: 'supplier' | 'customer';
  priceItems: PriceItem[];
  vehicleTypes: VehicleType[];
  zones: Zone[];
  serviceTypes: ServiceType[];
  onSave: (items: PriceItem[]) => Promise<void>;
  onDelete: (itemId: string) => Promise<void>;
  onImport: (file: File) => Promise<void>;
  onExportTemplate: () => void;
  showDriverTip?: boolean;            // true for both supplier and customer
}
```

### Features
- Virtual scrolling for large datasets (react-virtual or similar).
- Sticky header row + sticky first 3 columns (service type, from zone, to zone).
- Cell-level dirty tracking with visual indicator.
- Undo per cell (Escape while editing).
- Copy/paste support for price cells.
- Column resize handles.

---

## File Change Summary

### New Files
```
frontend/src/app/(dashboard)/dashboard/suppliers/[id]/page.tsx        - Supplier detail (tabs)
frontend/src/components/price-list-grid.tsx                            - Shared Excel-like grid
```

### Modified Files
```
backend/prisma/schema.prisma                                          - Add serviceType + driverTip to SupplierTripPrice
backend/src/suppliers/suppliers.controller.ts                          - Add vehicle + price list endpoints
backend/src/suppliers/suppliers.service.ts                             - Add vehicle + price list service methods
backend/src/dispatch/dispatch.controller.ts                            - Add supplierId filter to available-vehicles
backend/src/dispatch/dispatch.service.ts                               - Filter vehicles by supplier
frontend/src/app/(dashboard)/dashboard/dispatch/page.tsx               - Cascading supplier → vehicle selection
frontend/src/app/(dashboard)/dashboard/suppliers/page.tsx              - Add "View" action → navigate to detail
frontend/src/app/(dashboard)/dashboard/customers/[id]/page.tsx         - Replace price list with shared grid
frontend/src/types/index.ts                                            - Update SupplierTripPrice type
frontend/src/lib/i18n.ts                                               - Add translations
```

### Prisma Migration
```
ALTER TABLE "SupplierTripPrice" ADD COLUMN "serviceType" "ServiceType";
ALTER TABLE "SupplierTripPrice" ADD COLUMN "driverTip" DECIMAL(15,2) DEFAULT 0;
ALTER TABLE "SupplierTripPrice" DROP CONSTRAINT IF EXISTS "SupplierTripPrice_supplierId_fromZoneId_toZoneId_vehicleTyp_key";
ALTER TABLE "SupplierTripPrice" ADD CONSTRAINT "SupplierTripPrice_unique" UNIQUE ("supplierId", "serviceType", "fromZoneId", "toZoneId", "vehicleTypeId");
```

---

## Execution Order

1. Schema migration (add fields to SupplierTripPrice)
2. Backend: Supplier vehicle endpoints
3. Backend: Enhanced supplier price list endpoints (bulk upsert, import/export)
4. Backend: Dispatch supplier filtering
5. Frontend: Shared price list grid component
6. Frontend: Supplier detail page (Overview + Vehicles + Price List tabs)
7. Frontend: Update customer detail page to use shared grid
8. Frontend: Dispatch cascading supplier → vehicle selection
9. Test end-to-end flow
