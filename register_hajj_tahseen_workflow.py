# -*- coding: utf-8 -*-
"""
Register the 'Hajj Tahseen 3-Stage Follow-Up' workflow in automation_workflows.

يتم تسجيل السير العمل في محرك الأتمتة الأساسي دون إعادة تشغيل السيرفر
(يقرأ محرك الأتمتة قاعدة البيانات دورياً، فالتسجيل هنا يفعّله فوراً).

خطوات السير العمل: http_request → POST http://127.0.0.1:5001/api/automation/run_script
مع body: {"script_name": "hajj_tahseen_followup.py"}
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import automation_db

steps = [
    {
        "type": "http_request",
        "method": "POST",
        "url": "http://127.0.0.1:5001/api/automation/run_script",
        "timeout_seconds": 55,
        "body": {
            "script_name": "hajj_tahseen_followup.py",
        },
    }
]

payload = {
    "id": "hajj_tahseen_3stage_followup_v1",
    # الاسم يحتوي على "Religious" و "ديني" حتى يظهر السير العمل للمدير الديني فقط في الداشبورد
    "name": "Hajj Tahseen 3-Stage Follow-Up - Religious - حج طيران تحسين (ديني)",
    "description": (
        "Workflow جديد ومستقل 100% لإعلان برنامج حج طيران تحسين (Ad ID: 120246971083710757) فقط. "
        "تسلسل متابعة ثلاثي يقاس من آخر رسالة نصية حقيقية من العميل: "
        "(1) رسالة المتابعة الأولى بعد ساعتين (أو 45 دقيقة للـ lead الساخن الذي ضغط زرار "
        "'إزاي أحجز؟' مع محتوى خطوات الحجز)، (2) الثانية بعد 8 ساعات، (3) الثالثة بعد 21 ساعة "
        "وبحد أقصى 22 ساعة داخل نافذة Meta الـ 24 ساعة (تجنب Error #10). "
        "كلمات مفتاحية: 'ملخص' (يرسل ملخص البرنامج الكامل ويعيد ضبط العداد)، "
        "'أحجز' (يرسل خطوات الحجز والمستندات ويحوّل لخدمة العملاء)، "
        "رقم موبايل (تسجيل + تحويل كـ lead ساخن)، طلب إيقاف (opt-out نهائي). "
        "عند اكتمال التسلسل الثلاثي بدون رد: توضع tag باسم no-response-hajj-tahseen ويتوقف. "
        "الفلاتر في SQL من الجذور: facebook_ad_id = '120246971083710757' فقط — لا يلمس أي إعلان "
        "أو قسم آخر. التوقيت بتوقيت القاهرة chat_db.get_cairo_time(). "
        "الحالة محفوظة في ملف محلي hajj_tahseen_followup_state.json عبر fts_paths.get_data_path."
    ),
    "enabled": True,  # تفعيل فوري بدون إعادة تشغيل السيرفر
    "category": "customer",
    "trigger_type": "schedule",
    "trigger_config": {"every_minutes": 5},
    "steps": steps,
}

created = automation_db.upsert_workflow(payload)
print("=== Workflow created ===")
print("ID:", created.get("id"))
print("NAME:", created.get("name"))
print("ENABLED:", created.get("enabled"))
print("TRIGGER:", created.get("trigger_type"))
print("STEPS count:", len(json.loads(created.get("steps_json") or "[]")))
