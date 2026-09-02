# -*- coding: utf-8 -*-
"""
Register the 'Religious "طيران تحسين — ٢٧٥ ألف" Auto-Reply - ديني
(Exact Match لحظي)' workflow in automation_workflows (chat_history.db).

المطلوب (من المدير — 2026-09-02):
  اعمل workflow باسم "طيران تحسين — ٢٧٥ ألف":
    - أول ما يبقى في رسالة بكلمة "طيران تحسين — ٢٧٥ ألف" بنسبة تطابق 100%
      (Exact Match كامل)
    - رد عليها بـ 2 رسائل:
        رسالة ١: عرض حج طيران تحسين مع FTS 🕋 — ٢٧٥ ألف بدل ٣٠٤ ألف،
                  الخصم لحد الخميس ١٧ سبتمبر ✅، (تذكرة الطيران بتتضاف
                  بسعرها وقت الحجز)، ليه التحسين؟ (ساحة الحرم مباشرة بعد
                  تعب المناسك)، خط السير (المدينة ٢–٥ / قطار الحرمين /
                  مكة ٦–٨ / المناسك ٩–١٣ / ⭐ التحسين على ساحة الحرم ١٤–٢٠
                  لمدة 7 أيام كاملين) + جدية الحجز ٨٠٬١٥٠ جنيه بتتخصم من
                  الإجمالي وتُسترد في حاله عدم الفوز على بنك مصر.
        رسالة ٢: النتيجة يوم ٣٠ سبتمبر + شرح الدفع والتقسيط وتثبيت المكان
                  بسعر الخصم في مكالمة دقيقتين (سؤال إغلاق: أكلم حضرتك على
                  أي رقم؟ 📞)
      (النص الكامل في workflows/religious_airline_tahseen_275k_autoreply.py)

قرار هندسي حول الـ trigger:
  - الطلب "رد عليها" = رد لحظي على رسالة العميل الواردة ⇒
    trigger_type = "message_received" (نفس سلوك Workflows الردود اللحظية
    المعتمدة — آخرها Religious "حج بري — ٢٢٠ ألف" بتاريخ 2026-09-02 بنفس
    القالب الحرفي).
  - الخطوة steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "religious_airline_tahseen_275k_autoreply.py"} +
    تمرير حقول حدث الرسالة كاملة إلى السكربت.
  - Guard: event.payload.location يحتوي "Religious" (فلترة من الجذور —
    قاعدة النظام 15: لا نلمس أي قسم آخر).
  - المطابقة 100% = مساواة كاملة == بعد إزالة الرموز غير الحرفية فقط (نفس
    المعنى المعتمد في workflow "حج بري — ٢٢٠ ألف" الموافق عليه من المدير).

قواعد النظام المطبقة:
  - الاسم يحتوي على "Religious" و "ديني" حتى يظهر في لوحة المدير الديني
    (الفلاتر في الواجهة تعتمد على هذه الكلمات في الاسم — قاعدة النظام D).
  - الاسم يبدأ أيضاً بالاسم الذي طلبه المدير حرفياً: "طيران تحسين — ٢٧٥ ألف".
  - لا حاجة لإعادة تشغيل السيرفر: محرك الأتمتة يقرأ قاعدة البيانات
    automation_workflows في كل tick (hot-load) — لا نلمس ai_agent.py.
  - نسخة احتياطية كاملة من جدول automation_workflows إلى ملف JSON قبل
    أي تعديل (قاعدة النظام 3: نسخ قبل أي تعديل).
  - upsert_workflow (إضافة فقط — لا حذف لأي سجل — قاعدة النظام 8).
  - لا نعدّل أو نلغي أي Workflow قديم لحملات طيران تحسين السابقة (بأسعار
    أخرى) — حملة جديدة مستقلة بكلمة مفتاحية مختلفة (٢٧٥ بدل ٣٠٤).
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
    f"automation_workflows.backup_before_airline_tahseen_275k_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
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
            "script_name": "religious_airline_tahseen_275k_autoreply.py",
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
    "id": "religious_airline_tahseen_275k_autoreply_v1",
    "name": "طيران تحسين — ٢٧٥ ألف - Religious Auto-Reply - ديني (Exact Match 100% لحظي)",
    "description": (
        "الرد التلقائي اللحظي (رد مباشرة) على رسائل عملاء القسم الديني "
        "(Religious فقط - فلترة صارمة لا تمس أي قسم آخر) عندما يرسل العميل "
        "عبارة 'طيران تحسين — ٢٧٥ ألف' بنسبة تطابق 100% (Exact Match كامل - "
        "ممنوع Contains/StartsWith/EndsWith). الرد برسالتين متتاليتين: "
        "الرسالة ١: عرض حج طيران تحسين مع FTS 🕋 — ٢٧٥ ألف بدل ٣٠٤ ألف "
        "(الخصم لحد الخميس ١٧ سبتمبر ✅ — تذكرة الطيران بتتضاف بسعرها وقت "
        "الحجز)، ليه التحسين؟ (بعد تعب المناسك بتكون على ساحة الحرم مباشرة — "
        "صلاة أسهل ومشاوير أقل وراحة أكتر لراحة كبار السن)، مع خط السير "
        "كاملاً (🕌 المدينة ٢–٥ ذو الحجة إقامة قريبة من الحرم، 🚄 قطار "
        "الحرمين من المدينة لمكة، 🕋 مكة ٦–٨ إقامة فندقية، ⛺ المناسك ٩–١٣ "
        "عرفات ومزدلفة ومنى مخيمات مكيّفة، ⭐ التحسين على ساحة الحرم ١٤–٢٠ "
        "إقامة على الحرم مباشرة لمدة 7 أيام كاملين) + مشرف الشركة معاك + "
        "جدية الحجز ٨٠٬١٥٠ جنيه بتتخصم من الإجمالي وتُسترد في حاله عدم "
        "الفوز على بنك مصر. الرسالة ٢: النتيجة يوم ٣٠ سبتمبر + شرح تفاصيل "
        "الدفع والتقسيط وتثبيت المكان بسعر الخصم في مكالمة دقيقتين (سؤال "
        "إغلاق: أكلم حضرتك على أي رقم؟ 📞). يُرسل مرة واحدة فقط لكل رسالة "
        "(حجز ذري Atomic Claim يمنع التكرار من Webhook duplicate "
        "deliveries). احترام auto_reply_hold_until و needs_help (لا نتداخل "
        "مع موظف بشري). تخطي نافذة Meta الـ 24 ساعة تلقائياً لأن هذا رد "
        "مباشر على رسالة العميل وليس برومو مستقل. لا يلمس أي Workflow آخر "
        "(بما في ذلك حملات طيران تحسين السابقة بأسعار أخرى) ولا أي قسم آخر."
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
