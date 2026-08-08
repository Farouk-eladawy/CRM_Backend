# -*- coding: utf-8 -*-
"""
Register the 'Religious Hajj Early-Booking Follow-Up - ديني' workflow
in automation_workflows (chat_history.db).

المطلوب (من المدير — برومبت نظام الفولو اب لخصم الحجز المبكر لحج ١٤٤٨):
  - Workflow بنوع trigger_type = "schedule" يشتغل كل 60 دقيقة.
  - الخطوة steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "religious_hajj_earlybooking_followup.py"}.
  - الاسم يحتوي على "Religious" و "ديني" حتى يظهر في لوحة المدير الديني
    (الفلاتر في الواجهة تعتمد على هذه الكلمات في الاسم — قاعدة النظام D).
  - شرط التفعيل الحصري داخل السكربت: facebook_ad_id = 120247344380410757 فقط
    (فلترة صارمة في SQL من الجذور — لا يلمس أي إعلان أو قسم آخر).
  - لا حاجة لإعادة تشغيل السيرفر: محرك الأتمتة يقرأ قاعدة البيانات
    automation_workflows في كل tick (hot-load) — لا نلمس ai_agent.py.

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
    f"automation_workflows.backup_before_hajj_earlybooking_followup_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
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
        "body": {"script_name": "religious_hajj_earlybooking_followup.py"},
    }
]

payload = {
    "id": "religious_hajj_earlybooking_followup_v1",
    "name": "Religious Hajj Early-Booking Follow-Up - ديني (خصم الحجز المبكر حج ١٤٤٨ - إعلان 120247344380410757)",
    "description": (
        "نظام الفولو اب التلقائي لخصم الحجز المبكر لحج ١٤٤٨ — يُطبَّق حصرياً "
        "على المحادثات الواردة من الإعلان Ad ID: 120247344380410757 فقط "
        "(فلترة صارمة في SQL من الجذور). دورة فحص كل 60 دقيقة حسب جدول "
        "القرارات: أقل من ساعة من آخر رسالة عميل → انتظر؛ من 1 إلى أقل من 6 "
        "ساعات + 0 متابعات → المتابعة 1؛ من 6 إلى أقل من 21 ساعة + 0 أو 1 "
        "متابعات → المتابعة 2 (إن لم تُرسل 1 تُرسل 2 مباشرة ولا تُعوَّض 1)؛ "
        "من 21 إلى أقل من 24 ساعة + 0/1/2 متابعات → المتابعة 3 (الإغلاق)؛ "
        "24 ساعة أو أكثر → توقف نهائي (نافذة ميتا). قاعدة صارمة: رسالة "
        "متابعة واحدة كحد أقصى في الدورة، لا تكرار أبداً، والحد الأقصى 3 "
        "رسائل متابعة لكل محادثة (العدّاد الكلي محفوظ حتى بعد رد العميل). "
        "شروط الإيقاف: أي رد عميل (إعادة ضبط الساعات من آخر رسالة له مع "
        "احتساب المتابعات السابقة ضمن الحد الأقصى)، أو رقم واتساب (رسالة "
        "تأكيد + وسم Lead جاهز للاتصال + needs_help=1 + إيقاف نهائي)، أو "
        "إتمام الحجز/دفع جدية الحجز (تحويل لمسار الحجز + إيقاف نهائي)، أو "
        "عدم الاهتمام الواضح (رسالة ختام مهذبة + إيقاف نهائي)، أو تدخل "
        "موظف بشري. التوقيت بتوقيت القاهرة (chat_db.get_cairo_time) والحالة "
        "في ملف JSON محلي. لا يلمس أي Workflow آخر ولا أي إعلان أو قسم آخر."
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
