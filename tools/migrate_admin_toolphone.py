import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import chat_db


PRIMARY_ADMIN_USERNAME = "admin"
TARGET_TOOL_PHONE = "201010323484"


def main():
    raw = chat_db.get_setting("dashboard_users")
    if not raw or not str(raw).strip():
        print(json.dumps({"status": "skipped", "reason": "dashboard_users_setting_missing"}))
        return

    users = []
    try:
        users = json.loads(raw) if isinstance(raw, str) else (raw if isinstance(raw, list) else [])
    except Exception:
        users = []

    if not isinstance(users, list) or not users:
        print(json.dumps({"status": "skipped", "reason": "dashboard_users_empty"}))
        return

    updated = False
    for u in users:
        if not isinstance(u, dict):
            continue
        if str(u.get("username") or "").strip().lower() != PRIMARY_ADMIN_USERNAME:
            continue
        current = "".join(ch for ch in str(u.get("toolPhone") or "") if ch.isdigit())
        if not current:
            u["toolPhone"] = TARGET_TOOL_PHONE
            updated = True
        role = str(u.get("role") or "").strip()
        if role.lower() != "admin":
            u["role"] = "Admin"
            updated = True
        break

    if not updated:
        print(json.dumps({"status": "ok", "updated": False}))
        return

    chat_db.set_setting("dashboard_users", json.dumps(users, ensure_ascii=False))
    print(json.dumps({"status": "ok", "updated": True, "admin_toolPhone": TARGET_TOOL_PHONE}))


if __name__ == "__main__":
    main()

