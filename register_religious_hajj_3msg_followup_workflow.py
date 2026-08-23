# -*- coding: utf-8 -*-
"""
Register the 'Religious Hajj 3-Message Follow-up — 3 رسائل حج متابعة (ديني)'
workflow in automation_workflows (chat_history.db).

المطلوب (من المدير - 2026-08-23):
  - اسم workflow: "3 رسائل حج متابعه" (مع إلزام كلمة Religious لأن القسم ديني —
    قاعدة النظام D: لوحة المدير الديني تفلتر بالاسم).
  - على أي رسالة تيجي من الإعلانات الأربعة:
      120248310136460757 / 120248557092680757 / 120248587975700757 / 120247657321100757
  - نرسل 3 رسائل متابعة:
      فولو أب ١: بعد ساعة من آخر رسالة للعميل بدون رد
      فولو أب ٢: بعد ٨ ساعات
      فولو أب ٣: بعد ٢٢ ساعة (قبل قفل النافذة بساعتين على الأقل — أمان)
  - لو العميل رد في أي وقت → السلسلة بتقف فوراً والنافذة بتتصفّر.

قرار هندسي:
  - trigger_type = "schedule" مع every_minutes=30 (فحص دوري كل 30 دقيقة) —
    نفس نمط pickup_reminder / hajj_tahseen_3stage_followup.
  - steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "religious_hajj_3msg_followup.py"}
  - السكربت نفسه يفلتر من الجذور (facebook_ad_id IN 4 + location='Religious').
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
    f"automation_workflows.backup_before_hajj3msg_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
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
            "script_name": "religious_hajj_3msg_followup.py",
        },
    },
]

payload = {
    "id": "religious_hajj_3msg_followup_v1",
    # القاعدة D: الاسم يحتوي "Religious" و "ديني" حتى يظهر في لوحة المدير الديني
    "name": "Religious - 3 رسائل حج متابعة (ديني) - Follow-up للإعلانات الأربعة",
    "description": (
        "متابعة تلقائية (3 رسائل) لعملاء القسم الديني Religious ONLY القادمين "
        "من الإعلانات الأربعة (120248310136460757 / 120248557092680757 / "
        "120248587975700757 / 120247657321100757) — فلترة صارمة من الجذور في "
        "SQL (facebook_ad_id IN 4 AND location='Religious') لا تمس أي قسم آخر. "
        "الجدول الزمني (مقاسة من آخر رسالة حقيقية للعميل): فولو أب ١ بعد ساعة، "
        "فولو أب ٢ بعد ٨ ساعات، فولو أب ٣ بعد ٢٢ ساعة (قبل قفل نافذة Meta الـ "
        "24 ساعة بساعتين — أمان من خطأ #10). لو العميل رد في أي وقت → السلسلة "
        "بتقف فوراً والنافذة بتتصفّر. التوقيت بتوقيت القاهرة (get_cairo_time) "
        "والحالة في ملف JSON محلي (لا load_state). يحترم needs_help / is_closed / "
        "auto_reply_hold_until (لا يتداخل مع موظف بشري). لا إعادة تشغيل للسيرفر."
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
