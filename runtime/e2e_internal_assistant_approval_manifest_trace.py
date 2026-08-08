import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import chat_db


BASE_URL = "http://127.0.0.1:5001"
WEBHOOK_URL = f"{BASE_URL}/api/internal_notifications/whatsapp/webhook"
SENDER_PHONE = "201010323484"
REMOTE_JID = f"{SENDER_PHONE}@s.whatsapp.net"
SESSION_KEY = "internal_assistant_session:ahmady"
BOOKING_NUMBER = "123456test"
USER_DIR = PROJECT_ROOT / "runtime" / "pi_brain" / "users" / "u_ahmady"
BRIDGE_OUTBOX = USER_DIR / "bridge" / "outbox"
BRIDGE_INBOX = USER_DIR / "bridge" / "inbox"
REPORT_DIR = USER_DIR / "e2e_backups"


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _snapshot_dir(path: Path):
    if not path.exists():
        return {}
    out = {}
    for item in path.glob("*.json"):
        try:
            stat = item.stat()
            out[item.name] = {"size": stat.st_size, "mtime": stat.st_mtime}
        except Exception:
            continue
    return out


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
    return {"status_code": resp.status_code, "body": body, "message_id": msg_id, "text": text}


def _get_session():
    raw = chat_db.get_setting(SESSION_KEY, "")
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return {"raw": str(raw)}


def _session_preview(session):
    session = session if isinstance(session, dict) else {}
    turns = session.get("recent_turns") if isinstance(session.get("recent_turns"), list) else []
    return {
        "updated_at": session.get("updated_at"),
        "last_case_context": session.get("last_case_context") if isinstance(session.get("last_case_context"), dict) else {},
        "pending_action": session.get("pending_action") if isinstance(session.get("pending_action"), dict) else {},
        "workflow_state": session.get("workflow_state") if isinstance(session.get("workflow_state"), dict) else {},
        "recent_turns_tail": turns[-6:],
    }


def _wait_for(predicate, timeout=25, interval=1.0):
    deadline = time.time() + timeout
    last_value = None
    while time.time() < deadline:
        last_value = predicate()
        if last_value:
            return last_value
        time.sleep(interval)
    return last_value


