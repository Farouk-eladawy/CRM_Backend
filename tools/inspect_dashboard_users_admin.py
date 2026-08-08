import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import chat_db


def main():
    raw = chat_db.get_setting("dashboard_users")
    has_setting = bool(raw and str(raw).strip())
    users = []
    if isinstance(raw, str) and raw.strip():
        try:
            users = json.loads(raw)
        except Exception:
            users = []
    elif isinstance(raw, list):
        users = raw

    admin = None
    for u in users:
        if isinstance(u, dict) and str(u.get("username") or "").strip().lower() == "admin":
            admin = u
            break

    summary = {
        "has_dashboard_users_setting": has_setting,
        "users_count": len(users) if isinstance(users, list) else 0,
        "admin_in_setting": bool(admin),
        "admin_summary": None,
    }
    if isinstance(admin, dict):
        summary["admin_summary"] = {
            "id": admin.get("id"),
            "username": admin.get("username"),
            "name": admin.get("name"),
            "role": admin.get("role"),
            "toolPhone": admin.get("toolPhone"),
            "phone": admin.get("phone"),
            "allowedLocations_count": len(admin.get("allowedLocations") or []) if isinstance(admin.get("allowedLocations"), list) else None,
            "allowIntents_count": len(admin.get("allowIntents") or []) if isinstance(admin.get("allowIntents"), list) else None,
        }

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
