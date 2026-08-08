# [OPEN] gmail-attachment-ssl

## Scope
- Analyze intermittent Gmail attachment fetch failures and SSL errors in `gmail_service.py:get_attachment_content` that surface as `/api/gmail_attachment/...` returning 404 and internal error alerts.

## Observed Symptoms (from user logs)
- Repeated warnings:
  - `Attachment not found across all connected Gmail services` for `requested_mailbox=booking`, `message_id=19f5f2a708cf8c59`, and specific `attachment_id=...`
- Intermittent TLS/SSL errors:
  - `[SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:2559)`
  - `[SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC] decryption failed or bad record mac (_ssl.c:2559)`
  - `[SSL] internal error (_ssl.c:2559)`
- HTTP surface symptom:
  - `GET /api/gmail_attachment/booking/<message_id>/<attachment_id> ...` returns 404 during failures
  - At least once, the same endpoint returns 200 later, indicating intermittent behavior

## Hypotheses (falsifiable)
1. **Wrong account/mailbox routing**: The requested `message_id` exists, but not in the Gmail service mapped to `requested_mailbox=booking`, so attachment lookup legitimately fails across connected services.
2. **Intermittent transport/TLS instability** between this runtime and Google endpoints (proxy/VPN/SSL interception/connection reuse) causes sporadic SSL exceptions; retries later succeed (explains 404s and later 200).
3. **Partial/failed message fetch leads to false “not found”**: an SSL exception during message/attachment fetch is caught and surfaced as “attachment not found”, masking the true cause.
4. **Stale/invalid attachment_id**: frontend requests an attachment_id that no longer matches the message payload (e.g., message changed, different MIME part chosen), so backend cannot find it.
5. **Concurrent Gmail clients / token refresh race**: multi-service iteration or token refresh under concurrency produces sporadic SSL or API errors for the same message_id.

## Evidence Needed (instrumentation targets)
- For each attachment request: resolved Gmail account/service used, target host/scheme, request path (no tokens), whether failure was “not found” vs exception, exception type, and whether retry succeeded.
- For “not found”: list available attachment part IDs on the message for that account to confirm mismatch.
- For SSL errors: record whether a proxy is configured (no credentials), TLS endpoint hostname, and whether errors correlate with a specific service/account.

## Plan
1. Add runtime instrumentation (no business logic change) around `get_attachment_content` to emit structured debug events.
2. Reproduce by opening the same attachment in the dashboard a few times.
3. Compare pre/post results and decide minimal fix.

## Status Log
- 2026-07-14: Session opened, awaiting instrumentation and reproduction.

