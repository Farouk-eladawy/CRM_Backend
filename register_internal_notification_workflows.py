"""
One-shot: seed / refresh Internal Notification automation workflows from
workflows/internal_notification_scenarios.json into SQLite.

Usage:
  python register_internal_notification_workflows.py
  python register_internal_notification_workflows.py --force   # overwrite steps/config
  python register_internal_notification_workflows.py --enable  # set enabled=1 (careful if Make still on)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from fts_paths import get_data_path
import automation_db


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Overwrite existing workflow definitions")
    parser.add_argument("--enable", action="store_true", help="Create/update with enabled=True and dry_run=False")
    parser.add_argument("--port", type=int, default=5001)
    args = parser.parse_args()

    automation_db.init_db()
    path = os.path.join(get_data_path("workflows"), "internal_notification_scenarios.json")
    if not os.path.exists(path):
        print(f"Missing scenarios file: {path}")
        return 1
    with open(path, "r", encoding="utf-8") as f:
        scenarios = list((json.load(f) or {}).get("scenarios") or [])

    port = int(args.port or 5001)
    enabled = bool(args.enable)
    dry_run = not enabled
    created = 0
    updated = 0
    skipped = 0

    for sc in scenarios:
        if not isinstance(sc, dict):
            continue
        wid = str(sc.get("id") or "").strip()
        if not wid:
            continue
        existing = automation_db.get_workflow(wid)
        if existing and not args.force:
            skipped += 1
            continue

        name = str(sc.get("name") or wid).strip()
        source_file = str(sc.get("source_file") or "").strip()
        trigger_kind = str(sc.get("trigger") or "").strip().lower()
        mode = str(sc.get("mode") or "last_minute").strip()
        desc = (
            f"Imported from Make Internal Notification blueprint: {source_file}. "
            "Enable only after disabling the Make scenario to avoid duplicate WhatsApp alerts."
        )

        if trigger_kind == "webhook":
            slug = str(sc.get("webhook_slug") or "").strip()
            wf = {
                "id": wid,
                "name": name,
                "description": desc + (f" Webhook: /api/internal_notifications/webhook/{slug}" if slug else ""),
                "enabled": enabled,
                "category": "internal",
                "trigger_type": "manual",
                "trigger_config": {"webhook_slug": slug},
                "steps": [
                    {
                        "type": "http_request",
                        "method": "POST",
                        "url": f"http://127.0.0.1:{port}/api/automation/run_script",
                        "headers": {"content-type": "application/json"},
                        "timeout_seconds": 60,
                        "body": {
                            "script_name": "internal_webhook_notify.py",
                            "webhook_slug": slug,
                            "dry_run": dry_run,
                        },
                    }
                ],
            }
        else:
            wf = {
                "id": wid,
                "name": name,
                "description": desc,
                "enabled": enabled,
                "category": "internal",
                "trigger_type": "schedule",
                "trigger_config": {"every_minutes": 1},
                "steps": [
                    {
                        "type": "http_request",
                        "method": "POST",
                        "url": f"http://127.0.0.1:{port}/api/automation/run_script",
                        "headers": {"content-type": "application/json"},
                        "timeout_seconds": 90,
                        "body": {
                            "script_name": "internal_view_notify.py",
                            "scenario_id": wid,
                            "view": sc.get("view_label"),
                            "view_id": sc.get("view_id"),
                            "table_id": sc.get("table_id"),
                            "base_id": sc.get("base_id"),
                            "mode": mode,
                            "phones": sc.get("phones") or [],
                            "include_customer_phone": bool(sc.get("include_customer_phone", True)),
                            "max_records": 25,
                            "dry_run": dry_run,
                        },
                    }
                ],
            }

        automation_db.upsert_workflow(wf)
        if existing:
            updated += 1
            print(f"UPDATED {wid} | {name}")
        else:
            created += 1
            print(f"CREATED {wid} | {name}")

    print(f"Done. created={created} updated={updated} skipped={skipped} total={len(scenarios)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
