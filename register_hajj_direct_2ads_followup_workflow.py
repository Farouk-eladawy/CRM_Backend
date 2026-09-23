# -*- coding: utf-8 -*-
"""
Register the 'Religious - تسلسل فولو أب عملاء إعلان الحج المباشر' workflow
in the built-in automation engine (automation_workflows table).

المطلوب (من المدير - 2026-09-23):
  - على أي محادثة أول رسالة فيها من الإعلانين التاليين فقط:
      120248934377370757
      120248934520430757
  - بعد أن يُرسل للعميل شرح برنامج الحج المباشر ولم يردّ ولم يرسل رقمه:
      الرسالة ١: بعد ٣ ساعات من آخر رسالة للعميل
      الرسالة ٢: بعد ١٠ ساعات
      الرسالة ٣: بعد ٢١ ساعة
      وممنوع أي إرسال بعد مرور ٢٣ ساعة (نافذة Meta 24h).
  - إيقاف فوري عند: رد العميل / إرسال رقم / عدم الاهتمام / التحويل لمبيعات /
    انتهاء يوم الأربعاء ٣٠ سبتمبر / "السنة دي مش مناسبة".

قرارات هندسية (قواعد النظام):
  - trigger_type = "schedule" مع every_minutes=30 (فحص دوري).
  - steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "hajj_direct_2ads_followup.py"}.
  - السكربت يفلتر من الجذور (facebook_ad_id IN 2 إعلان).
  - القاعدة D: الاسم يحتوي "Religious" و"ديني" حتى يظهر في لوحة المدير الديني.
  - لا تعديل على ai_agent.py ولا إعادة تشغيل للسيرفر (محرك الأتمتة hot-load).
  - نسخة احتياطية من automation_workflows قبل الإضافة (قاعدة النظام 3).
"""
import sys
import io
import json
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import automation_db
from fts_paths import get_data_path

# =============================================================================
# 1) نسخة احتياطية من automation_workflows قبل الإضافة (قاعدة النظام 3)
# =============================================================================
BACKUP_FILE = get_data_path(
    f"automation_workflows.backup_before_hajj_direct_2ads_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
)
try:
    existing = automation_db.list_workflows()
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"[Backup] Saved {len(existing)} existing workflows -> {BACKUP_FILE}")
except Exception as e:
    print(f"[Backup] WARNING: could not backup automation_workflows: {e}")

# =============================================================================
# 2) تسجيل الـ workflow (upsert — إضافة فقط، لا حذف لأي سجل)
# =============================================================================
steps = [
    {
        "type": "http_request",
        "method": "POST",
        "url": "http://127.0.0.1:5001/api/automation/run_script",
        "headers": {"content-type": "application/json"},
        "timeout_seconds": 60,
        "body": {
            "script_name": "hajj_direct_2ads_followup.py",
        },
    },
]

payload = {
    "id": "hajj_direct_2ads_followup_v1",
    # القاعدة D: الاسم يحتوي "Religious" و"ديني" حتى يظهر في لوحة المدير الديني
    "name": "Religious - تسلسل فولو أب عملاء إعلان الحج المباشر (ديني) - إعلانان 120248934377370757/120248934520430757",
    "description": (
        "تسلسل فولو أب تلقائي (٣ رسائل) لعملاء إعلان الحج المباشر Religious "
        "القادمين من الإعلانين (120248934377370757 / 120248934520430757) — "
        "فلترة صارمة من الجذور في SQL (facebook_ad_id IN 2) لا تمس أي إعلان آخر. "
        "شرط البدء: إرسال شرح برنامج الحج المباشر للعميل وعدم ردّه. "
        "المواعيد مقاسة من وقت آخر رسالة أرسلها العميل (وليس من ردنا): "
        "الرسالة ١ بعد ٣ ساعات، الرسالة ٢ بعد ١٠ ساعات، الرسالة ٣ بعد ٢١ ساعة، "
        "وممنوع أي إرسال بعد ٢٣ ساعة (أمان من خطأ Meta #10). Messages تُرسل "
        "بالترتيب وواحدة فقط في الدورة الواحدة. إيقاف فوري عند: رد العميل، إرسال "
        "رقم تليفون (تأكيد + تحويل لمبيعات)، عدم الاهتمام/طلب عدم الإرسال، "
        "'السنة دي مش مناسبة' (تعليم مهتم بالسنة الجاية)، تحويل المحادثة لموظف "
        "مبيعات (needs_help/sales_inbox)، أو انتهاء الأربعاء ٣٠ سبتمبر. "
        "قاعدة التاريخ: لو الإرسال يوم الثلاثاء ٢٩ سبتمبر تُكتب 'بكرة الأربعاء ٣٠ "
        "سبتمبر'، ولو الأربعاء ٣٠ سبتمبر تُكتب 'النهارده الأربعاء ٣٠ سبتمبر'. "
        "التوقيت بتوقيت القاهرة (get_cairo_time) والحالة في ملف JSON محلي "
        "(لا load_state). لا إعادة تشغيل للسيرفر."
    ),
    "enabled": True,
    "category": "customer",
    "trigger_type": "schedule",
    "trigger_config": {"every_minutes": 30},
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
