# -*- coding: utf-8 -*-
"""
Register the 'Religious Parent Hajj Booking Auto-Reply - ديني
(بحجز لوالدي/والدتي — إيه المطلوب؟)' workflow in automation_workflows
(chat_history.db).

المطلوب (من المدير الديني - 2026-08-20):
  اعمل workflow باسم: (بحجز لوالدي/والدتي — إيه المطلوب؟)
  لما عميل يبقي الكلمة ديه مطابقة 100% (Exact Match بالظبط)
  الكلمة: بحجز لوالدي/والدتي — إيه المطلوب؟
  → رد عليه فوراً بثلاث رسائل متقطعين ورا بعض بالنص الثابت
    (كما ورد حرفياً في الطلب — مع الحفاظ على النص والإيموجي والأرقام).
  فقط في قسم Religious (فلترة صارمة من الجذور - لا يمس أي قسم آخر).

قرار هندسي حول الـ trigger:
  - الطلب "رد عليه" = رد لحظي على رسالة العميل الواردة ⇒
    trigger_type = "message_received" (نفس سلوك Workflows الردود اللحظية
    المعتمدة: Save 29,000 Discount، Register With Discount، Tahseen
    Discount، Hotel Photos Trip Program...).
  - الخطوة steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "religious_parent_hajj_booking_autoreply.py"}
    + تمرير حقول حدث الرسالة كاملة إلى السكربت.
  - Guard: event.payload.location يحتوي "Religious" (فلترة من الجذور).

قواعد النظام المطبقة:
  - الاسم يحتوي على "Religious" و "ديني" حتى يظهر في لوحة المدير الديني
    (الفلاتر في الواجهة تعتمد على هذه الكلمات في الاسم — قاعدة النظام D).
  - لا حاجة لإعادة تشغيل السيرفر: محرك الأتمتة يقرأ قاعدة البيانات
    automation_workflows في كل حدث (hot-load) — لا نلمس ai_agent.py.
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
    f"automation_workflows.backup_before_parent_hajj_booking_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
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
            "script_name": "religious_parent_hajj_booking_autoreply.py",
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
    "id": "religious_parent_hajj_booking_autoreply_v1",
    "name": "Religious Parent Hajj Booking Auto-Reply - ديني (بحجز لوالدي/والدتي — إيه المطلوب؟ - Exact Match لحظي)",
    "description": (
        "الرد التلقائي اللحظي (رد عليه فوراً) على رسائل عملاء القسم الديني "
        "(Religious فقط - فلترة صارمة لا تمس أي قسم آخر) عندما تكون رسالة "
        "العميل مطابقة للكلمة (بحجز لوالدي/والدتي — إيه المطلوب؟) بالكامل 100% "
        "(Exact Match بعد التطبيع الذي يحذف الرموز غير الحرفية فقط — ممنوع "
        "Contains/StartsWith/EndsWith: أي كلمة إضافية قبل النص أو بعده تمنع "
        "الرد). الرد: ثلاث رسائل متقطعات ورا بعض (ثلاث رسائل منفصلة متتالية "
        "بفاصل زمني قصير) بالنص الثابت: (1) طمأنة العميل: ربنا يتقبل منك 🌹 "
        "دي أجمل هدية ممكن تقدمها لحد في الدنيا + والدك/والدتك مش هيتسابوا "
        "لوحدهم ولا لحظة — مشرفنا الميداني معاهم بالاسم من المطار للمطار "
        "👥📞؛ (2) أنسب برامجنا لكبار السن هو حج الطيران تحسين: ⭐ ٧ أيام "
        "إقامة ٥ نجوم على ساحة الحرم مباشرة بعد المناسك، 🚆 قطار الحرمين "
        "السريع، ⛺ مخيمات ألماني مكيفة، 🍽 وجبات طوال الرحلة، 📅 ١٩ يوم + "
        "💰 السعر للفرد: ٢٥٠ ألف بدلًا من ٢٧٩ — ميزة الـ٢٩,٠٠٠ بتتحفظ باسمهم "
        "كتابيًا وبتتخصم من السعر الرسمي أيًا كان بعد الضوابط + ✈️ تذكرة "
        "الطيران بسعرها المعلن وقت الحجز + 📌 السعر على أساس الموسم السابق "
        "لحين ضوابط ١٤٤٨؛ (3) المطلوب عشان نحجزلهم: 1️⃣ صورة بطاقة "
        "والدك/والدتك (سارية ٦ شهور على الأقل)، 2️⃣ رقم موبايلك + ⚠️ ومهم "
        "نعرف منك حاجتين: سنهم كام؟ وهل سبق لهم الحج قبل كده؟ (شرط التقديم "
        "إنها تكون أول مرة) + ولو حابب الاتنين يسافروا مع بعض في نفس "
        "المجموعة — بنعمل ربط عائلي 😊. يُرسل مرة واحدة فقط لكل رسالة (حجز "
        "ذري Atomic Claim يمنع التكرار من Webhook duplicate deliveries). "
        "احترام auto_reply_hold_until و needs_help (لا نتداخل مع موظف بشري). "
        "تخطي نافذة Meta الـ 24 ساعة تلقائياً لأن هذا رد مباشر على رسالة "
        "العميل وليس برومو مستقل (لتجنب خطأ 10 من Meta). لا يلمس أي Workflow "
        "آخر ولا أي قسم آخر."
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
