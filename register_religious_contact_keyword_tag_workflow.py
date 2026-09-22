# -*- coding: utf-8 -*-
"""Register Religious Contact keyword → auto-tag workflow."""
import sys
import io
import json
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import automation_db
from fts_paths import get_data_path

BACKUP_FILE = get_data_path(
    f"automation_workflows.backup_before_contact_keyword_tag_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
)
try:
    existing = automation_db.list_workflows()
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"[Backup] Saved {len(existing)} existing workflows -> {BACKUP_FILE}")
except Exception as e:
    print(f"[Backup] WARNING: could not backup automation_workflows: {e}")

steps = [
    {
        "type": "guard",
        "path": "event.payload.location",
        "contains_any": ["Religious"],
        "case_insensitive": True,
    },
    {
        "type": "guard",
        "path": "event.payload.source",
        "contains_any": ["facebook", "whatsapp"],
        "case_insensitive": True,
    },
    {
        "type": "http_request",
        "method": "POST",
        "url": "http://127.0.0.1:5001/api/automation/run_script",
        "headers": {"content-type": "application/json"},
        "timeout_seconds": 20,
        "body": {
            "script_name": "religious_contact_keyword_tag.py",
            "chat_id": "{{event.payload.chat_id}}",
            "message_body": "{{event.payload.message_body}}",
            "source": "{{event.payload.source}}",
            "sender_identifier": "{{event.payload.sender_identifier}}",
            "location": "{{event.payload.location}}",
            "receiving_phone_id": "{{event.payload.receiving_phone_id}}",
            "incoming_external_message_id": "{{event.payload.incoming_external_message_id}}",
        },
    },
]

payload = {
    "id": "religious_contact_keyword_tag_v1",
    "name": "Contact Keyword Auto-Tag - Religious",
    "description": (
        "عند رسالة عميل في القسم الديني: إذا وُجدت كلمة من قواعد تاج Contact "
        "(religious_contact_tag_rules.json) يُضاف التاج تلقائياً في Contact. "
        "لا يرسل أي رد للعميل — تصنيف فقط."
    ),
    "enabled": True,
    "category": "customer",
    "trigger_type": "message_received",
    "trigger_config": {"source": "Any"},
    "steps": steps,
}

try:
    automation_db.upsert_workflow(payload)
    print(f"[OK] Registered workflow: {payload['id']}")
except Exception as e:
    # Fallback older API names
    try:
        if hasattr(automation_db, "save_workflow"):
            automation_db.save_workflow(payload)
            print(f"[OK] Registered via save_workflow: {payload['id']}")
        elif hasattr(automation_db, "create_workflow"):
            automation_db.create_workflow(payload)
            print(f"[OK] Registered via create_workflow: {payload['id']}")
        else:
            raise e
    except Exception as e2:
        print(f"[ERROR] Failed to register workflow: {e2}")
        raise
