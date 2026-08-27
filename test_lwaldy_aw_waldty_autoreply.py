# -*- coding: utf-8 -*-
"""اختبار شامل لـ workflows/religious_lwaldy_aw_waldty_autoreply.py"""
import sys, io, json, importlib.util, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

spec = importlib.util.spec_from_file_location(
    "religious_lwaldy_aw_waldty_autoreply",
    os.path.join("workflows", "religious_lwaldy_aw_waldty_autoreply.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# الرد المتوقع (من طلب المدير)
EXPECTED_REPLY = (
    "أهلًا بحضرتك 🌿 ربنا يبلّغ والدك عنك.\n"
    "ده خط سير برنامج طيران تحسين ببساطة:\n"
    "\n"
    "🕌 المدينة المنورة — من ٢ إلى ٥ ذو الحجة\n"
    "إقامة قريبة من الحرم + إفطار وعشاء\n"
    "\n"
    "🚄 قطار الحرمين من المدينة لمكة\n"
    "\n"
    "🕋 مكة قبل المناسك — من ٦ إلى ٨ ذو الحجة\n"
    "إقامة فندقية + إفطار وعشاء\n"
    "\n"
    "⛺ المناسك — من ٩ إلى ١٣ ذو الحجة\n"
    "عرفات ومزدلفة ومنى، مخيمات مكيفة ووجبات ومشروبات، ومشرف الشركة مع والدك طول الوقت\n"
    "\n"
    "⭐ التحسين على ساحة الحرم — من ١٤ إلى ٢٠ ذو الحجة\n"
    "ودي أهم ميزة للوالدين تحديدًا: بعد تعب المناسك، والدك بيكون على الحرم مباشرة، يصلي ويرجع يرتاح، من غير باص ولا مشاوير.\n"
    "\n"
    "💰 السعر ٢٥٠ ألف بدل ٢٧٩ بخصم الحجز المبكر (بسعر الموسم اللي فات، والتأكيد بعد ضوابط الوزارة — والخصم بيتثبت باسم الحاج مهما كان السعر النهائي). تذكرة الطيران بتتضاف بسعرها وقت الحجز.\n"
    "\n"
    "والدك هيسافر لوحده ولا معاه حد؟ ولو تحب أكلم حضرتك دقيقتين أشرحلك طرق الدفع والتقسيط — رقمك عليه واتساب؟"
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

# 1) Exact match - Facebook
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-1", "message_body": "لوالدي أو والدتي",
    "source": "Facebook", "sender_identifier": "psid-111",
    "location": "Religious",
})
check("exact_match_fb_sent", r.get("sent") is True and r.get("channel") == "Facebook", str(r))
check("exact_match_fb_text", len(agent.sent) == 1 and agent.sent[0][2] == EXPECTED_REPLY, "text length mismatch")

# 2) Exact match - WhatsApp
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-2", "message_body": "لوالدي أو والدتي",
    "source": "whatsapp", "sender_identifier": "201001234567",
    "location": "Religious", "receiving_phone_id": "1029384756",
})
check("exact_match_wa_sent", r.get("sent") is True and r.get("channel") == "WhatsApp", str(r))

# 3) Non-Religious location MUST be skipped (قاعدة 15)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-3", "message_body": "لوالدي أو والدتي",
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
    "chat_id": "test-chat-5", "message_body": "عايز حجز لوالدي أو والدتي من فضلك",
    "source": "Facebook", "sender_identifier": "psid-555",
    "location": "Religious",
})
check("extra_words_no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

# 6) Duplicate delivery -> already_processed (Atomic claim)
agent = MockAgent()
payload = {
    "chat_id": "test-chat-6", "message_body": "لوالدي أو والدتي",
    "source": "Facebook", "sender_identifier": "psid-666",
    "location": "Religious",
}
r1 = mod.run(agent, payload)
r2 = mod.run(agent, payload)
check("dup_first_sent", r1.get("sent") is True, str(r1))
check("dup_second_skipped", r2.get("skipped") == "already_processed" and len(agent.sent) == 1, str(r2))

# 7) Normalized punctuation still matches (نفس المحتوى + نقطة)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-7", "message_body": "لوالدي أو والدتي.",
    "source": "Facebook", "sender_identifier": "psid-777",
    "location": "Religious",
})
check("punct_normalized_match", r.get("sent") is True, str(r))

print("\n==================== TEST RESULTS ====================")
all_ok = True
for name, ok, detail in results:
    print(f"{'✅' if ok else '❌'} {name} | {detail}")
    if not ok:
        all_ok = False
print("======================================================")
print("ALL PASSED" if all_ok else "SOME FAILED")
