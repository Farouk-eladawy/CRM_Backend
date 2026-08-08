# Debug Session: internal-worker-timeout

Status: [OPEN]

## Symptom
- Internal WhatsApp assistant worker crashes with `urllib.error.URLError: <urlopen error timed out>`.
- User receives fallback: `حصل خطأ داخلي أثناء معالجة طلبك. [ESCALATE]`.

## Expected
- The worker should complete processing or fail gracefully with a precise stage-aware message.
- The timeout source should be observable: debug server call, internal webhook call, outbound WhatsApp send, or another `urlopen` dependency.

## Hypotheses
1. A debug/instrumentation `urlopen()` call is still present in the runtime path and times out when no debug server is reachable.
2. The worker is blocking on an outbound internal HTTP call (webhook/send/reply) that lacks a safe timeout budget or retry policy.
3. The worker enters a slow PI/orchestrator path, then a later `urlopen()` helper times out after the request is already delayed.
4. Exception handling around the worker is too coarse, so a non-critical telemetry timeout escalates as a full worker crash.
5. Multiple sequential network calls in the same worker cause cumulative latency, and the failing `urlopen()` is only the first visible error.

## Evidence Plan
- Identify every `urlopen(` reachable from `_process_internal_whatsapp_message_async`.
- Instrument the worker entry, pre/post each `urlopen` stage, and final exception path.
- Reproduce one failing internal message and compare stage timings.
- Confirm whether the timeout is caused by debug telemetry or business transport.

## Notes
- No business-logic fix before evidence collection.

## Evidence
- Reproduced with synthetic internal WhatsApp payload `DBG-TIMEOUT-007` that matched the real `messages.upsert` structure for `201010323484`.
- Confirmed pre-fix runtime crash in server logs:
  - `Internal assistant worker crashed for 201010323484: <urlopen error timed out>`
  - Traceback pointed to `ai_agent.py:20163` inside `_build_internal_assistant_reply`.
- Confirmed the failing statement was a debug telemetry call:
  - `urllib.request.urlopen(Request('http://127.0.0.1:7778/event', ...), timeout=2).read()`
  - This violated the requirement that telemetry must not break the worker path.
- Post-fix verification no longer shows the original `urlopen error timed out` worker crash.

## Fix Applied
- Wrapped the direct debug telemetry calls in the internal assistant path with local `try/except` guards.
- Reduced telemetry timeout from `2` seconds to `0.25` seconds to avoid worker stalls when no debug listener is present.
- Covered the confirmed failing point plus adjacent internal assistant telemetry points in:
  - internal intent classification
  - booking summary entry
  - general QA fallback

## Current Status
- Original timeout crash: fixed in code and no longer reproducible in post-fix logs.
- Residual issue discovered after the crash fix: `AI request mediator failed: 'str' object has no attribute 'get'`
- Debug session remains open until user verifies the original symptom is resolved and we decide whether to continue into the mediator issue.
