# iTour Transport & Traffic – Database Schema

## Global Rules
- PostgreSQL + Prisma ORM
- UUID primary keys
- created_at / updated_at / deleted_at
- Timezone: Africa/Cairo
- Financial tables are immutable after posting

## Location Tree
Country → Airport → City → Zone → Hotel

Tables:
- countries
- airports (country_id)
- cities (airport_id)
- zones (city_id)
- hotels (zone_id)

Zones are the pricing and routing unit.

## Vehicles & Operations
- vehicle_types (seat_capacity)
- vehicles (plate_number, vehicle_type_id, ownership)
- drivers (mobile_number)
- driver_vehicle (many-to-many)
- reps (assigned_zones)

## Agents
- agents (legal_name, address, currency)
- agent_documents
- agent_credit_terms (credit_limit, credit_days)
- agent_invoice_cycles

## Suppliers
- suppliers (full legal & tax profile)
- supplier_trip_prices (route, vehicle_type)

## Traffic Jobs
- traffic_jobs (internal_ref, agent_ref, service_type)
- traffic_flights (flight_no, carrier, terminal, time)
- traffic_assignments (vehicle, driver, rep)

## Finance
- driver_trip_fees
- rep_fees
- supplier_costs
- agent_invoices
- invoice_lines
- payments

## Accounting (Odoo Ready)
- accounts
- journal_entries
- journal_lines