# -*- coding: utf-8 -*-
"""
Register the 'Religious Umrah 8-Day Follow-Up - ديني' workflow
in automation_workflows (chat_history.db).

المطلوب (من المدير — برومبت نظام المتابعة التلقائية، برنامج عمرة الـ٨ أيام):
  - Workflow بنوع trigger_type = "schedule" يشتغل كل 60 دقيقة.
  - الخطوة steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "religious_umrah_8day_followup.py"}.
  - الاسم يحتوي على "Religious" و "ديني" حتى يظهر في لوحة المدير الديني
    (الفلاتر في الواجهة تعتمد على هذه الكلمات في الاسم — قاعدة النظام D)،
    لأن كل محادثات الإعلان المستهدف تنتمي لقسم Religious (location='Religious').
  - لا حاجة لإعادة تشغيل السيرفر: محرك الأتمتة يقرأ قاعدة البيانات
    automation_workflows في كل tick (hot-load).
  - شرط التفعيل الحصري داخل السكربت: facebook_ad_id = 120248067160660757 فقط.
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
        "body": {"script_name": "religious_umrah_8day_followup.py"},
    }
]

payload = {
    "id": "religious_umrah_8day_followup_v1",
    "name": "Religious Umrah 8-Day Follow-Up - ديني (عمرة الـ٨ أيام - إعلان 120248067160660757)",
    "description": (
        "نظام المتابعة التلقائية لبرنامج عمرة الـ٨ أيام — يُطبَّق حصرياً على "
        "المحادثات الواردة من الإعلان Ad ID: 120248067160660757 فقط "
        "(فلترة صارمة في SQL من الجذور). دورة فحص كل 60 دقيقة، والوقت يُحسب "
        "من آخر رسالة من العميل (وليس منّا): المتابعة 1 بعد 1-3 ساعات، "
        "المتابعة 2 بعد 6-9 ساعات، المتابعة 3 بعد 21-22 ساعة — كل رسالة مرة "
        "واحدة فقط. إذا ردّ العميل بأي رسالة: أوقف التسلسل وأعد ضبط العدّاد "
        "من الصفر (رده الجديد = بداية نافذة جديدة، والرسائل الثلاث تعود متاحة). "
        "لا إرسال بعد 23 ساعة (نافذة ميتا). شروط الإيقاف النهائي: رقم موبايل "
        "(وسم «Lead جاهز للاتصال» + إشعار فريق)، أو تأكيد حجز/تحويل عربون "
        "(تحويل لمسار الحجز)، أو رفض صريح/طلب عدم التواصل (إيقاف دائم بالـ "
        "sender)، أو تدخّل موظف بشري (needs_help/is_closed). كلمة «موعد» → "
        "إرسال مواعيد السفر المتاحة وخطوات الحجز + إعادة ضبط العدّاد. "
        "نصوص الرسائل الثلاث كما هي بالحرف من طلب المدير."
    ),
    "enabled": True,
    "category": "customer",
    "trigger_type": "schedule",
    "trigger_config": {"every_minutes": 60},
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
