# [OPEN] PI Workflow E2E Tests

## Session
- session_id: pi-workflow-e2e-tests
- goal: Run real end-to-end tests for the new PI integration + staged hard-case workflow + internal assistant flows, with runtime evidence.

## Scope (Initial)
- Validate staged workflow writes under runtime/pi_cases/<case_id> for stages 1-8.
- Validate PI real call only happens when delegation_allowed=true and should_delegate=true.
- Validate PI output is structured JSON and saved into pi_delegation.json.
- Validate pi_guidance is included in execution_bridge.json and pi_summary in memory.json when eligible.
- Validate approval gating and no unintended execution happens during tests unless explicitly allowed.
- Validate trip_booking_alert watcher creation + polling behavior without spamming and respecting permissions.

## Hypotheses (Falsifiable)
1) Stage transitions still advance in some cases even when validation is blocked (should remain on same stage with blocked reasons).
2) PI CLI returns non-JSON output or JSON wrapped in text, causing parse failures and blocking delegation unexpectedly.
3) PI runs when it should not (delegation_allowed=false or should_delegate=false), causing unnecessary latency.
4) Execution bridge does not surface PI guidance in execution_bridge.json, losing the benefit of PI output.
5) Watcher polling or filtering can miss new records or re-notify the same record_id due to state persistence issues.

## Evidence Plan
- Start debug server and collect NDJSON runtime logs per scenario.
- Run scripted scenario driver that triggers internal assistant intent flows through HTTP endpoints (or direct callable entrypoints).
- Compare expected vs observed stage files and debug logs.

## Notes
- Do not log secrets (tokens / api keys).
- Do not approve real customer-facing sends or Airtable writes unless explicitly enabled for a dedicated test record.

