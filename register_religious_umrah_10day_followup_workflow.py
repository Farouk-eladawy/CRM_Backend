# -*- coding: utf-8 -*-
"""
Register the 'Religious Umrah 10-Day Follow-Up - ديني' workflow
in automation_workflows (chat_history.db).

المطلوب (من المدير — برومبت نظام المتابعة التلقائية، برنامج العمرة المريح ١٠ أيام):
  - Workflow بنوع trigger_type = "schedule" يشتغل كل 60 دقيقة.
  - الخطوة steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "religious_umrah_10day_followup.py"}.
  - الاسم يحتوي على "Religious" و "ديني" حتى يظهر في لوحة المدير الديني
    (الفلاتر في الواجهة تعتمد على هذه الكلمات في الاسم — قاعدة النظام D).
  - لا حاجة لإعادة تشغيل السيرفر: محرك الأتمتة يقرأ قاعدة البيانات
    automation_workflows في كل tick (hot-load).
  - شرط التفعيل الحصري داخل السكربت: facebook_ad_id = 120248068201650757 فقط.
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
        "body": {"script_name": "religious_umrah_10day_followup.py"},
    }
]

payload = {
    "id": "religious_umrah_10day_followup_v1",
    "name": "Religious Umrah 10-Day Follow-Up - ديني (العمرة المريح ١٠ أيام - إعلان 120248068201650757)",
    "description": (
        "نظام المتابعة التلقائية لبرنامج العمرة المريح ١٠ أيام — يُطبَّق حصرياً "
        "على المحادثات الواردة من الإعلان Ad ID: 120248068201650757 فقط "
        "(فلترة صارمة في SQL من الجذور). دورة فحص كل 60 دقيقة: المتابعة 1 بعد "
        "60 دقيقة من آخر رسالة، المتابعة 2 بعد 7 ساعات من آخر رسالة عميل، "
        "المتابعة 3 بعد 22 ساعة (قبل إغلاق نافذة Meta الـ 24 ساعة) — كل رسالة "
        "مرة واحدة بالترتيب 1←2←3. ساعات الليل [12م-8ص بتوقيت القاهرة]: تأجيل "
        "الإرسال لما بعد 8 صباحاً، مع استثناء وحيد: إذا كانت النافذة ستُغلق قبل "
        "8 صباحاً تُرسل المتابعة 3 فوراً. شروط الإيقاف: أي رد من العميل، أو "
        "استلام رقم تليفون (تأكيد + تسجيل + إشعار فريق بشري)، أو نية حجز "
        "(تحويل لمسار الحجز)، أو طلب عدم التواصل (إيقاف دائم بالـ sender)، "
        "أو تدخّل موظف بشري (needs_help/is_closed). لا يلمس أي Workflow آخر "
        "ولا أي إعلان أو قسم آخر."
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