def _fetch_main_record():
    config = json.loads((PROJECT_ROOT / "config.json").read_text(encoding="utf-8"))
    url = f"https://api.airtable.com/v0/{config['airtable']['base_id']}/{config['airtable']['tables']['main_list']}"
    params = {"filterByFormula": "{Booking Nr.}='123456test'", "maxRecords": "1"}
    headers = {"Authorization": f"Bearer {config['airtable']['api_key']}"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    records = data.get("records") or []
    return records[0] if records else {}


def _extract_execution_id(text: str):
    match = re.search(r"Execution ID:\s*([A-Za-z0-9._-]+)", str(text or ""))
    return match.group(1).strip() if match else ""


def _find_new_files(before: dict, after: dict):
    new_names = sorted(set(after) - set(before))
    return new_names


def run():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    BRIDGE_OUTBOX.mkdir(parents=True, exist_ok=True)
    BRIDGE_INBOX.mkdir(parents=True, exist_ok=True)

    run_id = f"trace_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}_{uuid.uuid4().hex[:6]}"
    approval_amount = 20
    approval_currency = "يورو"
    manifest_value = f"E2E MANIFEST TRACE {run_id}"

    report = {
        "run_id": run_id,
        "booking_number": BOOKING_NUMBER,
        "session_key": SESSION_KEY,
        "approval_update_trace": {},
        "manifest_trace": {},
    }

    report["approval_update_trace"]["pre_session"] = _session_preview(_get_session())
    approval_outbox_before = _snapshot_dir(BRIDGE_OUTBOX)
    approval_inbox_before = _snapshot_dir(BRIDGE_INBOX)
    reset_result = _post_internal_message("جلسة جديدة", message_id=f"{run_id}-reset")
    time.sleep(1.5)
    approval_cmd = f"انشاء فاتورة رقم الحجز {BOOKING_NUMBER} قيمة {approval_amount} {approval_currency}"
    approval_send = _post_internal_message(approval_cmd, message_id=f"{run_id}-approval")

    def _approval_pending():
        session = _get_session()
        pending = session.get("pending_action") if isinstance(session.get("pending_action"), dict) else {}
        if str(pending.get("type") or "").strip() == "create_invoice":
            return session
        return None

    approval_pending_session = _wait_for(_approval_pending, timeout=30, interval=1.0)

    report["approval_update_trace"]["reset_result"] = reset_result
    report["approval_update_trace"]["approval_send"] = approval_send
    report["approval_update_trace"]["pending_session"] = _session_preview(approval_pending_session or _get_session())

    approve_result = _post_internal_message("نعم", message_id=f"{run_id}-approve")

    def _approval_done():
        session = _get_session()
        pending = session.get("pending_action") if isinstance(session.get("pending_action"), dict) else {}
        turns = session.get("recent_turns") if isinstance(session.get("recent_turns"), list) else []
        if pending:
            return None
        if any("تم وضع الأوامر في مسار التنفيذ بنجاح" in str((item or {}).get("text") or "").strip() for item in turns[-4:]):
            return session
        workflow = session.get("workflow_state") if isinstance(session.get("workflow_state"), dict) else {}
        if str(workflow.get("action_type") or "").strip() == "execute_manifest":
            return session
        return None

    approval_done_session = _wait_for(_approval_done, timeout=30, interval=1.0)
    approval_outbox_after = _snapshot_dir(BRIDGE_OUTBOX)
    approval_inbox_after = _snapshot_dir(BRIDGE_INBOX)
    approval_record = _fetch_main_record()
    report["approval_update_trace"]["approve_result"] = approve_result
    report["approval_update_trace"]["done_session"] = _session_preview(approval_done_session or _get_session())
    report["approval_update_trace"]["outbox_before"] = approval_outbox_before
    report["approval_update_trace"]["inbox_before"] = approval_inbox_before
    report["approval_update_trace"]["outbox_after"] = approval_outbox_after
    report["approval_update_trace"]["inbox_after"] = approval_inbox_after
    report["approval_update_trace"]["new_outbox_files"] = _find_new_files(approval_outbox_before, approval_outbox_after)
    report["approval_update_trace"]["new_inbox_files"] = _find_new_files(approval_inbox_before, approval_inbox_after)
    report["approval_update_trace"]["record_after_approval"] = {
        "record_id": approval_record.get("id"),
        "Stripe invoice": (approval_record.get("fields") or {}).get("Stripe invoice"),
    }

    manifest_outbox_before = _snapshot_dir(BRIDGE_OUTBOX)
    manifest_inbox_before = _snapshot_dir(BRIDGE_INBOX)
    manifest_cmd = f"حدث حقل Reason للحجز {BOOKING_NUMBER} إلى {manifest_value}"
    manifest_send = _post_internal_message(manifest_cmd, message_id=f"{run_id}-manifest")

    def _manifest_session_ready():
        session = _get_session()
        turns = session.get("recent_turns") if isinstance(session.get("recent_turns"), list) else []
        tail_text = "\n".join(str((item or {}).get("text") or "") for item in turns[-4:])
        if "Execution ID:" in tail_text:
            return session
        workflow = session.get("workflow_state") if isinstance(session.get("workflow_state"), dict) else {}
        note = str(workflow.get("note") or "").strip()
        if "Execution ID:" in note:
            return session
        return None

    manifest_session = _wait_for(_manifest_session_ready, timeout=20, interval=1.0)
    manifest_session_preview = _session_preview(manifest_session or _get_session())
    recent_text = "\n".join(str((item or {}).get("text") or "") for item in manifest_session_preview.get("recent_turns_tail") or [])
    workflow_note = str((manifest_session_preview.get("workflow_state") or {}).get("note") or "")
    manifest_id = _extract_execution_id(recent_text) or _extract_execution_id(workflow_note)

    def _manifest_done():
        after_inbox = _snapshot_dir(BRIDGE_INBOX)
        new_inbox = _find_new_files(manifest_inbox_before, after_inbox)
        if manifest_id:
            for name in new_inbox:
                if manifest_id in name:
                    return {"after_inbox": after_inbox, "new_inbox": new_inbox}
        elif new_inbox:
            return {"after_inbox": after_inbox, "new_inbox": new_inbox}
        return None

    manifest_done = _wait_for(_manifest_done, timeout=30, interval=1.0)
    manifest_outbox_after = _snapshot_dir(BRIDGE_OUTBOX)
    manifest_inbox_after = _snapshot_dir(BRIDGE_INBOX)

    manifest_result_payload = None
    if manifest_done:
        new_inbox = manifest_done.get("new_inbox") or []
        target_name = ""
        if manifest_id:
            for name in new_inbox:
                if manifest_id in name:
                    target_name = name
                    break
        if not target_name and new_inbox:
            target_name = new_inbox[-1]
        if target_name:
            manifest_result_payload = _read_json(BRIDGE_INBOX / target_name)

    manifest_record = _fetch_main_record()
    report["manifest_trace"] = {
        "outbox_before": manifest_outbox_before,
        "inbox_before": manifest_inbox_before,
        "manifest_send": manifest_send,
        "session_after_manifest_send": manifest_session_preview,
        "manifest_id": manifest_id,
        "outbox_after": manifest_outbox_after,
        "inbox_after": manifest_inbox_after,
        "new_outbox_files": _find_new_files(manifest_outbox_before, manifest_outbox_after),
        "new_inbox_files": _find_new_files(manifest_inbox_before, manifest_inbox_after),
        "manifest_result_payload": manifest_result_payload,
        "record_after_manifest": {
            "record_id": manifest_record.get("id"),
            "Reason": (manifest_record.get("fields") or {}).get("Reason "),
        },
    }

    report_path = REPORT_DIR / f"approval_manifest_trace_{run_id}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "done", "report_path": str(report_path), "run_id": run_id}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
