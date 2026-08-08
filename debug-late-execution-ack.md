[OPEN] Debug Session: late-execution-ack

## Symptom
- User sees a successful completion message for invoice creation/template send.
- A later message then says: `تم وضع الطلب في مسار التنفيذ` with an `Execution ID`.
- Expected behavior: queue/enqueue acknowledgment should appear before execution, or not appear at all once success is already confirmed.

## Hypotheses
1. A delayed async acknowledgment from `manifest/outbox` is emitted after final success because completion state is not checked.
2. The same request flows through both direct interactive execution and background async execution, producing two lifecycle messages.
3. `pending_action` or workflow state remains active after template selection, causing a stale branch to enqueue later.
4. Duplicate manifest creation or duplicate outbox pickup triggers a late queue message with no new business result.
5. The queue acknowledgment is emitted unconditionally on enqueue, but enqueue itself happens in the wrong order after direct success.

## Evidence To Collect
- Where `تم وضع الطلب في مسار التنفيذ` is generated.
- Where invoice/template success messages are generated.
- Whether the same booking/request creates more than one manifest ID.
- Whether a stale pending action survives after template selection.

## Status
- Session initialized. No business-logic changes yet.

## Evidence Collected
- `runtime/pi_brain/users/u_admin/conversations/internal_assistant.jsonl`
  - user `اعمل فاتورة للحجز 546980816555`
  - assistant invoice review / approval flow
  - user `نعم`
  - assistant `تم إنشاء الفاتورة بنجاح`
  - user `1`
  - assistant `تم التنفيذ بنجاح`
  - user `رقم الهاتف`
  - assistant `تم وضع الطلب في مسار التنفيذ. Execution ID: man_b094ec94`
- Therefore the late queue message was triggered by a **new user message** (`رقم الهاتف`) and not by the prior template-send success branch.

## Hypothesis Status
1. Delayed async ack after final success because completion state not checked -> Rejected for this incident.
2. Same request executed by both direct and background paths -> Rejected for this incident.
3. Stale pending_action after template selection -> Rejected by conversation trace; success branch cleared and completed.
4. Duplicate manifest / duplicate pickup -> No evidence for this incident.
5. New follow-up message was classified into `agentic_orchestrator`, which queued a manifest instead of resolving the contact request directly from open case context -> Confirmed.

## Root Cause
- After the successful template send, the user's new follow-up `رقم الهاتف` was treated as a new `agentic_orchestrator` request.
- The open booking context `546980816555` was preserved, so the agentic branch queued a manifest and returned `Execution ID: man_b094ec94`.
- This created the impression that the original invoice/send flow had regressed to queued execution, while in reality it was a separate follow-up request.

## Additional Runtime Evidence
- In a fresh session, a clear executable request `اعمل فاتورة للحجز 546980816555` still entered the guided mediator menu.
- When the user refined the request with another explicit command `اعمل فاتورة 120 يورو للحجز 546980816555`, the guided menu treated it as an invalid option instead of a refined request.
- This confirms a second mediation failure: the guided layer was trapping explicit requests and free-form corrections instead of reinterpreting them.

## Fix Applied
- Skip the guided mediator menu for explicit direct intents when the request already includes a lookup/reference context.
- While inside the guided mediator menu, any free-form user reply is now treated as a refined/new request and reinterpreted immediately instead of being rejected as an invalid numeric choice.
