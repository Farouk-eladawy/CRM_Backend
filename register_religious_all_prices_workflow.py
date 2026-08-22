# -*- coding: utf-8 -*-
"""
Register the 'Religious All Prices Auto-Reply - ديني (💰 عايز الأسعار كلها)'
workflow in automation_workflows (chat_history.db).

المطلوب (من المدير — 2026-08-22):
  اعمل workflow باسم: (💰 عايز الأسعار كلها)
  لما عميل يبقي الكلمة ديه مطابقة 100% (Exact Match بالظبط):
  الكلمة: 💰 عايز الأسعار كلها
  → رد عليه فوراً بـ 2 رسائل متقطعين ورا بعض (رسالة 1 ثم رسالة 2) بالنص
    الحرفي التالي كما ورد في الطلب (مع الحفاظ على النص والإيموجي والأرقام):
      📩 رسالة 1: دي الـ٦ برامج بأسعار الموسم الماضي ... (الـ٦ برامج كاملة)
      📩 رسالة 2: ⭐ والأهم: اللي بيسجل دلوقتي بنحافظله على الخصم ...
  فقط في قسم Religious (فلترة صارمة - لا يمس أي قسم آخر).

قرار هندسي حول الـ trigger:
  - الطلب "رد عليه" = رد لحظي على رسالة العميل الواردة ⇒
    trigger_type = "message_received" (نفس سلوك Workflows الردود اللحظية
    المعتمدة: Religious 6 Programs Prices، Religious Keyword Auto-Reply،
    15 Days Exact Keyword Auto-Reply، Religious Umrah Package Phrases
    Auto-Reply، Religious September Campaign Auto-Reply).
  - الخطوة steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "religious_all_prices_autoreply.py"}
    + تمرير حقول حدث الرسالة كاملة إلى السكربت.
  - Guard: event.payload.location يحتوي "Religious" (فلترة من الجذور).

قواعد النظام المطبقة:
  - الاسم يحتوي على "Religious" و "ديني" حتى يظهر في لوحة المدير الديني
    (الفلاتر في الواجهة تعتمد على هذه الكلمات في الاسم — قاعدة النظام D)،
    مع الحفاظ على العبارة التي طلبها المدير حرفياً (💰 عايز الأسعار كلها).
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
    f"automation_workflows.backup_before_all_prices_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
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
            "script_name": "religious_all_prices_autoreply.py",
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
    "id": "religious_all_prices_autoreply_v1",
    "name": "Religious All Prices Auto-Reply - ديني (💰 عايز الأسعار كلها - Exact Match لحظي)",
    "description": (
        "الرد التلقائي اللحظي (رد عليه فوراً) على رسائل عملاء القسم الديني "
        "(Religious فقط - فلترة صارمة لا تمس أي قسم آخر) عندما تكون رسالة "
        "العميل مطابقة للكلمة (💰 عايز الأسعار كلها) بالكامل 100% (Exact "
        "Match بعد التطبيع الذي يحذف الرموز غير الحرفية فقط — ممنوع "
        "Contains/StartsWith/EndsWith: أي كلمة إضافية قبل النص أو بعده تمنع "
        "الرد). الرد: رسالتان متتاليتان ورا بعض (رسالة 1 ثم رسالة 2): "
        "الرسالة الأولى بنص الـ٦ برامج بأسعار الموسم الماضي (الحج البري "
        "٢١٠,٠٠٠ بدل ٢٢٠,٠٠٠، طيران اقتصادي ٢٢٠,٠٠٠ بدل ٢٤٥,٠٠٠، طيران "
        "تحسين ٢٥٠,٠٠٠ بدل ٢٧٩,٠٠٠ + ٧ أيام على ساحة الحرم، مخيمات ٥ نجوم "
        "٤٩٠,٠٠٠، مخيمات ٥ نجوم صف أول ٥٥٠,٠٠٠، أبراج كدانة ٦٤٠,٠٠٠ + ملاحظة "
        "أن كل الأسعار محسوب فيها خصم الحجز المبكر) — والرسالة الثانية عن "
        "الحفاظ على الخصم من تاريخ التسجيل وطلب صورة البطاقة (وش وضهر) "
        "ورقم الموبايل لتثبيت الخصم والتأكيد المبدأي للحجز. يُرسل مرة واحدة "
        "فقط لكل رسالة (حجز ذري Atomic Claim واحد يغطي الرسالتين معاً ويمنع "
        "التكرار من Webhook duplicate deliveries). احترام "
        "auto_reply_hold_until و needs_help (لا نتداخل مع موظف بشري). تخطي "
        "نافذة Meta الـ 24 ساعة تلقائياً لأن هذا رد مباشر على رسالة العميل "
        "وليس برومو مستقل. لا يلمس أي Workflow آخر ولا أي قسم آخر."
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
