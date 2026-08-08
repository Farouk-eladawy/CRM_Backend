[OPEN] Debug Session: internal-latency

## Symptom
- Internal WhatsApp assistant responds slowly to executable commands.
- Observed gap can exceed 2 minutes between user request and final actionable response.
- After PI-style execution requests, user may receive generic completion text instead of immediate progress/status visibility.

## Expected
- The assistant should acknowledge executable requests quickly.
- Long-running execution should provide immediate queued/progress feedback instead of leaving the user waiting.
- Follow-up steps such as sending tickets should reuse context without unnecessary extra delay.

## Hypotheses
1) The internal assistant performs synchronous heavy work (mediator/PI/background prep) before sending an initial acknowledgement.
2) The PI/background execution path completes asynchronously, but the user-facing status update is delayed or missing.
3) Some follow-up requests are routed through slower agentic paths instead of direct contextual handlers.
4) The observed delay is partly caused by waiting for external providers/tools (invoice provider, PI execution, CRM update) without an early progress reply.
5) There is no dedicated operator-facing progress window/state surface, so completed work is not surfaced promptly even when execution started.

## Evidence Plan
- Compare timestamps across conversation logs, internal webhook logs, and execution manifests.
- Measure time spent in internal webhook intake, intent/mediator, pending action creation, PI manifest queueing, and final reply send.
- Check whether a request is already "in progress" while the user sees no intermediate status.

