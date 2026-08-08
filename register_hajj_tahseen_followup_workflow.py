# -*- coding: utf-8 -*-
"""
Register the 'Religious Hajj Tahseen Follow-Up - ديني' workflow
in automation_workflows (chat_history.db).

المطلوب (من المدير — 2026-08-02):
  - Workflow بنوع trigger_type = "schedule" يشتغل كل 5 دقائق.
  - الخطوة steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "hajj_tahseen_followup.py"}.
  - الاسم يحتوي على "Religious" و "ديني" حتى يظهر في لوحة المدير الديني
    (الفلاتر في الواجهة تعتمد على هذه الكلمات في الاسم).
  - لا حاجة لإعادة تشغيل السيرفر: محرك الأتمتة يقرأ قاعدة البيانات
    automation_workflows في كل tick (hot-load).
"""
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import automation_db

steps = [
    {
        "type": "http_request",
        "method": "POST",
        "url": "http://127.0.0.1:5001/api/automation/run_script",
        "headers": {"content-type": "application/json"},
        "timeout_seconds": 60,
        "body": {"script_name": "hajj_tahseen_followup.py"},
    }
]

payload = {
    "id": "hajj_tahseen_followup_religious_v1",
    "name": "Religious Hajj Tahseen Follow-Up - ديني (إعلان طيران تحسين 120246971083710757)",
    "description": (
        "نظام Follow-Up تلقائي لبرنامج حج طيران تحسين — يطبَّق حصرياً على المحادثات "
        "الواردة من الإعلان Ad ID: 120246971083710757 فقط. التسلسل الثلاثي: "
        "الرسالة 1 بعد ساعتين، الرسالة 2 بعد 8 ساعات، الرسالة 3 بعد 21 ساعة "
        "(قبل الساعة 22 كحد أقصى) — جميعها داخل نافذة Meta الـ 24 ساعة من آخر "
        "رسالة عميل. معالجة كلمات مفتاحية (ملخص / أحجز / رقم واتساب) وتحويل "
        "المحادثات لموظف خدمة العملاء، وتصنيف الزرار الأول (إزاي أحجز؟ = lead "
        "ساخن بعد 45 دقيقة)، ووضع tag 'no-response-hajj-tahseen' عند اكتمال "
        "التسلسل بدون رد. لا يلمس أي Workflow آخر ولا أي قسم آخر."
    ),
    "enabled": True,
    "category": "customer",
    "trigger_type": "schedule",
    "trigger_config": {"every_minutes": 5},
    "steps": steps,
}

created = automation_db.upsert_workflow(payload)
print("=== Workflow created/updated ===")
print("ID:", created.get("id"))
print("NAME:", created.get("name"))
print("ENABLED:", created.get("enabled"))
print("TRIGGER:", created.get("trigger_type"))
print("TRIGGER_CONFIG:", created.get("trigger_config_json"))
print("STEPS count:", len(json.loads(created.get("steps_json") or "[]")))
print("STEPS:", created.get("steps_json"))
