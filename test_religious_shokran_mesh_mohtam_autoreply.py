# -*- coding: utf-8 -*-
"""
اختبار شامل لـ workflows/religious_shokran_mesh_mohtam_autoreply.py
بعد تحديث رسالة الرد (2026-09-03).

يعمل هذا الاختبار في عزلة تامة:
  - chat_db مُستبدل بـ Stub (لا كتابة في chat_history.db الإنتاجية إطلاقاً).
  - DEDUP_DB و STATE_FILE محوّلان إلى ملفات مؤقتة (لا نلمس ملفات الإنتاج).
"""
import sys
import io
import os
import json
import types
import importlib.util
import tempfile
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# =============================================================================
# 1) Stub لـ chat_db لحماية قاعدة البيانات الإنتاجية أثناء الاختبار
# =============================================================================
_stub = types.ModuleType("chat_db")


def _get_conversation(chat_id):
    if chat_id == "human-active-chat":
        return {"needs_help": "1"}
    if chat_id == "hold-chat":
        return {"auto_reply_hold_until": "2099-01-01T00:00:00"}
    return {}


def _add_message(**kw):
    return {"ok": True, "message_id": "stub"}


def _mark_read(chat_id):
    return True


def _del_drafts(chat_id):
    return True


def _cairo_time():
    return datetime.now().isoformat()  # naive ISO — كما يعيد النظام (Cairo)


def _update_hold(chat_id, value):
    return True


_stub.get_conversation = _get_conversation
_stub.add_message = _add_message
_stub.mark_conversation_read = _mark_read
_stub.delete_proposed_drafts = _del_drafts
_stub.get_cairo_time = _cairo_time
_stub.update_auto_reply_hold_until = _update_hold
sys.modules["chat_db"] = _stub

