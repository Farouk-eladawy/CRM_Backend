# -*- coding: utf-8 -*-
"""اختبار شامل لـ workflows/religious_la_ma_qaddamtch_autoreply.py"""
import sys, io, json, importlib.util, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

spec = importlib.util.spec_from_file_location(
    "religious_la_ma_qaddamtch_autoreply",
    os.path.join("workflows", "religious_la_ma_qaddamtch_autoreply.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# الرد المتوقع (من طلب المدير — حرفياً)
EXPECTED_REPLY = (
    "تمام يا حاج، يبقى باب حج السياحة مفتوح ليك بالكامل ✅\n"
    "\n"
    "أسعار حج ١٤٤٨ بعد خصم التسجيل المبكر:\n"
    "\n"
    "🚌 بري: ٢١٠,٠٠٠ بدل ٢٢٠,٠٠٠ (خصم ١٠,٠٠٠)\n"
    "✈️ طيران اقتصادي: ٢٢٠,٠٠٠ بدل ٢٤٥,٠٠٠ (خصم ٢٥,٠٠٠)\n"
    "✈️ طيران تحسين: ٢٥٠,٠٠٠ بدل ٢٧٩,٠٠٠ (خصم ٢٩,٠٠٠)\n"
    "🏨 ومتاح كمان ٥ نجوم وكدانة\n"
    "\n"
    "كل البرامج شاملة الوجبات يوميًا، مخيمات مكيفة، وإشراف ديني وإداري معاك من أول يوم.\n"
    "\n"
    "الأسعار بأسعار موسم ١٤٤٧ لحد ما ضوابط ١٤٤٨ تنزل، والخصم ثابت ليك بمجرد التسجيل.\n"
    "\n"
    "📌 التسجيل دلوقتي بصورة البطاقة .\n"
    "\n"
    "ابعتلنا رقم موبايلك عشان نكلمك ونشرحلك أكتر — يناسبك دلوقتي ولا في وقت معين؟"
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

# 1) Exact match - Facebook -> يجب إرسال الرد حرفياً
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-1", "message_body": "لا، ما قدمتش",
    "source": "Facebook", "sender_identifier": "psid-111",
    "location": "Religious",
})
check("exact_match_fb_sent", r.get("sent") is True and r.get("channel") == "Facebook", str(r))
check("exact_match_fb_1_msg", len(agent.sent) == 1, f"sent={len(agent.sent)}")
check("reply_content_exact", len(agent.sent) == 1 and agent.sent[0][2] == EXPECTED_REPLY, "reply mismatch")

# 2) Exact match - WhatsApp -> عبر واتساب
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-2", "message_body": "لا، ما قدمتش",
    "source": "whatsapp", "sender_identifier": "201001234567",
    "location": "Religious", "receiving_phone_id": "1029384756",
})
check("exact_match_wa_sent", r.get("sent") is True and r.get("channel") == "WhatsApp", str(r))
check("exact_match_wa_1_msg", len(agent.sent) == 1 and agent.sent[0][0] == "whatsapp", f"sent={len(agent.sent)}")
check("wa_content_exact", len(agent.sent) == 1 and agent.sent[0][2] == EXPECTED_REPLY, "wa reply mismatch")

# 3) Non-Religious location MUST be skipped (قاعدة 15)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-3", "message_body": "لا، ما قدمتش",
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
    "chat_id": "test-chat-5", "message_body": "لا، ما قدمتش لسه",
    "source": "Facebook", "sender_identifier": "psid-555",
    "location": "Religious",
})
check("extra_words_no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

# 6) Near-miss (لسه ما قدّمتش - Workflow آخر) -> NOT exact match (يجب ألا يتعارض)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-8", "message_body": "لسه ما قدّمتش",
    "source": "Facebook", "sender_identifier": "psid-888",
    "location": "Religious",
})
check("near_miss_other_wf_no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

# 7) Near-miss (قدّمت خلاص - Workflow آخر) -> NOT exact match
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-10", "message_body": "قدّمت خلاص",
    "source": "Facebook", "sender_identifier": "psid-1010",
    "location": "Religious",
})
check("near_miss_applied_no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

# 8) Duplicate delivery -> already_processed (Atomic claim) + رسالة واحدة فقط إجمالاً
agent = MockAgent()
payload = {
    "chat_id": "test-chat-6", "message_body": "لا، ما قدمتش",
    "source": "Facebook", "sender_identifier": "psid-666",
    "location": "Religious",
}
r1 = mod.run(agent, payload)
r2 = mod.run(agent, payload)
check("dup_first_sent", r1.get("sent") is True, str(r1))
check("dup_second_skipped", r2.get("skipped") == "already_processed" and len(agent.sent) == 1, str(r2))

# 9) Normalized punctuation still matches (فاصلة/نقطة — نفس منطق المحرك الرسمي)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-7", "message_body": "لا، ما قدمتش.",
    "source": "Facebook", "sender_identifier": "psid-777",
    "location": "Religious",
})
check("punct_normalized_match", r.get("sent") is True and len(agent.sent) == 1, str(r))

# 10) Message without comma matches (لا ما قدمتش) - نفس النص بعد إزالة الرموز
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-9", "message_body": "لا ما قدمتش",
    "source": "Facebook", "sender_identifier": "psid-999",
    "location": "Religious",
})
check("no_comma_normalized_match", r.get("sent") is True and len(agent.sent) == 1, str(r))

# 11) Media message -> skipped non_text_media
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-11", "message_body": "[customer sent an audio message.]",
    "source": "Facebook", "sender_identifier": "psid-1111",
    "location": "Religious",
})
check("media_skipped", r.get("skipped") == "non_text_media" and len(agent.sent) == 0, str(r))

print("\n==================== TEST RESULTS ====================")
all_ok = True
for name, ok, detail in results:
    print(f"{'✅' if ok else '❌'} {name} | {detail}")
    if not ok:
        all_ok = False
print("======================================================")
print("ALL PASSED" if all_ok else "SOME FAILED")
