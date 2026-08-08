import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests


def _request_json(
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 20,
) -> Tuple[int, Dict[str, Any]]:
    res = requests.request(method, url, params=params, json=body, timeout=timeout)
    try:
        payload = res.json()
    except Exception:
        payload = {"_raw": res.text}
    return res.status_code, payload


def _assert(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def _load_dashboard_users(base_url: str, actor_username: str) -> List[Dict[str, Any]]:
    status_code, payload = _request_json(
        "GET",
        f"{base_url}/api/settings/dashboard_users",
        params={"actor_username": actor_username},
        timeout=20,
    )
    _assert(status_code == 200, f"GET dashboard_users failed: {status_code} {payload}")
    _assert(payload.get("status") == "success", f"GET dashboard_users not success: {payload}")
    raw_value = payload.get("value")
    if isinstance(raw_value, str) and raw_value.strip():
        try:
            raw_value = json.loads(raw_value)
        except Exception:
            raw_value = []
    if not isinstance(raw_value, list):
        return []
    return [u for u in raw_value if isinstance(u, dict)]


def _save_dashboard_users(base_url: str, users: List[Dict[str, Any]], actor: Dict[str, Any]) -> Dict[str, Any]:
    status_code, payload = _request_json(
        "POST",
        f"{base_url}/api/settings/dashboard_users",
        body={"value": users, "actor": actor},
        timeout=25,
    )
    _assert(status_code == 200, f"POST dashboard_users failed: {status_code} {payload}")
    _assert(payload.get("status") == "success", f"POST dashboard_users not success: {payload}")
    return payload


def _find_user(users: List[Dict[str, Any]], username: str) -> Optional[Dict[str, Any]]:
    for u in users:
        if str(u.get("username") or "").strip() == username:
            return u
    return None


def _evolution_message_payload(instance_name: str, sender_phone: str, text: str, message_id: str) -> Dict[str, Any]:
    remote_jid = f"{sender_phone}@s.whatsapp.net"
    return {
        "event": "messages.upsert",
        "instance": {"instanceName": instance_name},
        "data": {
            "key": {
                "remoteJid": remote_jid,
                "fromMe": False,
                "id": message_id,
            },
            "message": {"conversation": text},
        },
    }


def _read_last_jsonl_lines(path: str, max_lines: int = 30) -> List[str]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    return [line for line in lines[-max_lines:] if str(line or "").strip()]


def _pi_actor_slug(username: str) -> str:
    username = str(username or "").strip().lower()
    actor_key = f"u:{username}" if username else ""
    safe = "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in actor_key.lower())
    safe = safe.strip("._-")
    return safe


def run():
    base_url = str(os.environ.get("E2E_BASE_URL") or "http://127.0.0.1:5001").rstrip("/")
    internal_instance = str(os.environ.get("E2E_INTERNAL_INSTANCE") or "fts_internal_notifications").strip()

    actor_admin = {
        "id": "admin",
        "username": "admin",
        "name": "Admin Manager",
        "role": "Admin",
    }

    test_username = str(os.environ.get("E2E_TEST_USERNAME") or "tool_tester").strip()
    test_phone = str(os.environ.get("E2E_TEST_PHONE") or "201000000001").strip()
    unauthorized_phone = str(os.environ.get("E2E_UNAUTHORIZED_PHONE") or "201000000099").strip()
    allow_intents = os.environ.get("E2E_TEST_ALLOW_INTENTS")
    allow_intents_list = (
        [v.strip() for v in str(allow_intents).split(",") if v.strip()]
        if allow_intents is not None
        else ["general_qa"]
    )

    print(json.dumps({"step": "probe_backend", "url": base_url}, ensure_ascii=False))
    status_code, payload = _request_json("GET", f"{base_url}/api/system/status", timeout=10)
    _assert(status_code == 200 and payload.get("status") == "success", f"Backend not ready: {status_code} {payload}")

    original_users = _load_dashboard_users(base_url, actor_admin["username"])
    _assert(len(original_users) > 0, "dashboard_users empty (cannot run test safely)")

    try:
        print(json.dumps({"step": "upsert_test_user", "username": test_username}, ensure_ascii=False))
        users = list(original_users)
        existing = _find_user(users, test_username)
        base_user = existing if isinstance(existing, dict) else {}
        test_user = {
            "id": str(base_user.get("id") or f"e2e_{int(time.time())}"),
            "username": test_username,
            "name": str(base_user.get("name") or "Tool Tester"),
            "role": str(base_user.get("role") or "Agent"),
            "allowedLocations": list(base_user.get("allowedLocations") or ["NeedHelp"]),
            "toolPhone": test_phone,
            "allowIntents": allow_intents_list,
        }
        users = [u for u in users if str(u.get("username") or "").strip() != test_username]
        users.append(test_user)
        _save_dashboard_users(base_url, users, actor_admin)

        refreshed = _load_dashboard_users(base_url, actor_admin["username"])
        saved_user = _find_user(refreshed, test_username) or {}
        _assert(str(saved_user.get("toolPhone") or "") == test_phone, f"toolPhone not saved: {saved_user}")
        got_intents = saved_user.get("allowIntents") or []
        _assert(isinstance(got_intents, list) and set(got_intents) == set(allow_intents_list), f"allowIntents not saved: {saved_user}")
        print(json.dumps({"step": "dashboard_users_ok", "saved_user": saved_user}, ensure_ascii=False))

        print(json.dumps({"step": "admin_user_activity_primary_admin"}, ensure_ascii=False))
        status_code, payload = _request_json(
            "GET",
            f"{base_url}/api/admin/user_activity",
            params={"actor_username": "admin", "target_username": test_username, "last": 50},
            timeout=20,
        )
        _assert(status_code == 200 and payload.get("status") == "success", f"admin user_activity failed: {status_code} {payload}")
        _assert(isinstance(((payload.get("data") or {}).get("conversation") or []), list), f"conversation not list: {payload}")
        print(json.dumps({"step": "admin_user_activity_ok", "data_keys": list((payload.get("data") or {}).keys())}, ensure_ascii=False))

        print(json.dumps({"step": "admin_user_activity_non_admin_should_fail"}, ensure_ascii=False))
        status_code, payload = _request_json(
            "GET",
            f"{base_url}/api/admin/user_activity",
            params={"actor_username": test_username, "target_username": test_username, "last": 20},
            timeout=20,
        )
        _assert(status_code in (401, 403), f"Expected forbidden for non-admin: {status_code} {payload}")
        print(json.dumps({"step": "non_admin_forbidden_ok", "status_code": status_code, "payload": payload}, ensure_ascii=False))

        print(json.dumps({"step": "internal_webhook_unauthorized_sender"}, ensure_ascii=False))
        status_code, payload = _request_json(
            "POST",
            f"{base_url}/api/internal_notifications/whatsapp/webhook",
            body=_evolution_message_payload(internal_instance, unauthorized_phone, "hello", f"e2e_unauth_{int(time.time())}"),
            timeout=10,
        )
        _assert(status_code == 200 and payload.get("status") == "success", f"unauthorized webhook failed: {status_code} {payload}")
        _assert(payload.get("message") == "ignored_unauthorized_sender" or payload.get("message") == "ignored_other_instance" or "message" not in payload, f"unexpected unauthorized webhook response: {payload}")
        print(json.dumps({"step": "internal_webhook_unauthorized_ok", "payload": payload}, ensure_ascii=False))

        print(json.dumps({"step": "internal_webhook_authorized_sender"}, ensure_ascii=False))
        status_code, payload = _request_json(
            "POST",
            f"{base_url}/api/internal_notifications/whatsapp/webhook",
            body=_evolution_message_payload(internal_instance, test_phone, "حالة الواتساب", f"e2e_auth_{int(time.time())}"),
            timeout=10,
        )
        _assert(status_code == 200 and payload.get("status") == "success", f"authorized webhook failed: {status_code} {payload}")
        print(json.dumps({"step": "internal_webhook_authorized_ack", "payload": payload}, ensure_ascii=False))

        actor_slug = _pi_actor_slug(test_username)
        conv_path = os.path.join(
            os.getcwd(),
            "runtime",
            "pi_brain",
            "users",
            actor_slug,
            "conversations",
            "internal_assistant.jsonl",
        )
        deadline = time.time() + 12
        while time.time() < deadline:
            if os.path.exists(conv_path) and os.path.getsize(conv_path) > 0:
                break
            time.sleep(0.6)
        lines = _read_last_jsonl_lines(conv_path, 10)
        _assert(len(lines) > 0, f"conversation jsonl not written: {conv_path}")
        print(json.dumps({"step": "conversation_jsonl_ok", "path": conv_path, "tail": lines[-3:]}, ensure_ascii=False))

        print(json.dumps({"step": "done", "status": "success"}, ensure_ascii=False))
    finally:
        print(json.dumps({"step": "restore_dashboard_users"}, ensure_ascii=False))
        _save_dashboard_users(base_url, original_users, actor_admin)


if __name__ == "__main__":
    run()
