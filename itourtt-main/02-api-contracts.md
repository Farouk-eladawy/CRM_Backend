# iTour Transport & Traffic – API Contracts

## Authentication
POST /auth/login
POST /auth/refresh

## Master Data
GET /locations/tree
GET /zones/{id}/hotels

## Agents
POST /agents
GET /agents/{id}
PUT /agents/{id}/credit
POST /agents/{id}/documents

## Traffic Jobs
POST /traffic/jobs
GET /traffic/jobs/{id}
PATCH /traffic/jobs/{id}/status

## Dispatch Console
GET /dispatch/day?date=YYYY-MM-DD
POST /dispatch/assign

Returns:
- Arrival jobs
- Departure jobs
- Assignments
- Availability & conflicts

## Finance
POST /finance/post-job
GET /finance/job/{id}/pl

## Odoo Export
GET /export/odoo/customers
GET /export/odoo/invoices
GET /export/odoo/vendor-bills
GET /export/odoo/journals