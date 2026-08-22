# -*- coding: utf-8 -*-
"""
Register the 'Religious Early Booking Benefit Auto-Reply - ديني (🎁 إيه ميزة الحجز المبكر؟)'
workflow in automation_workflows (chat_history.db).

المطلوب (من المدير - 2026-08-22):
  اعمل workflow باسم: (🎁 إيه ميزة الحجز المبكر؟)
  لما عميل يبقي الكلمة ديه مطابقة 100% (Exact Match بالظبط)
  الكلمة: 🎁 إيه ميزة الحجز المبكر؟
  → رد عليه فوراً برسالتين متقطعتين وراء بعض بالنص الثابت
    (كما ورد حرفياً في الطلب — مع الحفاظ على النص والإيموجي والأرقام).
  فقط في قسم Religious (فلترة صارمة من الجذور - لا يمس أي قسم آخر).

قرار هندسي حول الـ trigger:
  - الطلب "رد عليه" = رد لحظي على رسالة العميل الواردة ⇒
    trigger_type = "message_received" (نفس سلوك Workflows الردود اللحظية
    المعتمدة: Save 29,000 Discount، Price Changes، 6 Programs Prices...).
  - الخطوة steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "religious_early_booking_benefit_autoreply.py"}
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
    f"automation_workflows.backup_before_early_booking_benefit_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
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
            "script_name": "religious_early_booking_benefit_autoreply.py",
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
    "id": "religious_early_booking_benefit_autoreply_v1",
    "name": "Religious Early Booking Benefit Auto-Reply - ديني (🎁 إيه ميزة الحجز المبكر؟ - Exact Match لحظي)",
    "description": (
        "الرد التلقائي اللحظي (رد عليه فوراً) على رسائل عملاء القسم الديني "
        "(Religious فقط - فلترة صارمة لا تمس أي قسم آخر) عندما تكون رسالة "
        "العميل مطابقة للكلمة (🎁 إيه ميزة الحجز المبكر؟) بالكامل 100% "
        "(Exact Match بعد التطبيع الذي يحذف الرموز غير الحرفية فقط — ممنوع "
        "Contains/StartsWith/EndsWith: أي كلمة إضافية قبل النص أو بعده تمنع "
        "الرد). الرد: رسالتان متقطعتان وراء بعض (رسالتان منفصلتان متتاليتان "
        "بفاصل زمني قصير) بالنص الثابت: (1) سؤال ممتاز — ودي أهم معلومة قبل "
        "نزول الضوابط 👌 (شرح معنى خصم الحجز المبكر: اللي بيسجل اهتمامه قبل "
        "صدور ضوابط وزارة السياحة بياخد سعر أقل + قيمة الخصم توصل لحد "
        "٢٩,٠٠٠ ج حسب البرنامج + ⭐ والأهم الخصم محفوظ حتى لو الأسعار "
        "اتغيرت بعد نزول الضوابط — خصمك محسوبلك من تاريخ تسجيلك)؛ "
        "(2) وفيه سبب تاني أهم من الخصم نفسه (الموسم اللي فات برنامج الحج "
        "البري اكتمل قبل نزول الضوابط واللي استنوا ملقوش مكان + التسجيل مش "
        "بيكلف حاجة: 📸 صورة البطاقة و 📱 رقم الموبايل + وبكده مكانك محجوز "
        "والخصم مثبتلك وهتعرف التفاصيل قبل أي حد ✅ + CTA: تحب أبعتلك الـ٦ "
        "برامج بأسعارها وخصوماتها دلوقتي؟). يُرسل مرة واحدة فقط لكل رسالة "
        "(حجز ذري Atomic Claim يمنع التكرار من Webhook duplicate deliveries). "
        "احترام auto_reply_hold_until و needs_help (لا نتداخل مع موظف بشري). "
        "تخطي نافذة Meta الـ 24 ساعة تلقائياً لأن هذا رد مباشر على رسالة "
        "العميل وليس برومو مستقل. لا يلمس أي Workflow آخر ولا أي قسم آخر."
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
