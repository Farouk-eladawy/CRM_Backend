# Debug Session: internal-webhook-timeout

Status: OPEN

## Scope
- Improve internal WhatsApp webhook responsiveness so it returns HTTP 200 quickly.
- Preserve current business behavior and verify PI can still execute `update_fields` end-to-end on booking `123456test`.

## Symptoms
- Local E2E caller times out while posting to `/api/internal_notifications/whatsapp/webhook`.
- The system still eventually sends the WhatsApp reply, which suggests the request is processed synchronously and finishes after the client timeout.

## Initial Hypotheses
1. The webhook waits for the full PI generation path, including `query_ai()`, before returning HTTP 200.
2. The webhook also waits for outbound WhatsApp delivery via `_send_internal_whatsapp_response`, adding extra latency after PI generation.
3. A blocking lookup or schema-aware Airtable read for `123456test` happens inside the request thread and pushes the total duration past the client timeout.
4. The webhook path performs additional logging/session writes that are small individually but still occur synchronously before responding.
5. The timeout is partly client-side, but the server design still needs fast-ack behavior because synchronous processing makes E2E testing and webhook reliability fragile.

## Evidence Plan
- Instrument the webhook entry/exit and key sub-steps with timing markers.
- Reproduce one inbound internal webhook request.
- Compare pre-fix vs post-fix timing.

## Constraints
- No business-logic change before instrumentation evidence is collected.
- Cleanup only after explicit user confirmation.

## Evidence Collected
- Pre-fix local reproduction on the instrumented server at `:5002` returned HTTP `200` after about `22.535s`.
- Post-fix local reproduction with `fast-ack` returned HTTP `200` after about `0.025s`.
- This confirms the timeout symptom was caused by synchronous in-request processing before acknowledgment.

## Current Status
- Fast acknowledgment fix is implemented and verified locally.
- Follow-up E2E test for `update_fields` on booking `123456test` is still inconclusive:
  - stale `pending_action` was cleared successfully from `internal_assistant_session:ahmady`
  - a new internal WhatsApp update request returned `200` quickly
  - but no new `pending_action` / `workflow_state` was persisted within the observation window
- Working hypothesis now: background processing after `fast-ack` is not yet producing observable session mutation for the update flow, so a second bug or blind spot remains in the async path.
