# -*- coding: utf-8 -*-
"""
Register the 'Religious - متابعة الإعلانات الجديدة (ديني)' workflow
in automation_workflows (chat_history.db).

المطلوب (من المدير - 2026-09-11):
  - اسم workflow: "متابعة الإعلانات الجديدة" — مع إلزام كلمة Religious/ديني لأن
    القسم ديني (قاعدة النظام D: لوحة المدير الديني تفلتر بالاسم).
  - على أي رسالة واردة من الإعلانات الخمسة الأتية (مصحّحة لتطابق chat_history.db):
      120248849213600757
      120248848846290757
      120248843843220757
      120248833392320757
      120248731132970757
    (المدير أرسلها بكتابة مختلفة قليلاً لا تطابق أي صف في قاعدة البيانات —
     انظر تفاصيل التصحيح في ملف workflows/religious_new_ads_followup.py)
  - نرسل رسالتي متابعة (مقاستان من آخر رسالة حقيقية للعميل):
      Follow-up 1: بعد 3 ساعات
      Follow-up 2: بعد 23 ساعة (قبل قفل نافذة Meta الـ 24 ساعة بهامش أمان)
  - لو العميل رد في أي وقت → يُعاد ضبط العدّاد من رسالته الأخيرة (الحد الأقصى
    رسالتان) ويتولى المساعد الأساسي الرد عليه.

قرار هندسي:
  - trigger_type = "schedule" مع every_minutes=30 (فحص دوري كل 30 دقيقة).
  - steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "religious_new_ads_followup.py"}
  - السكربت نفسه يفلتر من الجذور (facebook_ad_id IN 5 + location='Religious').
  - لا تعديل على ai_agent.py ولا إعادة تشغيل للسيرفر: محرك الأتمتة hot-load
    من قاعدة البيانات في كل tick.
  - نسخة احتياطية من جدول automation_workflows قبل الإضافة (قاعدة النظام 3).
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
    f"automation_workflows.backup_before_new_ads_followup_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
)
try:
    existing = automation_db.list_workflows()
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"[Backup] Saved {len(existing)} existing workflows -> {BACKUP_FILE}")
except Exception as e:
    print(f"[Backup] WARNING: could not backup automation_workflows: {e}")

# =============================================================================
# 2) تسجيل الـ workflow الجديد (upsert — إضافة فقط، لا حذف لأي سجل)
# =============================================================================
steps = [
    {
        "type": "http_request",
        "method": "POST",
        "url": "http://127.0.0.1:5001/api/automation/run_script",
        "headers": {"content-type": "application/json"},
        "timeout_seconds": 60,
        "body": {
            "script_name": "religious_new_ads_followup.py",
        },
    },
]

payload = {
    "id": "religious_new_ads_followup_v1",
    # القاعدة D: الاسم يحتوي "Religious" و"ديني" حتى يظهر في لوحة المدير الديني
    "name": "Religious - متابعة الإعلانات الجديدة (ديني) - 5 إعلانات",
    "description": (
        "متابعة تلقائية (رسالتا فولو اب) لعملاء القسم الديني Religious ONLY "
        "القادمين من الإعلانات الخمسة الجديدة (120248849213600757 / "
        "120248848846290757 / 120248843843220757 / 120248833392320757 / "
        "120248731132970757) — فلترة صارمة من الجذور في SQL "
        "(facebook_ad_id IN 5 AND location='Religious') لا تمس أي إعلان أو قسم آخر. "
        "الجدول الزمني (مقاس من آخر رسالة حقيقية للعميل): Follow-up 1 بعد 3 ساعات، "
        "Follow-up 2 بعد 23 ساعة (قبل قفل نافذة Meta الـ 24 ساعة بهامش أمان). "
        "لو العميل رد في أي وقت → يُعاد ضبط العدّاد من رسالته الأخيرة ويتولى "
        "المساعد الأساسي الرد عليه (منع السبام). التوقيت بتوقيت القاهرة "
        "(get_cairo_time) والحالة في ملف JSON محلي (لا load_state). يحترم "
        "needs_help / is_closed / auto_reply_hold_until ويوقف فوراً عند إرسال "
        "العميل لرقمه أو إتمام الحجز أو طلب إيقاف الرسائل. لا إعادة تشغيل للسيرفر."
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
