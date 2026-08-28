# -*- coding: utf-8 -*-
"""اختبار شامل لـ workflows/send_my_number_and_id_autoreply.py (تحديث رد برنامج الحج)"""
import sys, io, json, importlib.util, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

spec = importlib.util.spec_from_file_location(
    "send_my_number_and_id_autoreply",
    os.path.join("workflows", "send_my_number_and_id_autoreply.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# تنظيف سجلات الاختبار من قاعدة منع التكرار (تجنب تأثير التشغيلات السابقة)
try:
    import sqlite3
    _dedup_path = mod.DEDUP_DB
    with sqlite3.connect(_dedup_path, timeout=30.0) as _conn:
        _conn.execute("DELETE FROM send_my_number_and_id_reply_dedup WHERE chat_id LIKE 'test-chat-%'")
        _conn.commit()
except Exception as e:
    print("WARN: could not clean test dedup rows:", e)

# الرد المتوقع (من طلب المدير 2026-08-28 — رد تسجيل برنامج الحج)
EXPECTED_REPLY = (
    "تمام يا فندم 🌙\n"
    "علشان نسجّل حضرتك معانا في برنامج الحج، محتاجين منك حاجتين بس:\n"
    "\n"
    "📱 رقم الموبايل (اللي عليه واتساب)\n"
    "🪪 صورة بطاقة الرقم القومي (واضحة ومقروءة)\n"
    "\n"
    "أول ما توصلنا البيانات، هيتواصل معاك حد من فريقنا فورًا لاستكمال التسجيل وإجابة كل استفساراتك إن شاء الله."
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

# 1) Exact match - Facebook (Religious)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-1", "message_body": "ابعت رقمي وصورة البطاقة",
    "source": "Facebook", "sender_identifier": "psid-111",
    "location": "Religious",
})
check("exact_match_fb_sent", r.get("sent") is True and r.get("channel") == "Facebook", str(r))
check("exact_match_fb_text", len(agent.sent) == 1 and agent.sent[0][2] == EXPECTED_REPLY,
      "text mismatch: " + repr((agent.sent[0][2] if agent.sent else None)))

# 2) Exact match - WhatsApp (Religious)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-2", "message_body": "ابعت رقمي وصورة البطاقة",
    "source": "whatsapp", "sender_identifier": "201001234567",
    "location": "Religious", "receiving_phone_id": "1029384756",
})
check("exact_match_wa_sent", r.get("sent") is True and r.get("channel") == "WhatsApp", str(r))
check("exact_match_wa_text", len(agent.sent) == 1 and agent.sent[0][2] == EXPECTED_REPLY, "text mismatch")

# 3) Non-Religious location MUST be skipped (قاعدة 15)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-3", "message_body": "ابعت رقمي وصورة البطاقة",
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
    "chat_id": "test-chat-5", "message_body": "عايز ابعت رقمي وصورة البطاقة من فضلك",
    "source": "Facebook", "sender_identifier": "psid-555",
    "location": "Religious",
})
check("extra_words_no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

# 6) Exact match with punctuation/emoji variation (normalization -> still exact)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-6", "message_body": "ابعت رقمي وصورة البطاقة!",
    "source": "Facebook", "sender_identifier": "psid-666",
    "location": "Religious",
})
check("punctuation_normalized_match", r.get("sent") is True and len(agent.sent) == 1, str(r))

# 7) Duplicate delivery -> already_processed (Atomic claim)
agent = MockAgent()
r1 = mod.run(agent, {
    "chat_id": "test-chat-7", "message_body": "ابعت رقمي وصورة البطاقة",
    "source": "Facebook", "sender_identifier": "psid-777",
    "location": "Religious",
})
r2 = mod.run(agent, {
    "chat_id": "test-chat-7", "message_body": "ابعت رقمي وصورة البطاقة",
    "source": "Facebook", "sender_identifier": "psid-777",
    "location": "Religious",
})
check("first_send_ok", r1.get("sent") is True, str(r1))
check("duplicate_blocked", r2.get("skipped") == "already_processed" and len(agent.sent) == 1, str(r2))

# 8) Missing data -> skipped (location Religious so we reach the data check)
r = mod.run(MockAgent(), {"chat_id": "", "message_body": "ابعت رقمي وصورة البطاقة", "sender_identifier": "", "location": "Religious"})
check("missing_data", r.get("skipped") == "missing_data", str(r))

# 9) Empty/missing location -> safe skip (not_religious, nothing sent)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-9", "message_body": "ابعت رقمي وصورة البطاقة",
    "source": "Facebook", "sender_identifier": "psid-999", "location": "",
})
check("empty_location_skip", r.get("skipped") == "not_religious" and len(agent.sent) == 0, str(r))

print("=" * 70)
passed = 0
for name, ok, detail in results:
    print(("✅" if ok else "❌"), name, ("| " + detail[:200] if detail and not ok else ""))
    passed += 1 if ok else 0
print("=" * 70)
print(f"PASSED {passed}/{len(results)}")
sys.exit(0 if passed == len(results) else 1)
