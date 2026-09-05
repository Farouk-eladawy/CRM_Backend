# -*- coding: utf-8 -*-
"""
Register the 'Religious - متابعة العملاء برسالة فولو اب (ديني) - إعلانان'
workflow in automation_workflows (chat_history.db).

المطلوب (من المدير - 2026-09-05):
  - اسم workflow: "متابعة العملاء برسالة فولو اب" (مع إلزام كلمة Religious لأن
    القسم ديني — قاعدة النظام D: لوحة المدير الديني تفلتر بالاسم).
  - على أي رسالة واردة من الإعلانين التاليين فقط:
      120248731132960757
      120248766705610757
  - نرسل رسالتي متابعة:
      Follow-up 1: بعد 4 ساعات  (رسالة الفرق بين البرامج — بري/طيران/تحسين)
      Follow-up 2: بعد 22 ساعة  (رسالة خصم الحجز المبكر + هدايا FTS)
  - لو العميل رد في أي وقت → السلسلة بتقف فوراً (المساعد الأساسي بيرد عليه)
    ولا نرسل أي متابعة تانية (منع السبام وعدم التداخل مع الرد البشري).

قرار هندسي:
  - trigger_type = "schedule" مع every_minutes=30 (فحص دوري كل 30 دقيقة) —
    نفس نمط religious_hajj_3msg_followup / hajj_5ads_followup.
  - steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "religious_2ads_followup.py"}
  - السكربت نفسه يفلتر من الجذور (facebook_ad_id IN 2 + location='Religious').
  - لا تعديل على ai_agent.py ولا إعادة تشغيل للسيرفر: محرك الأتمتة hot-load
    من قاعدة البيانات في كل tick (آلية _run_schedules).
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
    f"automation_workflows.backup_before_2ad_followup_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
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
            "script_name": "religious_2ads_followup.py",
        },
    },
]

payload = {
    "id": "religious_2ads_followup_v1",
    # القاعدة D: الاسم يحتوي "Religious" و"ديني" حتى يظهر في لوحة المدير الديني
    "name": "Religious - متابعة العملاء برسالة فولو اب (ديني) - إعلانان 120248731132960757/120248766705610757",
    "description": (
        "متابعة تلقائية (رسالتا فولو اب) لعملاء القسم الديني Religious ONLY "
        "القادمين من الإعلانين (120248731132960757 / 120248766705610757) — "
        "فلترة صارمة من الجذور في SQL (facebook_ad_id IN 2 AND location='Religious') "
        "لا تمس أي إعلان أو قسم آخر. الجدول الزمني (مقاسة من آخر رسالة حقيقية "
        "للعميل): Follow-up 1 بعد 4 ساعات (الفرق بين البرامج بري/طيران/تحسين)، "
        "Follow-up 2 بعد 22 ساعة (خصم الحجز المبكر + هدايا FTS) — قبل قفل نافذة "
        "Meta الـ 24 ساعة بساعتين (أمان من خطأ #10). لو العميل رد في أي وقت → "
        "السلسلة بتقف فوراً (لا سبام ولا تداخل مع الرد البشري). التوقيت بتوقيت "
        "القاهرة (get_cairo_time) والحالة في ملف JSON محلي (لا load_state). يحترم "
        "needs_help / is_closed / auto_reply_hold_until. لا إعادة تشغيل للسيرفر."
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
