# [OPEN] religious-ui-routing

## Scope
- Verify unresolved issues still visible on the live UI:
- `Reply Channel` missing `Facebook` in `Auto`.
- `FB Template` preview hits WhatsApp preview endpoint and returns `404`.
- Religious dashboard users still show non-religious users.
- Religious assign list still incomplete.
- Religious reply signature rules may still be violated.
- Mobile attach may still fail on the actual active UI path.

## Hypotheses
1. Reply channel options are rendered from a hardcoded allowlist that excludes `facebook`.
2. FB template preview is incorrectly routed to WhatsApp preview API.
3. Religious dashboard and assign still rely on stale/general user sources on some code paths.
4. Religious signature logic is only partially centralized and some send/generate paths still bypass it.
5. Mobile attach fix was applied to one compose path but not all active mobile compose variants.

## Evidence Plan
- Inspect active frontend code paths for channel options and template preview routing.
- Inspect active backend endpoints used by preview/send.
- Reproduce behavior on production URL and compare with current source code.
- Instrument only if the code paths remain ambiguous after direct inspection.

## Status
- Session started. No business-logic fix applied in this debug session yet.
