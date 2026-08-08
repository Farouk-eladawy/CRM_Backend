# -*- coding: utf-8 -*-
"""Register the new '15 Days Exact Keyword Auto-Reply' workflow in automation_workflows."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import automation_db

steps = [
    {
        "type": "guard",
        "path": "event.payload.location",
        "contains_any": ["Religious"],
        "case_insensitive": True,
    },
    {
        "type": "http_request",
        "method": "POST",
        "url": "http://127.0.0.1:5001/api/automation/run_script",
        "body": {
            "script_name": "religious_15day_exact_keyword_autoreply.py",
            "chat_id": "{{event.payload.chat_id}}",
            "message_body": "{{event.payload.message_body}}",
            "source": "{{event.payload.source}}",
            "sender_identifier": "{{event.payload.sender_identifier}}",
            "location": "{{event.payload.location}}",
            "receiving_phone_id": "{{event.payload.receiving_phone_id}}",
            "incoming_external_message_id": "{{event.payload.incoming_external_message_id}}",
        },
        "timeout_seconds": 30,
    },
]

payload = {
    "id": "religious_15day_exact_keyword_autoreply_v1",
    "name": "15 Days Exact Keyword Auto-Reply - Religious - عمرة ١٥ يوم (لحظي)",
    "description": (
        "Workflow جديد ومستقل 100% لبرنامج عمرة ١٥ يوم (Exact Match لحظي): "
        "يرد تلقائياً وفوراً على رسائل عملاء القسم الديني (Religious فقط) عندما تكون "
        "الرسالة مطابقة بالكامل (Exact Match) لإحدى الكلمات الثلاث المعتمدة: "
        "(١) ابعتولي برنامج الـ١٥ يوم بالتفصيل 📋 — (٢) إيه أقرب مواعيد السفر المتاحة؟ 🗓 — "
        "(٣) السعر ٤٠٬٩٥٠ شامل إيه بالظبط؟ 💰. "
        "ممنوع Contains/StartsWith/EndsWith: أي كلمة إضافية قبل النص أو بعده تمنع الرد. "
        "كل كلمة ترسل ردها الخاص مرة واحدة فقط (حجز ذري Atomic Claim يمنع التكرار). "
        "لا يلمس أي Workflow موجود ولا strict_qa_rules."
    ),
    "enabled": True,  # تفعيل فوري (لحظي)
    "category": "customer",
    "trigger_type": "message_received",
    "trigger_config": {"source": "Any"},
    "steps": steps,
}

created = automation_db.upsert_workflow(payload)
print("=== Workflow created ===")
print("ID:", created.get("id"))
print("NAME:", created.get("name"))
print("ENABLED:", created.get("enabled"))
print("TRIGGER:", created.get("trigger_type"))
print("STEPS count:", len(json.loads(created.get("steps_json") or "[]")))
