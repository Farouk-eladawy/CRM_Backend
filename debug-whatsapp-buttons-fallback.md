# Debug Session: whatsapp-buttons-fallback

Status: OPEN

## Symptom
- Internal assistant menu reaches WhatsApp as plain text on phone instead of reply buttons.
- Earlier attempts also produced "This message couldn't load" on some clients.

## Expected
- Internal assistant menu should render as reply buttons on the target WhatsApp client when using supported payloads.

## Scope
- Internal assistant only.
- Customer-facing WhatsApp template/text sending is out of scope for this session.

## Initial Hypotheses
- H1: Evolution `sendButtons` endpoint rejects the payload for this instance/account at runtime.
- H2: The button payload is accepted by the server but downgraded/normalized before delivery, causing text fallback.
- H3: The current internal assistant flow sends prelude text successfully, then button send fails, so only the text is visible.
- H4: Some button fields or endpoint shape used by this Evolution version are incompatible with the current instance.
- H5: The WhatsApp client linked to this instance does not support the delivered interactive format consistently.

## Evidence Plan
- Add runtime instrumentation around `_send_internal_whatsapp_buttons`.
- Capture request intent, endpoint path, button types/count, HTTP status, and payload summary.
- Reproduce with `menu`.
- Compare pre-fix evidence before any business-logic change.

## Progress Log
- Session initialized.
- Instrumentation added around `_send_internal_whatsapp_buttons` and `_send_internal_whatsapp_response`.
- Reproduced with `menu`.

## Evidence
- C: response enters safe reply branch with `replyButtonCount=3` and `unsafeOptionCount=0`.
- A: request is sent to `/message/sendButtons/fts_internal_notifications` with three `reply` buttons.
- B: Evolution returns `statusCode=201` and payload preview contains `viewOnceMessage -> interactiveMessage -> nativeFlowMessage -> quick_reply`.
- No fallback-after-button-failure event was recorded in this reproduction.

## Hypothesis Status
- H1 rejected: the endpoint is not rejecting the request in this reproduction.
- H2 unconfirmed: no downgrade evidence inside the server response path.
- H3 rejected: text is not shown because `sendButtons` failed; text is sent first by design, and button request succeeds.
- H4 possible: the interactive format emitted by this Evolution/Baileys path may still be incompatible with the receiving client/runtime despite 201 success.
- H5 most likely: recipient-side/client-side rendering support for this unofficial interactive format is inconsistent, so buttons do not appear reliably on phone.

## Fix Candidate
- Minimal test change applied: when safe reply buttons exist, stop sending the prelude text as a separate WhatsApp message.
- The interactive bubble now carries the description/body by itself.
- Text fallback remains in place only if button send fails.

## Post-Restart Observation
- After server restart and re-test, runtime logs still show hypothesis A/B events only:
  - request sent to `sendButtons`
  - response returned `201`
- No fallback-to-text event was produced.
- User observed "no reply at all" on phone after restart.
- This means the button-only experiment removed the visible text, while the interactive payload still did not render on the client.
