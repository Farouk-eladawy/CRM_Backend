# -*- coding: utf-8 -*-
"""
Register Religious "شكرا مش مهتم" Auto-Reply workflow (Exact Match لحظي).

تحديث 2026-09-03: تحديث نص الرد فقط إلى الرسالة الجديدة من المدير (نفس الاسم، نفس
الكلمة، نفس نسبة التطابق 100% Exact Match). لا تغيير في الـ steps أو الفلاتر
(Religious فقط + فيسبوك/واتساب فقط).
"""
import sys
import io
import json
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import automation_db
from fts_paths import get_data_path

BACKUP_FILE = get_data_path(
    f"automation_workflows.backup_before_shokran_mesh_mohtam_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
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
        "timeout_seconds": 30,
        "body": {
            "script_name": "religious_shokran_mesh_mohtam_autoreply.py",
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
    "id": "religious_shokran_mesh_mohtam_autoreply_v1",
    "name": "شكرا مش مهتم - Religious Auto-Reply - ديني (Exact Match لحظي)",
    "description": (
        "الرد التلقائي اللحظي على رسائل القسم الديني (Religious فقط - فيسبوك/واتساب) "
        "عندما يرسل العميل عبارة 'شكرا مش مهتم' بنسبة تطابق 100% (Exact Match - أي "
        "كلمة إضافية قبل النص أو بعده تكسر المساواة → لا رد). الرد (تحديث 2026-09-03): "
        "'تمام يا فندم، شكرًا لحضرتك على وقتك 🙏 مش هنبعت لحضرتك رسائل تانية، ولو "
        "احتجت أي حاجة في الحج أو العمرة في أي وقت، إحنا موجودين. ربنا يكتبلك الزيارة "
        "قريب 🤲'. يُرسل مرة واحدة فقط لكل رسالة (حجز ذري Atomic Claim يمنع التكرار "
        "من Webhook duplicate deliveries). احترام auto_reply_hold_until و needs_help "
        "(لا نتداخل مع موظف بشري). تخطي نافذة Meta الـ 24 ساعة تلقائياً لأن هذا رد "
        "مباشر على رسالة العميل وليس برومو مستقل. القسم الديني فقط (فلترة صارمة - لا "
        "يمس أي قسم آخر — قاعدة النظام 15)."
    ),
    "enabled": True,
    "category": "customer",
    "trigger_type": "message_received",
    "trigger_config": {"source": "Any"},
    "steps": steps,
}

created = automation_db.upsert_workflow(payload)
print("=== Workflow created/updated ===")
print("ID:", created.get("id"))
print("NAME:", created.get("name"))
print("ENABLED:", created.get("enabled"))
print("TRIGGER:", created.get("trigger_type"))
