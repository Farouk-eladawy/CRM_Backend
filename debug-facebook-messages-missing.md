[OPEN] Debug Session: facebook-messages-missing

## Symptom
- Some messages sent to the Facebook page do not appear in the CRM/system inbox.

## Hypotheses
- H1: The Facebook webhook event reaches `/webhook`, but the payload shape is not handled by the current parser, so the message is dropped before save.
- H2: The webhook event is accepted, but chat creation or message persistence fails later in the processing pipeline.
- H3: The message is saved, but UI filtering or channel/location assignment hides it from the visible inbox.
- H4: The message belongs to an event type such as `delivery`, `read`, `echo`, or a non-message callback, so no user-visible message record is created.
- H5: The system creates the chat/message, but another dedupe/lookup branch links it incorrectly and it appears under a different chat than expected.

## Evidence Plan
- Inspect latest `agent_log.txt` lines around recent Facebook webhook events.
- Correlate inbound `page` payloads with downstream save/link logs.
- Inspect the Messenger webhook handling code path without changing business logic.
- Only if evidence is insufficient, add instrumentation as the first code change.

## Status
- Initialized session.
- Evidence reviewed from `agent_log.txt`.
- Confirmed likely root cause: inline Facebook debug network calls inside `/webhook` were timing out and tripping the outer webhook exception handler before processing completed.
- Minimal fix applied: removed the three inline debug network calls from the Messenger webhook path in `ai_agent.py`.
- Awaiting post-fix verification after backend restart.

## Evidence Summary
- Inbound Facebook `page` events with `postback` and `message.text` were present in logs.
- The same processing window logged `Error processing webhook: <urlopen error timed out>`.
- The timeout source matched inline `urllib.request.urlopen(... timeout=2)` debug calls embedded directly in the Messenger webhook branch.
- Post-fix verification exposed a second timeout source inside `_resolve_facebook_sender_name()` with a full traceback pointing to inline debug `urlopen(...)` calls there as well.
- Second minimal fix applied: removed all remaining inline Facebook debug network calls from `_resolve_facebook_sender_name()`.
