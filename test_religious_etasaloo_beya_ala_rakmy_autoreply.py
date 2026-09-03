# -*- coding: utf-8 -*-
"""اختبار شامل لـ workflows/religious_etasaloo_beya_ala_rakmy_autoreply.py"""
import sys, io, json, importlib.util, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

spec = importlib.util.spec_from_file_location(
    "religious_etasaloo_beya_ala_rakmy_autoreply",
    os.path.join("workflows", "religious_etasaloo_beya_ala_rakmy_autoreply.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# الرد المتوقع (من طلب المدير — حرفياً)
EXPECTED_REPLY = (
    "في خدمه حضرتك 👍 اكتبلي رقم حضرتك هنا واختارنا اي برنامج وهكلمك النهارده إن شاء الله."
)

# ===== عزل ملفات الحالة (Dedup/State) في مجلد مؤقت حتى لا نلوث ملفات الإنتاج =====
import tempfile
_TMP_DIR = tempfile.mkdtemp(prefix="etasaloo_test_")
mod.DEDUP_DB = os.path.join(_TMP_DIR, "dedup.db")
mod.STATE_FILE = os.path.join(_TMP_DIR, "state.json")

# ===== عزل الاختبار عن قاعدة المحادثات الحية (chat_history.db) =====
# نستبدل دوال chat_db مؤقتاً حتى لا تُكتب رسائل test-chat-* في قاعدة حقيقية.
import chat_db as _real_chat_db
_ORIG = {}
for _fn in ("get_conversation", "update_auto_reply_hold_until", "add_message",
            "mark_conversation_read", "delete_proposed_drafts", "get_cairo_time"):
    try:
        _ORIG[_fn] = getattr(_real_chat_db, _fn)
    except Exception:
        pass

def _fake_get_conversation(chat_id):
    return {"chat_id": chat_id, "needs_help": 0, "auto_reply_hold_until": None}

_real_chat_db.get_conversation = _fake_get_conversation
_real_chat_db.update_auto_reply_hold_until = lambda *a, **k: None
_real_chat_db.add_message = lambda *a, **k: None
_real_chat_db.mark_conversation_read = lambda *a, **k: None
_real_chat_db.delete_proposed_drafts = lambda *a, **k: None
_real_chat_db.get_cairo_time = lambda: "2026-09-03T12:00:00+03:00"

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

try:
    # 1) Exact match - Facebook -> يجب إرسال الرد حرفياً
    agent = MockAgent()
    r = mod.run(agent, {
        "chat_id": "test-chat-1", "message_body": "📞 اتصلوا بيا على رقمي",
        "source": "Facebook", "sender_identifier": "psid-111",
        "location": "Religious",
    })
    check("exact_match_fb_sent", r.get("sent") is True and r.get("channel") == "Facebook", str(r))
    check("exact_match_fb_1_msg", len(agent.sent) == 1, f"sent={len(agent.sent)}")
    check("reply_content_exact", len(agent.sent) == 1 and agent.sent[0][2] == EXPECTED_REPLY, "reply mismatch")

    # 2) Exact match بدون الإيموجي 📞 -> يجب أن يطابق (توحيد الرموز غير الحرفية) - WhatsApp
    agent = MockAgent()
    r = mod.run(agent, {
        "chat_id": "test-chat-2", "message_body": "اتصلوا بيا على رقمي",
        "source": "whatsapp", "sender_identifier": "201001234567",
        "location": "Religious", "receiving_phone_id": "1029384756",
    })
    check("no_emoji_wa_sent", r.get("sent") is True and r.get("channel") == "WhatsApp", str(r))
    check("no_emoji_wa_1_msg", len(agent.sent) == 1 and agent.sent[0][0] == "whatsapp", f"sent={len(agent.sent)}")
    check("no_emoji_wa_content", len(agent.sent) == 1 and agent.sent[0][2] == EXPECTED_REPLY, "wa reply mismatch")

    # 3) Non-Religious location MUST be skipped (قاعدة 15)
    agent = MockAgent()
    r = mod.run(agent, {
        "chat_id": "test-chat-3", "message_body": "📞 اتصلوا بيا على رقمي",
        "source": "Facebook", "sender_identifier": "psid-333",
        "location": "Hurghada",
    })
    check("skip_other_dept", r.get("skipped") == "not_religious" and len(agent.sent) == 0, str(r))

    # 4) Different message -> no keyword match
    agent = MockAgent()
    r = mod.run(agent, {
        "chat_id": "test-chat-4", "message_body": "عايز أسعار العمرة",
        "source": "Facebook", "sender_identifier": "psid-444",
        "location": "Religious",
    })
    check("no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

    # 5) Extra words -> NOT exact match (Contains ممنوع)
    agent = MockAgent()
    r = mod.run(agent, {
        "chat_id": "test-chat-5", "message_body": "📞 اتصلوا بيا على رقمي لو سمحت",
        "source": "Facebook", "sender_identifier": "psid-555",
        "location": "Religious",
    })
    check("extra_words_no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

    # 6) Near-miss spelling (علي بدل على) -> NOT exact match
    agent = MockAgent()
    r = mod.run(agent, {
        "chat_id": "test-chat-6", "message_body": "اتصلوا بيا علي رقمي",
        "source": "Facebook", "sender_identifier": "psid-666",
        "location": "Religious",
    })
    check("near_miss_spelling_no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

    # 7) Near-miss (أيوه، أحجزلي مكان - Workflow آخر) -> NOT exact match (لا تعارض)
    agent = MockAgent()
    r = mod.run(agent, {
        "chat_id": "test-chat-7", "message_body": "أيوه، أحجزلي مكان",
        "source": "Facebook", "sender_identifier": "psid-777",
        "location": "Religious",
    })
    check("near_miss_other_wf_no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

    # 8) Duplicate delivery -> already_processed (Atomic claim) + رسالة واحدة فقط
    agent = MockAgent()
    payload = {
        "chat_id": "test-chat-8", "message_body": "📞 اتصلوا بيا على رقمي",
        "source": "Facebook", "sender_identifier": "psid-888",
        "location": "Religious",
    }
    r1 = mod.run(agent, payload)
    r2 = mod.run(agent, payload)
    check("dup_first_sent", r1.get("sent") is True, str(r1))
    check("dup_second_skipped", r2.get("skipped") == "already_processed", str(r2))
    check("dup_total_1_msg", len(agent.sent) == 1, f"sent={len(agent.sent)}")

    # 9) Non-text media -> skipped
    agent = MockAgent()
    r = mod.run(agent, {
        "chat_id": "test-chat-9", "message_body": "[customer sent an audio message.",
        "source": "Facebook", "sender_identifier": "psid-999",
        "location": "Religious",
    })
    check("media_skipped", r.get("skipped") == "non_text_media" and len(agent.sent) == 0, str(r))

    # 10) Missing sender -> skipped
    agent = MockAgent()
    r = mod.run(agent, {
        "chat_id": "test-chat-10", "message_body": "📞 اتصلوا بيا على رقمي",
        "source": "Facebook", "sender_identifier": "",
        "location": "Religious",
    })
    check("missing_sender_skipped", r.get("skipped") == "missing_data" and len(agent.sent) == 0, str(r))

    # 11) Email source -> unsupported_source
    agent = MockAgent()
    r = mod.run(agent, {
        "chat_id": "test-chat-11", "message_body": "📞 اتصلوا بيا على رقمي",
        "source": "email", "sender_identifier": "x@y.com",
        "location": "Religious",
    })
    check("email_skipped", r.get("skipped") == "unsupported_source" and len(agent.sent) == 0, str(r))

    # 12) Keyword entry is defined exactly as requested
    check("keyword_exact", mod.KEYWORDS[0]["keyword"] == "📞 اتصلوا بيا على رقمي", str(mod.KEYWORDS[0]["keyword"]))
    check("reply_exact", mod.KEYWORDS[0]["reply"] == EXPECTED_REPLY, str(mod.KEYWORDS[0]["reply"]))
    check("keyword_enabled", mod.KEYWORDS[0]["enabled"] is True, str(mod.KEYWORDS[0]))
finally:
    # ===== استعادة chat_db الحقيقي بعد الاختبار =====
    for _fn, _orig in _ORIG.items():
        try:
            setattr(_real_chat_db, _fn, _orig)
        except Exception:
            pass

# ===== Report =====
print("=" * 70)
print("RELIGIOUS ETASALOO BEYA ALA RAKMY AUTO-REPLY TEST RESULTS")
print("=" * 70)
passed = 0
failed = 0
for name, ok, detail in results:
    mark = "✅ PASS" if ok else "❌ FAIL"
    print(f"{mark} | {name}" + (f" | {detail}" if detail else ""))
    if ok:
        passed += 1
    else:
        failed += 1
print("=" * 70)
print(f"TOTAL: {passed} passed, {failed} failed out of {len(results)}")
print("=" * 70)
sys.exit(0 if failed == 0 else 1)
