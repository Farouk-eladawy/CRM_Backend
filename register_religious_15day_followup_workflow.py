# -*- coding: utf-8 -*-
"""
Register the 'Religious 15-Day Follow-Up - ديني' workflow
in automation_workflows (chat_history.db).

المطلوب (من المدير — برومبت نظام الفولو اب لبرنامج عمرة الـ١٥ يوم):
  - Workflow بنوع trigger_type = "schedule" يشتغل كل 60 دقيقة.
  - الخطوة steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "religious_15day_followup.py"}.
  - الاسم يحتوي على "Religious" و "ديني" حتى يظهر في لوحة المدير الديني
    (الفلاتر في الواجهة تعتمد على هذه الكلمات في الاسم — قاعدة النظام D).
  - لا حاجة لإعادة تشغيل السيرفر: محرك الأتمتة يقرأ قاعدة البيانات
    automation_workflows في كل tick (hot-load) — لا نلمس ai_agent.py.
  - شرط التفعيل الحصري داخل السكربت: facebook_ad_id = 120248067701970757 فقط.

خطوات التنفيذ:
  1) نسخة احتياطية كاملة من جدول automation_workflows إلى ملف JSON
     (قاعدة النظام 3: نسخ قبل أي تعديل).
  2) upsert_workflow للـ workflow الجديد (إضافة فقط — لا حذف لأي سجل).
"""
import sys
import io
import json
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import automation_db
from fts_paths import get_data_path

# =============================================================================
# 1) نسخة احتياطية من automation_workflows قبل الإضافة
# =============================================================================
BACKUP_FILE = get_data_path(
    f"automation_workflows.backup_before_15day_followup_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
)
try:
    existing = automation_db.list_workflows()
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"[Backup] Saved {len(existing)} existing workflows -> {BACKUP_FILE}")
except Exception as e:
    print(f"[Backup] WARNING: could not backup automation_workflows: {e}")

# =============================================================================
# 2) تسجيل الـ workflow الجديد (إضافة فقط — upsert بنفس الـ id يعمل كتحديث)
# =============================================================================
steps = [
    {
        "type": "http_request",
        "method": "POST",
        "url": "http://127.0.0.1:5001/api/automation/run_script",
        "headers": {"content-type": "application/json"},
        "timeout_seconds": 60,
        "body": {"script_name": "religious_15day_followup.py"},
    }
]

payload = {
    "id": "religious_15day_followup_v1",
    "name": "Religious 15-Day Follow-Up - ديني (عمرة ال١٥ يوم - إعلان 120248067701970757)",
    "description": (
        "نظام الفولو اب التلقائي لبرنامج عمرة ال١٥ يوم — يُطبَّق حصرياً على "
        "المحادثات الواردة من الإعلان Ad ID: 120248067701970757 فقط (فلترة "
        "صارمة في SQL من الجذور). دورة فحص كل 60 دقيقة: الفولو اب الأول بعد 3 "
        "ساعات من آخر رسالة (بشرط ألا يرد العميل على آخر رسالة منّنا)، والفولو "
        "اب الثاني بعد 20 ساعة من آخر تفاعل عميل وقبل مرور 23 ساعة (قبل قفل "
        "نافذة Meta الـ 24 ساعة). الحد الأقصى: رسالتا فولو اب فقط لكل محادثة. "
        "اختيار النص حسب آخر زرار ضغطه العميل (برنامج بالتفصيل / أقرب مواعيد / "
        "السعر شامل إيه) أو النسخة العامة. ساعات الصمت [11م-9ص بتوقيت القاهرة]: "
        "تأجيل الإرسال لأول دورة بعد 9 صباحاً مع الالتزام بحد الـ 23 ساعة. "
        "شروط الإيقاف: أي رد من العميل (إعادة العدّاد بعد آخر رد منّنا)، أو "
        "استلام رقم تليفون (تحويل فوري لخدمة العملاء مع وسم عميل جاهز للاتصال)، "
        "أو تأكيد الحجز/تحويل العربون (تحويل لفريق الحجز)، أو طلب عدم التواصل "
        "(إيقاف دائم بالـ sender)، أو مرور 24 ساعة (إيقاف الإرسال). الرد "
        "بلايك/إيموجي فقط يفتح نافذة جديدة ويرد عليه رداً طبيعياً. لا يلمس أي "
        "Workflow آخر ولا أي إعلان أو قسم آخر."
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
