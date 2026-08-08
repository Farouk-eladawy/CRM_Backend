# Debug Session: reminder-dashboard-logging [OPEN]

## Symptom
- Reminder 10min sends email successfully for booking `9224280`.
- Expected: the sent email should also appear inside the customer's conversation in the dashboard.
- Actual: email is sent, but no message appears in the dashboard timeline.

## Scope
- Flow under investigation:
  - `pickup_reminder_10min.py`
  - `/api/pickup_reminder_10min/run`
  - chat logging path via `chat_db`

## Hypotheses
1. The reminder flow reaches `send_email()` successfully, but `_log_email()` is not being called.
2. `_log_email()` is called, but `_ensure_chat()` fails to resolve or create the customer conversation for this record.
3. The conversation is created/found, but `chat_db.add_message()` fails silently inside the `try/except`.
4. The reminder flow logs against a different conversation identifier/source than the one visible in the dashboard.
5. The Airtable record payload for this workflow lacks one of the identity fields used for chat matching, so the timeline write is skipped or attached elsewhere.

## Evidence Plan
- Add runtime instrumentation around:
  - `run()` decision path for reminder records
  - `_ensure_chat()`
  - `_log_email()`
  - `_log_whatsapp()`
- Reproduce with a single reminder send for a known booking.
- Compare pre-fix evidence before making any logic change.

## Status
- Session initialized.
- Evidence collected from runtime/database inspection:
  - `/api/pickup_reminder_10min/run` was hit successfully.
  - For booking `9224280`, the only conversation found in `chat_db` was an `Email` conversation with `airtable_record_id = recHJiMTtRtf8UFXx`.
  - `_ensure_chat()` was preferring `Email` whenever `customer_email` existed, even if a WhatsApp phone was available.
- Confirmed root cause:
  - Reminder timeline entries were being routed to an email-sourced conversation instead of the main customer WhatsApp conversation used in the dashboard.
- Minimal fix applied:
  - `_ensure_chat()` now prefers `WhatsApp` when a phone number exists, and falls back to `Email` only when no phone is available.
- Waiting for post-fix verification from the user.
