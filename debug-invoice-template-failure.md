# Debug Session: invoice-template-failure

Status: [OPEN]

Symptom:
- User asked: `546980816555 رقم الحجز برجاء انشاء فاتورة بقيمة 20 يورو وارسالها في قالب Opening`
- System asked for approval, then failed with:
  - `Meta WhatsApp 131047 Re-engagement message`
  - `Missing or invalid Amount/Currency`
  - Final invoice/send failure with `[ESCALATE]`

Scope:
- `ai_agent.py`
- Payment link creation flow
- Internal assistant / approval flow
- WhatsApp template send flow

Initial hypotheses:
- H1: The approval-to-execution flow drops or fails to persist `amount` and/or `currency` before calling `api_create_payment_link`.
- H2: The invoice creation path is mapping the booking record id where the payment API expects booking number or normalized booking payload, causing missing extracted finance fields.
- H3: The request says `Opening`, but the outbound WhatsApp sender is falling back to a freeform/session message path instead of a proper approved template path, triggering Meta `131047`.
- H4: Currency normalization for `يورو` is inconsistent, so the final payload reaches `api_create_payment_link` with an empty or unsupported currency token.
- H5: The system executes two partially independent actions, where invoice creation fails first and the message sender still attempts delivery with incomplete state.

Evidence to collect:
- Runtime payload entering approval state
- Runtime payload consumed after approval
- Runtime args entering `api_create_payment_link`
- Runtime branch used for WhatsApp delivery (`template` vs `session/freeform`)
- Final manifest / execution payload for invoice send

Plan:
1. Read current code paths around the reported stack points.
2. Add instrumentation only, with no business-logic changes.
3. Reproduce or inspect the next failing run.
4. Confirm or reject the hypotheses from evidence.
5. Apply the minimal fix only after evidence is clear.

Evidence summary:
- `create_invoice` pending actions store `custom_amount` and `custom_currency` at build time.
- Approval execution previously called `_execute_invoice_capability()` with only `action.custom_amount/custom_currency`, with no fallback to `simulate_result.amount/currency`.
- `/api/payments/create` and `_create_payment_link_for_record()` accept runtime `amount/currency` directly and do not require Airtable `Amount/Currency` to be pre-filled.
- Successful payment creation only wrote `Trip UUID`, `Stripe invoice`, and `Invoice Status` back to Airtable, leaving `Amount` and `Currency` stale or empty.

Confirmed root cause:
- The invoice flow had two gaps:
  1. `Amount/Currency` could be lost between approval preparation and execution if the pending action did not retain the direct custom fields.
  2. Even after successful creation, `Amount/Currency` were not persisted back to Airtable, causing downstream inconsistency.

Minimal fix applied:
- Added execution fallback from `simulate_result.amount/currency` when `custom_amount/custom_currency` are missing at approval execution time.
- Persist `Amount` and `Currency` into Airtable when invoice creation succeeds through both local execution and `/api/payments/create`.

Next step:
- Re-run the booking invoice scenario and compare `pre-fix` vs `post-fix` debug events before cleanup.

Post-fix observation 1:
- Symptom changed from `Missing or invalid Amount/Currency` to Airtable `422 INVALID_VALUE_FOR_COLUMN` on field `Currency`.
- This confirms the payment creation path advanced further and the next blocker was Airtable field parsing during persistence.

Post-fix adjustment 2:
- Updated invoice Airtable writes to use `typecast=True`, matching other schema-aware update paths in the project.
- Added a safe retry: if Airtable still rejects `Amount/Currency`, keep the invoice creation successful and persist the core invoice fields only (`Trip UUID`, `Stripe invoice`, `Invoice Status`) instead of failing the whole request.

Post-fix observation 2:
- Runtime debug log confirmed a separate failure mode where `/api/payments/create` received `record_id="546980816555"` instead of the Airtable record id `rec4mCX8CaQoQrXjI`.
- This produced Airtable `404 NOT_FOUND`, proving some manifest/executor paths pass Booking Number as `target_record`.

Post-fix adjustment 3:
- Hardened `background_task_engine.py` so `create_invoice` now resolves booking numbers to the correct Airtable `record_id` before calling `/api/payments/create`.
- The executor now uses the resolved Airtable record for both invoice creation and conversation lookup.
