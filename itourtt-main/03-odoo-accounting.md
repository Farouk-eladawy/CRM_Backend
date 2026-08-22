# iTour Transport & Traffic – Odoo Accounting Compatibility

## Core Rule
No customization on Odoo side.

## Mapping

iTour → Odoo
- Agent → res.partner
- Supplier → res.partner
- Invoice → account.move (out_invoice)
- Vendor Bill → account.move (in_invoice)
- Payment → account.payment
- Tax → account.tax

## Export Files
- odoo_customers.xlsx
- odoo_suppliers.xlsx
- odoo_customer_invoices.xlsx
- odoo_vendor_bills.xlsx
- odoo_payments.xlsx
- odoo_journal_entries.xlsx

## Invoice Columns
- partner_name
- invoice_date
- due_date
- currency
- account_code
- tax_code
- amount
- external_reference