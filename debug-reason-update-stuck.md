# Debug Session: reason-update-stuck

Status: OPEN

## Scope
- Investigate why an internal WhatsApp update request shows "جارٍ تحديث..." but does not consistently reach the final success message, while the PI Background Task Engine processes manifests.

## Reported Symptoms (User)
- First update: "✅ تم تحديث حقل Reason ... بنجاح."
- Second update: Stuck at "جارٍ تحديث ..." with no visible completion message.
- PI Background Task Engine shows multiple manifests processed and result files learned.

## Falsifiable Hypotheses
1. The manifest execution succeeded, but the outbound notification back to Ahmady failed (Evolution send error) or was skipped.
2. The manifest execution succeeded, but the result file content indicates an error (silent failure) and the UI message "جارٍ تحديث..." was emitted before result confirmation.
3. The request created multiple manifests; one succeeded and another overwrote state or caused a conflicting message flow.
4. The internal assistant session `pending_action/workflow_state` got cleared or mismatched, so the completion message is not routed back correctly.
5. The webhook fast-ack/background thread returns 200 quickly but the background thread crashes before sending the final WhatsApp response.

## Evidence Plan
- Inspect the exact `man_*.json` manifest(s) and corresponding `result_man_*.json` files.
- Verify whether the result contains success vs error and whether a send-back message is queued.
- Correlate with `agent_log.txt` around the message IDs.

## Constraints
- No business-logic modifications until evidence confirms the root cause.
- First code change (if needed) must be instrumentation only.