# =============================================================================
# 2) تحميل الوحدة من workflows/ + تحويل ملفات الحالة إلى مجلد مؤقت
# =============================================================================
spec = importlib.util.spec_from_file_location(
    "religious_shokran_mesh_mohtam_autoreply",
    os.path.join("workflows", "religious_shokran_mesh_mohtam_autoreply.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

_tmp = tempfile.mkdtemp(prefix="shokran_mohtam_test_")
mod.DEDUP_DB = os.path.join(_tmp, "dedup_test.db")
mod.STATE_FILE = os.path.join(_tmp, "state_test.json")

# =============================================================================
# 3) الرد المتوقع (من طلب المدير 2026-09-03 — حرفياً)
# =============================================================================
EXPECTED_REPLY = (
    "تمام يا فندم، شكرًا لحضرتك على وقتك 🙏\n"
    "مش هنبعت لحضرتك رسائل تانية، ولو احتجت أي حاجة في الحج أو العمرة في أي وقت، إحنا موجودين.\n"
    "ربنا يكتبلك الزيارة قريب 🤲"
)


class MockAgent:
    def __init__(self):
        self.sent = []

    def send_whatsapp_message(self, recipient, text=None, location="Unknown", receiving_phone_id=None, **kw):
        self.sent.append(("whatsapp", recipient, text, location, receiving_phone_id))
        return True, None

    def send_facebook_message(self, recipient, text=None, **kw):
        self.sent.append(("facebook", recipient, text))
        return True, None

    def cancel_whatsapp_ai_processing(self, **kw):
        return True


results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def run_case(body, chat_id="test-chat-x", source="Facebook", sender="psid-x", location="Religious"):
    agent = MockAgent()
    r = mod.run(agent, {
        "chat_id": chat_id,
        "message_body": body,
        "source": source,
        "sender_identifier": sender,
        "location": location,
    })
    return agent, r


# 1) Exact match - Facebook -> يجب إرسال الرد الجديد حرفياً
agent, r = run_case("شكرا مش مهتم", chat_id="test-chat-1", sender="psid-111")
check("exact_fb_sent", r.get("sent") is True and r.get("channel") == "Facebook", str(r))
check("exact_fb_1_msg", len(agent.sent) == 1, f"sent={len(agent.sent)}")
check("reply_content_exact", len(agent.sent) == 1 and agent.sent[0][2] == EXPECTED_REPLY,
      f"GOT={agent.sent[0][2] if agent.sent else None!r}")

# 2) Exact match - WhatsApp + كتابة العميل بالتنوين "شكراً مش مهتم" -> تطابق 100%
agent, r = run_case("شكراً مش مهتم", chat_id="test-chat-2", source="whatsapp",
                    sender="201001234567", location="Religious")
check("tanween_wa_sent", r.get("sent") is True and r.get("channel") == "WhatsApp", str(r))
check("tanween_wa_1_msg", len(agent.sent) == 1 and agent.sent[0][0] == "whatsapp", f"sent={len(agent.sent)}")
check("tanween_wa_content", len(agent.sent) == 1 and agent.sent[0][2] == EXPECTED_REPLY, "wa reply mismatch")

# 3) غير Religious -> ممنوع تماماً (قاعدة 15)
agent, r = run_case("شكرا مش مهتم", chat_id="test-chat-3", location="Hurghada", sender="psid-333")
check("skip_other_dept", r.get("skipped") == "not_religious" and len(agent.sent) == 0, str(r))

# 4) رسالة مختلفة -> لا تطابق
agent, r = run_case("عايز أسعار العمرة", chat_id="test-chat-4")
check("no_match_other_msg", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

# 5) كلمات إضافية -> ليست تطابق 100% (Contains ممنوع)
agent, r = run_case("شكرا مش مهتم دلوقتي", chat_id="test-chat-5")
check("extra_words_no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

# 6) Near-miss: "مش مهتم" وحدها -> ليست التطابق المطلوب (الكلمة الكاملة "شكرا مش مهتم")
agent, r = run_case("مش مهتم", chat_id="test-chat-6")
check("near_miss_no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

# 7) تكرار نفس الرسالة (Webhook duplicate) -> رسالة واحدة فقط إجمالاً
agent = MockAgent()
payload = {
    "chat_id": "test-chat-7", "message_body": "شكرا مش مهتم",
    "source": "Facebook", "sender_identifier": "psid-777", "location": "Religious",
}
r1 = mod.run(agent, payload)
r2 = mod.run(agent, payload)
check("dup_first_sent", r1.get("sent") is True, str(r1))
check("dup_second_skipped", r2.get("skipped") == "already_processed", str(r2))
check("dup_total_1_msg", len(agent.sent) == 1, f"sent={len(agent.sent)}")

# 8) وسائط غير نصية -> skipped
agent, r = run_case("[customer sent an audio message.", chat_id="test-chat-8")
check("media_skipped", r.get("skipped") == "non_text_media" and len(agent.sent) == 0, str(r))

# 9) بيانات ناقصة -> skipped
agent, r = run_case("شكرا مش مهتم", chat_id="test-chat-9", sender="")
check("missing_sender_skipped", r.get("skipped") == "missing_data" and len(agent.sent) == 0, str(r))

# 10) مصدر Email -> غير مدعوم
agent, r = run_case("شكرا مش مهتم", chat_id="test-chat-10", source="email", sender="x@y.com")
check("email_skipped", r.get("skipped") == "unsupported_source" and len(agent.sent) == 0, str(r))

# 11) موظف بشري نشط (needs_help=1) -> لا نتداخل
agent, r = run_case("شكرا مش مهتم", chat_id="human-active-chat")
check("human_active_skipped", r.get("skipped") == "human_active" and len(agent.sent) == 0, str(r))

# 12) محادثة على Hold (auto_reply_hold_until مستقبلي) -> لا نتداخل
agent, r = run_case("شكرا مش مهتم", chat_id="hold-chat")
check("hold_skipped", r.get("skipped") == "human_hold" and len(agent.sent) == 0, str(r))

# 13) تعريف الكلمة مضبوط كما طلبها المدير
check("keyword_exact", mod.KEYWORDS[0]["keyword"] == "شكرا مش مهتم", str(mod.KEYWORDS[0]["keyword"]))
check("keyword_enabled", mod.KEYWORDS[0]["enabled"] is True, str(mod.KEYWORDS[0]))
check("reply_constant_updated", mod.REPLY_SHOKRAN_MESH_MOHTAM == EXPECTED_REPLY, mod.REPLY_SHOKRAN_MESH_MOHTAM)

# ===== Report =====
print("=" * 72)
print("RELIGIOUS SHOKRAN MESH MOHTAM (شكرا مش مهتم) AUTO-REPLY TEST RESULTS")
print("=" * 72)
passed = 0
failed = 0
for name, ok, detail in results:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" | {detail}" if detail else ""))
    if ok:
        passed += 1
    else:
        failed += 1
print("=" * 72)
print(f"TOTAL: {passed} passed, {failed} failed out of {len(results)}")
print("=" * 72)
sys.exit(0 if failed == 0 else 1)
