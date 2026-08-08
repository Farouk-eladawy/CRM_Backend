# Debug Session: ops-alert-batch

Status: [OPEN]

Scope:
- Analyze and fix multiple production alerts separately and in order.
- Start with the highest-confidence issue first: invoice creation `404 NOT_FOUND`.

Issues in scope:
1. Invoice creation uses wrong Airtable identifier and fails with `404 NOT_FOUND`.
2. Werkzeug logs `Bad HTTP/0.9 request type`.
3. WhatsApp template send fails with Meta `132001` (`feedbackk` missing in `en`).
4. Meta delivery webhooks report `131026` and `131049`.
5. Gmail SSL fails with `WRONG_VERSION_NUMBER`.
6. Airtable `append_to_chat_log` fails with retriable `503`.

Initial hypotheses:
- H1: One or more `create_invoice` execution paths pass booking number where Airtable expects `record_id`.
- H2: Non-HTTP traffic or TLS handshakes are hitting the Flask HTTP port, producing the Werkzeug `HTTP/0.9` log noise.
- H3: A stale or misspelled template name (`feedbackk`) is being selected without a schema/config validation step.
- H4: Meta `131026` and `131049` are real delivery outcomes and need handling/routing improvements, not transport retries.
- H5: Gmail transport configuration is mixing TLS/SSL modes, causing `WRONG_VERSION_NUMBER`.
- H6: Airtable chat-log appends lack retry/backoff for retriable 503 responses.

Plan:
1. Inspect evidence and code paths for issue 1.
2. Confirm or reject H1 from code/runtime evidence.
3. Apply the minimal fix for issue 1 only.
4. Move to issue 2 with fresh evidence and isolated reasoning.
5. Repeat sequentially for each remaining issue.

Issue 1 evidence:
- Runtime log showed `/api/payments/create` receiving `record_id="546980816555"` in one run and `record_id="rec4mCX8CaQoQrXjI"` in another.
- This confirms a mixed identifier path where booking number was passed instead of Airtable record id.

Issue 1 fix status:
- `background_task_engine.py` now resolves booking number to Airtable `record_id` before calling `/api/payments/create`.
- Current status: code-level fix present; needs runtime re-verification.

Issue 2 evidence:
- Alert came from `werkzeug` with `Bad HTTP/0.9 request type (...)` while backend binds to `0.0.0.0`.
- This is consistent with non-HTTP or TLS garbage traffic hitting a plain HTTP Flask socket.

Issue 2 fix status:
- Internal WhatsApp error alerts now suppress known noisy `werkzeug` malformed-request messages.
- Current status: fixed at alerting layer; backend behavior unchanged.

Issue 3 evidence:
- `send_whatsapp_message()` fetches template details from Meta before send.
- The code selected a fallback template structure, but did not rewrite the outgoing payload template `name/language` to the actual resolved values.
- This can still produce Meta `132001` when the requested translation is missing.

Issue 3 fix status:
- The outbound template payload now rewrites `template.name` and `template.language.code` to the resolved Meta-approved template/language before sending.
- Current status: code-level fix present; needs runtime re-verification.

Issue 4 evidence:
- Meta webhook marks message status as `failed` with codes `131026` and `131049`.
- These are delivery outcomes reported after send, not local transport exceptions.

Issue 4 fix status:
- Webhook logging now downgrades `131026` and `131049` from `error` to `warning`.
- Current status: fixed at alert-severity layer; status persistence remains intact.

Issue 5 evidence:
- `gmail_service.py` failures occur across two Gmail API operations with the same TLS signature: `SSL: WRONG_VERSION_NUMBER`.
- No explicit proxy environment variables were present in the current shell.

Issue 5 fix status:
- Gmail transport errors matching TLS/SSL handshake failures now trigger a one-time service re-authentication and retry.
- Current status: code-level mitigation present; needs runtime re-verification.

Issue 6 evidence:
- Airtable returned `503 RETRIABLE_ERROR` with explicit message that retry is safe.
- `append_to_chat_log()` previously failed after a single update attempt.

Issue 6 fix status:
- `append_to_chat_log()` now retries retriable Airtable update failures up to 3 attempts with short backoff.
- Current status: code-level fix present; needs runtime re-verification.

Issue 7 evidence:
- `query_ai()` logged provider-level DeepSeek `503` failures, then returned a raw failure string when all providers failed.
- Multiple analyzer callers used direct `json.loads(...)` on the returned text, causing downstream parse failures such as `Expecting value: line 1 column 1 (char 0)`.

Issue 7 fix status:
- `query_ai()` now logs individual provider failures as `warning`, logs only the final aggregate failure as `error`, and returns an empty string for non-assistant roles when all providers fail.
- Analyzer parsing paths were hardened to safely return empty dict/list or `False` instead of raising on invalid/non-JSON output.
- Current status: code-level fix present; needs runtime re-verification.
