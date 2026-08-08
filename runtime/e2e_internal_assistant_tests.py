import json
import os
import time
import uuid

import requests


BASE_URL = "http://127.0.0.1:5001"
WEBHOOK_URL = f"{BASE_URL}/api/internal_notifications/whatsapp/webhook"
DEBUG_SERVER_URL = os.environ.get("DEBUG_SERVER_URL") or "http://127.0.0.1:7777/event"
DEBUG_SESSION_ID = os.environ.get("DEBUG_SESSION_ID") or "pi-workflow-e2e-tests"

SENDER_PHONE = "201010323484"
REMOTE_JID = f"{SENDER_PHONE}@s.whatsapp.net"
PI_CASES_ROOT = os.path.join(os.getcwd(), "runtime", "pi_cases")


def _post_internal_message(text: str, message_id: str | None = None):
    msg_id = message_id or uuid.uuid4().hex[:16]
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": REMOTE_JID,
                "fromMe": False,
                "id": msg_id,
            },
            "conversation": text,
        },
    }
    resp = requests.post(WEBHOOK_URL, json=payload, timeout=20)
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}
    return resp.status_code, body


def _dbg_emit(event: str, payload: dict | None = None, run_id: str = "e2e-runner"):
    try:
        body = {
            "sessionId": DEBUG_SESSION_ID,
            "runId": run_id,
            "hypothesisId": "e2e",
            "event": event,
            "payload": payload or {},
        }
        requests.post(DEBUG_SERVER_URL, json=body, timeout=4)
    except Exception:
        return


def _snapshot_case_dirs():
    if not os.path.isdir(PI_CASES_ROOT):
        return set()
    return {name for name in os.listdir(PI_CASES_ROOT) if name and name.startswith("case-")}


def _read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _summarize_case(case_id: str):
    case_dir = os.path.join(PI_CASES_ROOT, case_id)
    state = _read_json(os.path.join(case_dir, "state.json")) or {}
    summary = {
        "case_id": case_id,
        "status": state.get("status"),
        "current_stage": state.get("current_stage"),
        "stage_status": state.get("stage_status"),
        "next_stage": state.get("next_stage"),
        "case_reference": state.get("case_reference"),
        "intent": state.get("intent"),
        "has_intake": os.path.exists(os.path.join(case_dir, "intake.json")),
        "has_analysis": os.path.exists(os.path.join(case_dir, "analysis.json")),
        "has_plan": os.path.exists(os.path.join(case_dir, "plan.json")),
        "has_validation": os.path.exists(os.path.join(case_dir, "validation.json")),
        "has_approval": os.path.exists(os.path.join(case_dir, "approval_preparation.json")),
        "has_pi_delegation": os.path.exists(os.path.join(case_dir, "pi_delegation.json")),
        "has_execution_bridge": os.path.exists(os.path.join(case_dir, "execution_bridge.json")),
        "has_memory": os.path.exists(os.path.join(case_dir, "memory.json")),
    }
    pi_del = _read_json(os.path.join(case_dir, "pi_delegation.json")) or {}
    pi_analysis = pi_del.get("pi_analysis") if isinstance(pi_del, dict) else None
    if isinstance(pi_analysis, dict):
        summary["pi_status"] = pi_analysis.get("status")
        structured = pi_analysis.get("structured_result") if isinstance(pi_analysis.get("structured_result"), dict) else {}
        summary["pi_has_structured"] = bool(structured)
        summary["pi_confidence"] = structured.get("confidence") if structured else None
        summary["pi_execution_guidance"] = structured.get("execution_guidance") if structured else None
    return summary


def run():
    run_id = f"e2e-{int(time.time())}"
    pre_dirs = _snapshot_case_dirs()
    _dbg_emit("e2e.run.start", {"base_url": BASE_URL, "webhook_url": WEBHOOK_URL}, run_id=run_id)

    scenarios = [
        {
            "name": "context_next_step_repeat_for_stage_progression",
            "messages": [
                "next step 123456test",
                "next step 123456test",
                "next step 123456test",
                "next step 123456test",
                "next step 123456test",
                "next step 123456test",
                "next step 123456test",
            ],
        },
        {
            "name": "reported_speech_should_not_trigger_send",
            "messages": [
                "العميل قال ابعتله التفاصيل",
                "طيب في الحالة دي ايه افضل خطوة؟",
            ],
        },
        {
            "name": "trip_booking_alert_pending_then_cancel",
            "messages": [
                "اشعار عند وصول حجز لرحلة: Grand Egyptian Museum (اليوم وغدا)",
                "إلغاء",
            ],
        },
    ]

    results = []
    for scenario in scenarios:
        _dbg_emit("e2e.scenario.start", {"scenario": scenario["name"]}, run_id=run_id)
        for text in scenario["messages"]:
            status_code, body = _post_internal_message(text)
            results.append(
                {
                    "scenario": scenario["name"],
                    "message": text,
                    "status_code": status_code,
                    "response": body,
                }
            )
            _dbg_emit(
                "e2e.message.sent",
                {
                    "scenario": scenario["name"],
                    "text_preview": text[:120],
                    "status_code": status_code,
                    "response_status": (body or {}).get("status") if isinstance(body, dict) else None,
                },
                run_id=run_id,
            )
            time.sleep(0.8)

    post_dirs = _snapshot_case_dirs()
    new_dirs = sorted(post_dirs - pre_dirs)
    case_summaries = [_summarize_case(cid) for cid in new_dirs]
    _dbg_emit(
        "e2e.run.cases",
        {
            "new_case_count": len(new_dirs),
            "cases": case_summaries[:10],
        },
        run_id=run_id,
    )
    _dbg_emit("e2e.run.done", {"result_count": len(results)}, run_id=run_id)

    print(json.dumps({"status": "done", "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
