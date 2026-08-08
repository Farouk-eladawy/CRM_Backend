import re

file_path = "ai_agent.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the PI BYPASS inside _build_internal_assistant_reply (around line 17220)
# We want to intercept requires_approval: true
search_block = """                        if manifest_dict and manifest_dict.get("actions"):
                            try:
                                self._write_pi_manifest_to_outbox(actor, manifest_dict)
                            except Exception as e:
                                logging.error(f"Failed to write PI Agentic manifest from Internal Assistant: {e}")

                    reply_text = structured_result.get("internal_reply") or structured_result.get("recommended_internal_reply") or "تم استلام الطلب ومعالجته عبر (PI Agentic OS)."
                    return _finalize_internal_reply(reply_text, intent_name="agentic_orchestrator", case_context=session_state.get("last_case_context"))"""

replace_block = """                        if manifest_dict and manifest_dict.get("actions"):
                            has_approval = any(str(act.get("requires_approval", "")).lower() == "true" for act in manifest_dict.get("actions", []))
                            if has_approval:
                                session_state["pending_action"] = {"type": "execute_manifest", "manifest": manifest_dict}
                                _set_workflow_state(
                                    intent_name="agentic_orchestrator",
                                    phase="awaiting_approval",
                                    awaiting="approval",
                                    case_context=session_state.get("last_case_context"),
                                    note="Approval required for PI Manifest.",
                                    action={"type": "execute_manifest", "manifest": manifest_dict},
                                )
                                reply_text = structured_result.get("internal_reply") or structured_result.get("recommended_internal_reply") or "هناك إجراءات تحتاج لموافقتك. هل أعتمدها؟ (نعم/لا)"
                                return _finalize_internal_reply(reply_text, intent_name="agentic_orchestrator", case_context=session_state.get("last_case_context"))
                            else:
                                try:
                                    self._write_pi_manifest_to_outbox(actor, manifest_dict)
                                except Exception as e:
                                    logging.error(f"Failed to write PI Agentic manifest from Internal Assistant: {e}")

                    reply_text = structured_result.get("internal_reply") or structured_result.get("recommended_internal_reply") or "تم استلام الطلب ومعالجته عبر (PI Agentic OS)."
                    return _finalize_internal_reply(reply_text, intent_name="agentic_orchestrator", case_context=session_state.get("last_case_context"))"""

if search_block in content:
    content = content.replace(search_block, replace_block)
    print("Replaced Block 1 successfully")
else:
    print("Block 1 not found!")

# 2. Update the pending_action consumption (around line 17255)
search_block_2 = """                    elif pending_type == "trip_booking_alert":
                        ok, execution_message = _execute_pending_trip_booking_alert_action(pending_action, actor=actor)
                    else:
                        ok, execution_message = _execute_pending_send_action(pending_action)"""

replace_block_2 = """                    elif pending_type == "trip_booking_alert":
                        ok, execution_message = _execute_pending_trip_booking_alert_action(pending_action, actor=actor)
                    elif pending_type == "execute_manifest":
                        try:
                            self._write_pi_manifest_to_outbox(actor, pending_action.get("manifest"))
                            ok, execution_message = True, "تم وضع الأوامر في مسار التنفيذ بنجاح."
                        except Exception as e:
                            ok, execution_message = False, f"فشل التنفيذ: {e}"
                    else:
                        ok, execution_message = _execute_pending_send_action(pending_action)"""

if search_block_2 in content:
    content = content.replace(search_block_2, replace_block_2)
    print("Replaced Block 2 successfully")
else:
    print("Block 2 not found!")

with open("ai_agent_patched.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Saved to ai_agent_patched.py")
