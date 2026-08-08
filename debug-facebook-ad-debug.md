# Debug Session: facebook-ad-debug
- **Status**: [OPEN]
- **Issue**: Track Messenger ad/referral origin visibility and Facebook customer name resolution instead of placeholder names.
- **Debug Server**: http://127.0.0.1:7779/event
- **Log File**: .dbg/trae-debug-log-facebook-ad-debug.ndjson

## Reproduction Steps
1. Customer opens Messenger chat from a Facebook ad and sends the first message to the page.
2. Observe whether the CRM stores or displays ad/referral metadata for that conversation.
3. Observe whether the customer name is resolved from Facebook Graph API or falls back to `Facebook User`.

## Hypotheses & Verification
| ID | Hypothesis | Likelihood | Effort | Evidence |
|----|------------|------------|--------|----------|
| A | Meta sends ad metadata in `referral` or `postback.referral`, but the webhook handler does not log or persist it. | High | Low | Partially confirmed |
| B | The app/webhook subscription does not include the Messenger referral/postback events needed for ad attribution. | Medium | Medium | Suspected |
| C | Facebook profile lookup fails because the page token is missing, expired, or lacks the required permissions. | High | Low | Confirmed by app logs |
| D | The handler is sometimes using the wrong PSID or skipping lookup on the relevant branch. | Medium | Medium | Not proven |
| E | Name lookup succeeds in some cases, but the resolved name is not persisted back to the conversation record reliably. | Medium | Medium | Not proven |

## Log Evidence
- `agent_log.txt` confirms live `/webhook` traffic during the reproduction window.
- `agent_log.txt` also confirms Facebook profile lookup failure with `code=100` / `subcode=33` for Messenger PSID lookups.
- `fb_webhook_debug.jsonl` shows current Messenger payloads are mostly `message`, `delivery`, `read`, and `hop_context`, with no visible `referral` fields in the sampled reproduction payloads.
- Minimal fix applied:
  - Use `first_name,last_name,name` when resolving Facebook profile names.
  - Capture `referral` and `hop_context` details when present and write a visible referral note into the chat.

## Verification Conclusion
- Name issue currently points to Facebook Graph lookup/token/permission mismatch rather than frontend rendering alone.
- Ad visibility issue currently points to missing/unavailable `referral` metadata in the sampled webhook payloads, so the code now captures and surfaces it if Meta sends it.
