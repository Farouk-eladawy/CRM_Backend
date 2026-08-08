[OPEN]

## Session
- id: capability-dev-str-get
- symptom: Capability Dev Error: 'str' object has no attribute 'get' while processing PI manifest develop_new_capability

## Hypotheses (falsifiable)
1. The `actions` item for `develop_new_capability` has `payload` as a string instead of a dict, and the executor calls `.get` on it.
2. The `actions` item is a string (not a dict), causing downstream `.get` access to fail.
3. The manifest JSON was written partially/corrupted so `action.get("payload")` becomes a string due to parsing fallback.
4. A previous tool writes `python_code` / `parameters_schema` as strings in an unexpected nesting shape, shifting keys and making `tool_payload` non-dict.
5. The executor shadowed `payload` variable with a string before calling `.get` (variable reuse bug).

## Evidence to collect (instrumentation)
- For each processed action: type(action), action keys, type(payload), and a safe preview of payload fields names only (no secrets).
- For develop_new_capability specifically: which line triggers `.get`, and the concrete runtime type that reaches it.

## Repro steps
1. Trigger a `develop_new_capability` action from PI (any request that forces tool generation).
2. Observe debug-server logs for the action + payload shape.

## Status
- evidence collected:
  - `payload_py_type` observed as `str` for `develop_new_capability` actions (repro with `man_test_dev_str`)
  - debug logs: `process_outbox.action_shape` + `develop_new_capability.payload_shape`
- fix applied:
  - guard `develop_new_capability` executor against non-dict payloads; attempts JSON parse for string payloads; otherwise fails with a clear ValueError
- next:
  - reproduce with a real PI-generated manifest (not a synthetic one)
  - if payload still arrives as string, investigate manifest generation path and why it serializes payload incorrectly
