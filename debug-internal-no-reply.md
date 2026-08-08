[OPEN] Debug Session: internal-no-reply

## Symptom
- User sends internal WhatsApp message: "هاتلي تذكرة الطيران اللي علي الحجز ده 546980816555"
- No reply appears to user.

## Expected
- Bot replies with either:
  - attachments/tickets result (if allowed), or
  - "hidden by permissions" message (if not allowed), or
  - explicit error with [ESCALATE] (never silent).

## Hypotheses
1) Webhook not received / server not running: message never reaches backend.
2) Actor not resolved / permissions: request rejected silently due to actor mapping or allowIntents.
3) Handler throws exception before sending: message processed but send path fails.
4) Reply generated but sending to Evolution fails: outbox pending or delivery error.
5) Debounce/state: message stuck in pending timer/session state and never flushed.

## Evidence Plan
- Check runtime conversation JSONL for presence of the message and any subsequent reply.
- Check server logs (if available) for webhook receipt and response send attempts/errors.
- Inspect SQLite for pending outbox/queue items related to this actor/chat.

