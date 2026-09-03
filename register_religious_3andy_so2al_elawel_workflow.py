# -*- coding: utf-8 -*-
"""
Register the 'عندي سؤال الأول - Religious Auto-Reply - ديني (Exact Match 100% لحظي)'
workflow in automation_workflows (chat_history.db).

المطلوب (من المدير — 2026-09-03):
  - اسم الـ Workflow: "عندي سؤال الأول"
  - أول ما يبقى في رسالة بكلمة "عندي سؤال الأول" بنسبة تطابق 100%
    (تطابق حرفي بالظبط — Exact Match كامل) → رد مباشر (لحظي) بالرد المحدد
    حرفياً: "اتفضل يا فندم ، اسأل براحتك على أي حاجة تحب تعرفها، وأنا هجاوب
    حضرتك خطوة بخطوة 🙏"
  - فقط في قسم Religious (فلترة صارمة - لا يمس أي قسم آخر — قاعدة النظام 15)
    وعبر فيسبوك/واتساب فقط.

سياق حقيقي مهم:
  - "عندي سؤال الأول" خيار قائمة (Menu Option) يكتبه العملاء حرفياً في حملات
    القسم الديني الحالية (شوهد عميل فعلي أرسلها 2026-09-04 00:43 بتوقيت
    القاهرة). كانت ترد عليها سابقاً حملة سبتمبر برد قديم → هذا الـ Workflow
    المخصص يتولاها الآن بالرد الجديد، وتم تعطيل الكلمة القديمة في ملف حملة
    سبتمبر (وليس حذفها) لمنع الرد المزدوج — نسخة .bak كاملة محفوظة.

قرار هندسي حول الـ trigger:
  - الطلب "رد عليها بالرد ده" = رد لحظي على رسالة العميل الواردة ⇒
    trigger_type = "message_received" (نفس سلوك Workflows الردود اللحظية
    المعتمدة: عندي سؤال الأول / مش عارف / سؤال تاني ...).
  - الخطوة steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "religious_3andy_so2al_elawel_autoreply.py"}
    + تمرير حقول حدث الرسالة كاملة إلى السكربت.
  - Guard: event.payload.location يحتوي "Religious" (فلترة من الجذور).
  - Guard إضافي: event.payload.source فيسبوك/واتساب فقط (لا Email).
  - لا تداخل مع Workflows أخرى: عبارة "عندي سؤال" بدون "الأول" ليست كلمة هذا
    الـ Workflow (تترك للنظام الأساسي)، وعبارة "❓ سؤال تاني" تخص Workflow آخر.

قواعد النظام المطبقة:
  - الاسم يبدأ بالاسم الذي طلبه المدير حرفياً: "عندي سؤال الأول" ويحتوي على
    "Religious" و "ديني" حتى يظهر في لوحة المدير الديني (قاعدة النظام D).
  - لا حاجة لإعادة تشغيل السيرفر: run_automation_script يعيد تحميل ملفات
    workflows/ من القرص في كل حدث (hot-load) — لا نلمس ai_agent.py
    (قاعدة النظام 11 — منع إعادة تشغيل السيرفر).
  - نسخة احتياطية كاملة من جدول automation_workflows إلى ملف JSON قبل
    أي تعديل (قاعدة النظام 3).
  - upsert_workflow (إضافة فقط — لا حذف لأي سجل — قاعدة النظام 8).
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
    f"automation_workflows.backup_before_3andy_so2al_elawel_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
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
        "type": "guard",
        "path": "event.payload.source",
        "contains_any": ["facebook", "whatsapp"],
        "case_insensitive": True,
    },
    {
        "type": "http_request",
        "method": "POST",
        "url": "http://127.0.0.1:5001/api/automation/run_script",
        "headers": {"content-type": "application/json"},
        "timeout_seconds": 30,
        "body": {
            "script_name": "religious_3andy_so2al_elawel_autoreply.py",
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
    "id": "religious_3andy_so2al_elawel_autoreply_v1",
    "name": "عندي سؤال الأول - Religious Auto-Reply - ديني (Exact Match 100% لحظي)",
    "description": (
        "الرد التلقائي اللحظي (رد مباشرة) على رسائل عملاء القسم الديني "
        "(Religious فقط - فلترة صارمة لا تمس أي قسم آخر — قاعدة النظام 15) "
        "عبر قنوات فيسبوك/واتساب فقط عندما يرسل العميل عبارة "
        "'عندي سؤال الأول' بنسبة تطابق 100% (Exact Match كامل - ممنوع "
        "Contains/StartsWith/EndsWith: أي كلمة إضافية قبل النص أو بعده "
        "تكسر المساواة → لا رد — أي أن عبارة 'عندي سؤال' بدون 'الأول' أو "
        "'عندي سؤال عن الأسعار' لا تطابق هذا الـ Workflow وتترك للنظام "
        "الأساسي/AI). الرد الثابت حرفياً كما كتبه المدير (2026-09-03): "
        "'اتفضل يا فندم ، اسأل براحتك على أي حاجة تحب تعرفها، وأنا هجاوب "
        "حضرتك خطوة بخطوة 🙏' يُرسل مرة واحدة فقط لكل رسالة (حجز ذري "
        "Atomic Claim يمنع التكرار من Webhook duplicate deliveries). "
        "ملاحظة توثيقية: كانت عبارة 'عندي سؤال الأول' ترد عليها سابقاً حملة "
        "'Religious September Campaign Auto-Reply' برد قديم، وتم تعطيل "
        "(وليس حذف) تلك الكلمة في ملف الحملة مع هذا الـ Workflow الجديد "
        "لمنع الرد المزدوج (Double Reply) على نفس رسالة العميل — النسخة "
        "الأصلية محفوظة بملف .bak وقابلة للتراجع. احترام "
        "auto_reply_hold_until و needs_help (لا نتداخل مع موظف بشري). "
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
