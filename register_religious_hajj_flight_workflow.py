# -*- coding: utf-8 -*-
"""
Register the 'Religious "برنامج حج طيران" Auto-Reply - ديني (Exact Match لحظي)'
workflow in automation_workflows (chat_history.db).

المطلوب (من المدير — 2026-08-27):
  اعمل workflow باسم "برنامج حج طيران":
    - أول ما يبقى في رسالة بكلمة "برنامج حج طيران 👍" بنسبة تطابق 100% (Exact Match)
    - رد عليها بـ 2 رسائل:
        رسالة ١: خط سير برنامج حج الطيران الاقتصادي كاملاً (المدينة المنورة ٢-٥ ذو الحجة،
                  قطار الحرمين هدية، مكة قبل المناسك ٦-٨، المناسك ٩-١٣، العزيزية ١٤-١٧)
        رسالة ٢: السعر ٢٢٠ ألف بدل ٢٤٥ + أولوية الخصم + سؤال الإغلاق
      (النص الكامل في workflows/religious_hajj_flight_autoreply.py)

قرار هندسي حول الـ trigger:
  - الطلب "رد عليها" = رد لحظي على رسالة العميل الواردة ⇒
    trigger_type = "message_received" (نفس سلوك Workflows الردود اللحظية
    المعتمدة: Religious Hajj Bari / Tahseen Flight Program / Li Ana / With You).
  - الخطوة steps_json: http_request يستدعي المسار الثابت
    http://127.0.0.1:5001/api/automation/run_script
    مع body = {"script_name": "religious_hajj_flight_autoreply.py"} + تمرير
    حقول حدث الرسالة كاملة إلى السكربت.
  - Guard: event.payload.location يحتوي "Religious" (فلترة من الجذور).

قواعد النظام المطبقة:
  - الاسم يحتوي على "Religious" و "ديني" حتى يظهر في لوحة المدير الديني
    (الفلاتر في الواجهة تعتمد على هذه الكلمات في الاسم — قاعدة النظام D).
  - الاسم يبدأ أيضاً بالاسم الذي طلبه المدير حرفياً: "برنامج حج طيران".
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
    f"automation_workflows.backup_before_hajj_flight_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
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
            "script_name": "religious_hajj_flight_autoreply.py",
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
    "id": "religious_hajj_flight_autoreply_v1",
    "name": "برنامج حج طيران - Religious Auto-Reply - ديني (Exact Match لحظي)",
    "description": (
        "الرد التلقائي اللحظي (رد مباشرة) على رسائل عملاء القسم الديني "
        "(Religious فقط - فلترة صارمة لا تمس أي قسم آخر) عندما يرسل العميل "
        "عبارة 'برنامج حج طيران 👍' بنسبة تطابق 100% (Exact Match كامل - "
        "ممنوع Contains/StartsWith/EndsWith، مع ملاحظة أن الإيموجي 👍 رمز غير "
        "حرفي يُحذف في التطبيع فتطابق بدون الإيموجي أيضاً). الرد برسالتين "
        "متتاليتين: الرسالة ١: خط سير برنامج حج الطيران الاقتصادي مع FTS "
        "(المدينة المنورة ٢-٥ ذو الحجة بفندق بالمركزية، قطار الحرمين السريع "
        "هدية من الشركة، مكة قبل المناسك ٦-٨، المناسك ٩-١٣ بمخيمات ألماني "
        "مكيفة، العزيزية ١٤-١٧ ذو الحجة، مشرف مرافق وحج على سنة النبي ﷺ). "
        "الرسالة ٢: السعر ٢٢٠ ألف بدل ٢٤٥ بخصم الحجز المبكر على أساس الموسم "
        "اللي فات، وأولوية الخصم لمن يسجل ملفه من دلوقتي، غير شامل تذكرة "
        "الطيران + سؤال إغلاق (رقمك عليه واتساب؟). يُرسل مرة واحدة فقط لكل "
        "رسالة (حجز ذري Atomic Claim يمنع التكرار من Webhook duplicate "
        "deliveries). احترام auto_reply_hold_until و needs_help (لا نتداخل مع "
        "موظف بشري). تخطي نافذة Meta الـ 24 ساعة تلقائياً لأن هذا رد مباشر "
        "على رسالة العميل وليس برومو مستقل. لا يلمس أي Workflow آخر ولا أي "
        "قسم آخر (كلمة 'برنامج حج طيران' لا تتعارض مع 'برنامج حج طيران "
        "تحسين' لأن المطابقة Exact بالمساواة الكاملة)."
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
