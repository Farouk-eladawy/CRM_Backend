# -*- coding: utf-8 -*-
"""
Register the 'Religious "راحة بسعر متوسط" Auto-Reply - ديني (Exact Match لحظي)'
workflow in automation_workflows (chat_history.db).

المطلوب (من المدير — 2026-08-30):
  اعمل workflow باسم "راحة بسعر متوسط":
    - أول ما يبقي في رسالة بكلمة "راحة بسعر متوسط" بنسبة تطابق 100% (Exact Match)
    - رد عليها بالرد الثابت التالي (حرفياً كما كتبها المدير):

        تمام 🌙 اللي يناسبك غالبًا هو برنامج التحسين ٥ نجوم (أسعار الموسم الماضي
        بدون الطيران، والرسمية لـ١٤٤٨ بتصدر خلال أيام):

        🏨 تحسين ٧ أيام — ٢٥٠ ألف بدلًا من ٢٧٩ ألف (خصم ٢٩ ألف)
        بتحج بمسار الاقتصادي طيران، وبعد المناسك بتقضي ٧ أيام في فندق ٥ نجوم
        قريب من الحرم. يعني راحة الـ٥ نجوم في الجزء اللي بتحتاجها فيه، من غير
        ما تدفع سعر برنامج ٥ نجوم كامل.

        💡 وهو أكبر برنامج من حيث أعداد التأشيرات المتوقعة السنة دي.

        يناسبك لو: عايز قرب من الحرم وراحة بعد التعب، أو بتحجز لوالدك أو والدتك،
        أو مش عايز تدفع ٤٠٠ ألف وأكتر.

        🎁 الخصم ده محفوظ ليك لو سجلت قبل صدور الضوابط، حتى لو السعر الرسمي زاد.

        نكلمك على الموبايل نشرحلك الفندق والمسافة والتفاصيل — إمتى مناسب؟ 👇

قرار هندسي حول الـ trigger:
  - الطلب "رد عليها" = رد لحظي على رسالة العميل الواردة ⇒
    trigger_type = "message_received" (نفس سلوك Workflows الردود اللحظية
    المعتمدة: Religious Reasonable Price Comfort / Haram Comfort / Less Cost ...).
  - الخطوة steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "religious_raha_medium_price_autoreply.py"} + تمرير
    حقول حدث الرسالة كاملة إلى السكربت.
  - Guard: event.payload.location يحتوي "Religious" (فلترة من الجذور) —
    المحتوى عن برنامج التحسين ٥ نجوم وأسعار الحج وهو تخصص القسم الديني.

قواعد النظام المطبقة:
  - الاسم يحتوي على "Religious" و "ديني" حتى يظهر في لوحة المدير الديني
    (الفلاتر في الواجهة تعتمد على هذه الكلمات في الاسم — قاعدة النظام D).
  - الاسم يبدأ أيضاً بالاسم الذي طلبه المدير حرفياً: "راحة بسعر متوسط".
  - لا حاجة لإعادة تشغيل السيرفر: محرك الأتمتة يقرأ قاعدة البيانات
    automation_workflows في كل tick (hot-load) — لا نلمس ai_agent.py.
  - نسخة احتياطية كاملة من جدول automation_workflows إلى ملف JSON قبل
    أي تعديل (قاعدة النظام 3: نسخ قبل أي تعديل).
  - upsert_workflow (إضافة فقط — لا حذف لأي سجل).
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
    f"automation_workflows.backup_before_raha_medium_price_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
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
        "type": "guard",
        "path": "event.payload.location",
        "contains_any": ["Religious"],
        "case_insensitive": True,
    },
    {
        "type": "http_request",
        "method": "POST",
        "url": "http://127.0.0.1:5001/api/automation/run_script",
        "headers": {"content-type": "application/json"},
        "timeout_seconds": 30,
        "body": {
            "script_name": "religious_raha_medium_price_autoreply.py",
            "chat_id": "{{event.payload.chat_id}}",
            "message_body": "{{event.payload.message_body}}",
            "source": "{{event.payload.source}}",
            "sender_identifier": "{{event.payload.sender_identifier}}",
            "location": "{{event.payload.location}}",
            "receiving_phone_id": "{{event.payload.receiving_phone_id}}",
            "incoming_external_message_id": "{{event.payload.incoming_external_message_id}}",
        },
    },
]

payload = {
    "id": "religious_raha_medium_price_autoreply_v1",
    "name": "راحة بسعر متوسط - Religious Auto-Reply - ديني (Exact Match لحظي)",
    "description": (
        "الرد التلقائي اللحظي (رد مباشرة) على رسائل عملاء القسم الديني "
        "(Religious فقط - فلترة صارمة لا تمس أي قسم آخر) عندما يرسل العميل "
        "عبارة 'راحة بسعر متوسط' بنسبة تطابق 100% (Exact Match كامل - "
        "ممنوع Contains/StartsWith/EndsWith). الرد الثابت: تمام 🌙 اللي يناسبك "
        "غالبًا هو برنامج التحسين ٥ نجوم (أسعار الموسم الماضي بدون الطيران "
        "والرسمية لـ١٤٤٨ بتصدر خلال أيام) + تحسين ٧ أيام — ٢٥٠ ألف بدلًا من "
        "٢٧٩ ألف (خصم ٢٩ ألف) مع مسار الاقتصادي طيران وفندق ٥ نجوم قريب من "
        "الحرم بعد المناسك + أكبر برنامج في أعداد التأشيرات المتوقعة + يناسب "
        "اللي عايز قرب من الحرم وراحة بعد التعب أو الحجز للوالدين أو اللي مش "
        "عايز يدفع ٤٠٠ ألف وأكتر + الخصم محفوظ لو سجل قبل صدور الضوابط + دعوة "
        "للاتصال على الموبايل لشرح الفندق والمسافة والتفاصيل. يُرسل مرة واحدة "
        "فقط لكل رسالة (حجز ذري Atomic Claim يمنع التكرار من Webhook duplicate "
        "deliveries). احترام auto_reply_hold_until و needs_help (لا نتداخل مع "
        "موظف بشري). تخطي نافذة Meta الـ 24 ساعة تلقائياً لأن هذا رد مباشر على "
        "رسالة العميل وليس برومو مستقل. لا يلمس أي Workflow آخر ولا أي قسم آخر."
    ),
    "enabled": True,
    "category": "customer",
    "trigger_type": "message_received",
    "trigger_config": {"source": "Any"},
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
