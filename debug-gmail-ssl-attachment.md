# [OPEN] gmail-ssl-attachment

## Symptom
- Repeated SSL failures in `gmail_service.py:572` inside `get_attachment_content`.
- Observed errors include `WRONG_VERSION_NUMBER`, `internal error`, `DECRYPTION_FAILED_OR_BAD_RECORD_MAC`, `UNEXPECTED_RECORD`, and `UNEXPECTED_MESSAGE`.

## Falsifiable Hypotheses
| ID | Hypothesis | Likelihood | Effort | Expected Signal |
|----|------------|------------|--------|-----------------|
| A | Failure occurs in Gmail HTTPS transport before payload decoding | High | Low | `SSLError` at `message_get`/`attachment_get` before `data` decode |
| B | Same Gmail API client / `_http` object is hit concurrently by overlapping requests | High | Low | Same `service_id` and `http_id` appear across overlapping requests with `active_now > 1` |
| C | Upstream proxy / TLS interception is involved | Medium | Low | Proxy env flags present and failures cut across different Gmail operations |
| D | Issue is attachment-specific payload corruption | Low | Low | Same attachment consistently fails after transport succeeds |
| E | Failure is broader Gmail transport instability, not limited to attachment fetch | Medium | Medium | Similar TLS signals in other Gmail API operations near reproduction |

## Current Evidence
- `gmail_service.py` creates one long-lived Gmail API client via `self.service = build('gmail', 'v1', credentials=creds)`.
- `get_attachment_content()` fails at Gmail API calls `messages().get(...).execute()` or `attachments().get(...).execute()`, before any local base64 decoding.
- Runtime debug log shows near-simultaneous attachment requests inside the same PID for different Gmail messages, with mixed outcomes:
  - one request succeeds while another fails with `SSLError`
  - failures occur at both `message_get` and `attachment_get`
- `gmail_attachment_part_missing` is not sufficient to explain the incident, because some requests log `part_missing` and still end with `gmail_attachment_success`.
- Current evidence confirms a transport-layer SSL/TLS failure during Gmail API access; it does not yet prove whether the corruption source is shared-client concurrency, upstream network/proxy interference, or another lower transport issue.

## Instrumentation Added
- Added authentication-time debug event to record `service_id`, `http_id`, `http_type`, `thread_id`, and proxy env presence.
- Added per-request concurrency tracking in `get_attachment_content()` to record `active_before`, `active_now`, and `active_after` per `service_id`.
- Added unique `req_id` generation including `pid`, `thread_id`, and message suffix to avoid same-millisecond collisions seen in prior logs.
- Added separate start markers for `message_get` and `attachment_get` to pinpoint the exact failing stage.

## Reproduction Readiness
- Active backend process on port `5001` is `python ai_agent.py` with PID `39424`.
- That process started before the latest instrumentation change, so a backend restart is required before collecting the next clean evidence run.

## Evidence Analysis

### Reproduction Performed By Agent
- Started debug server for `gmail-attachment-ssl`.
- Restarted backend and issued four parallel HTTP requests to `/api/gmail_attachment/...` using previously observed Gmail message/attachment IDs.
- Observed mixed runtime outcomes: repeated `404` responses at API level while internal Gmail transport logged TLS / stream corruption errors.

### Verification Table
| ID | Hypothesis | Status | Evidence Summary |
|----|------------|--------|------------------|
| A | Failure occurs in Gmail HTTPS transport before payload decoding | Confirmed | `gmail_attachment_exception` fired at `message_get` and `attachment_get` before any decode success path completed |
| B | Same Gmail API client / `_http` object is hit concurrently by overlapping requests | Confirmed | Multiple requests shared identical `service_id=2834401337392` and `http_id=2834401335472` while `active_now` rose from 1 to 4 |
| C | Upstream proxy / TLS interception is involved | Rejected for this run | All events show `https_proxy=false` and `http_proxy=false` |
| D | Issue is attachment-specific payload corruption | Rejected | Errors affected two different Gmail messages and failed at both `message_get` and `attachment_get`; one request also produced `IncompleteRead` |
| E | Failure is broader Gmail transport instability, not limited to attachment fetch | Inconclusive | Current reproduction focused on attachment endpoint only |

### Key Runtime Evidence
- `gmail_attachment_content_start` shows first request on shared client with `active_now=1`.
- A second request entered the same shared client with `active_now=2`.
- A third request entered the same shared client with `active_now=3`.
- A fourth request entered the same shared client with `active_now=4`.
- Exceptions then appeared on the same `service_id/http_id` pair:
  - `IncompleteRead(4 bytes read)` at `message_get`
  - `[SSL: UNEXPECTED_RECORD] unexpected record`
  - `[SSL: WRONG_VERSION_NUMBER] wrong version number` at `attachment_get`
  - `[SSL: WRONG_VERSION_NUMBER] wrong version number` at `message_get`

## Root Cause
- The bug is reproduced and confirmed as concurrent use of the same Gmail API transport object (`AuthorizedHttp`) across overlapping attachment fetch requests.
- When multiple attachment requests overlap, they share one `service_id/http_id` and the underlying transport produces corrupted/inconsistent reads (`IncompleteRead`, `UNEXPECTED_RECORD`, `WRONG_VERSION_NUMBER`), which the API layer then surfaces as attachment `404` / not found.
