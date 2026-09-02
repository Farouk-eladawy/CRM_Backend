# -*- coding: utf-8 -*-
"""
Register Collecting On Date Trip Internal Notification workflow.

المطلوب (من المدير — 2026-09-02):
  عند إضافة قيمة في حقل Collecting on date Trip داخل View
  Collecting On Data Trip (viwLCrbJAim0LSR1a / tblJodXmOWKiYqiXS)
  يُرسل واتساب إلى +201128174899 بالقالب Collecting Booking Alert.

قواعد النظام المطبقة:
  - يعتمد على السكربت الموجود internal_view_notify.py (وضع mode=collecting).
  - لا حاجة لإعادة تشغيل السيرفر: محرك الأتمتة يقرأ automation_workflows في كل tick.
  - نسخة احتياطية كاملة من جدول automation_workflows قبل أي تعديل.
  - upsert_workflow (إضافة فقط — لا حذف لأي سجل).
  - أول تشغيل يعلّم السجلات الحالية في الـ View كـ seen حتى لا تُرسل الحجوزات القديمة.
"""
import sys
import io
import json
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import automation_db
from fts_paths import get_data_path

BACKUP_FILE = get_data_path(
    f"automation_workflows.backup_before_collecting_on_date_trip_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
)
try:
    existing = automation_db.list_workflows()
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"[Backup] Saved {len(existing)} existing workflows -> {BACKUP_FILE}")
except Exception as e:
    print(f"[Backup] WARNING: could not backup automation_workflows: {e}")

WID = "int_notify_collecting_on_date_trip_v1"
steps = [
    {
        "type": "http_request",
        "method": "POST",
        "url": "http://127.0.0.1:5001/api/automation/run_script",
        "headers": {"content-type": "application/json"},
        "timeout_seconds": 90,
        "body": {
            "script_name": "internal_view_notify.py",
            "scenario_id": WID,
            "view": "Collecting On Data Trip",
            "view_id": "viwLCrbJAim0LSR1a",
            "table_id": "tblJodXmOWKiYqiXS",
            "base_id": "appTp5YgSp9DV2HYc",
            "mode": "collecting",
            "phones": ["+201128174899"],
            "include_customer_phone": False,
            "trigger_field": "Collecting on date Trip",
            "bootstrap_seen_on_first_run": True,
            "max_records": 25,
            "dry_run": False,
        },
    }
]

payload = {
    "id": WID,
    "name": "Collecting On Date Trip",
    "description": (
        "Internal notification: when Collecting on date Trip gets a value "
        "(View: Collecting On Data Trip / viwLCrbJAim0LSR1a / table List). "
        "Sends WhatsApp to +201128174899 with Collecting Booking Alert "
        "(Ref / Trip / Option / Date / Pax / Collecting / Pickup Hotel). "
        "First run marks current view records as already notified. "
        "After that it sends only for new or changed Collecting values. "
        "Runs every minute via the automation engine without a server restart."
    ),
    "enabled": True,
    "category": "internal",
    "trigger_type": "schedule",
    "trigger_config": {"every_minutes": 1},
    "steps": steps,
}

created = automation_db.upsert_workflow(payload)
print("=== Workflow created/updated ===")
print("ID:", created.get("id"))
print("NAME:", created.get("name"))
print("ENABLED:", created.get("enabled"))
print("CATEGORY:", created.get("category"))
print("TRIGGER:", created.get("trigger_type"))
print("TRIGGER_CONFIG:", created.get("trigger_config_json"))
print("STEPS count:", len(json.loads(created.get("steps_json") or "[]")))
print("STEPS:", created.get("steps_json"))
