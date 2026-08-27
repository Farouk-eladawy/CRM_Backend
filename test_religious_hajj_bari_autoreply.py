# -*- coding: utf-8 -*-
"""اختبار شامل لـ workflows/religious_hajj_bari_autoreply.py"""
import sys, io, json, importlib.util, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

spec = importlib.util.spec_from_file_location(
    "religious_hajj_bari_autoreply",
    os.path.join("workflows", "religious_hajj_bari_autoreply.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# الرسالتان المتوقعتان (من طلب المدير — حرفياً)
EXPECTED_MSG_1 = (
    "برنامج الحج البري مع FTS للسياحة 🕋\n"
    "⏳ المدة: ١٧ يوم (خط السير على أساس الموسم اللي فات)\n"
    "\n"
    "🕌 المدينة المنورة — من ٢ إلى ٥ ذو الحجة\n"
    "فندق بالمنطقة المركزية، ٥ دقايق مشي للحرم — إفطار وعشاء أوبن بوفيه\n"
    "\n"
    "🕋 مكة قبل المناسك — من ٦ إلى ٨ ذو الحجة\n"
    "عمارة فندقية — إفطار وعشاء\n"
    "\n"
    "⛺ المناسك — من ٩ إلى ١٣ ذو الحجة\n"
    "مخيمات ألماني مكيفة — إفطار وغداء وعشاء أوبن بوفيه + مشروبات وسناكس\n"
    "\n"
    "🕋 العزيزية — من ١٤ إلى ١٧ ذو الحجة\n"
    "إفطار وعشاء\n"
    "\n"
    "✅ مشرف مرافق معتمد ووجبات طوال الرحلة\n"
    "✅ حجك على سنة النبي ﷺ: المبيت في منى أيام التشريق والمبيت في مزدلفة"
)

EXPECTED_MSG_2 = (
    "💰 السعر ٢١٠ ألف بدل ٢٢٠ بخصم الحجز المبكر، على أساس الموسم اللي فات، والتأكيد بعد ضوابط الوزارة.\n"
    "والخصم ليه أولوية لمن يسجّل ملفه من دلوقتي. غير شامل تذكرة العبّارة.\n"
    "\n"
    "الموسم اللي فات البري خلص بدري، فأسهل حاجة أكلمك دقيقتين ونفتح ملفك — رقمك عليه واتساب؟"
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

# 1) Exact match - Facebook -> يجب إرسال رسالتين بالترتيب الصحيح
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-1", "message_body": "برنامج حج بري",
    "source": "Facebook", "sender_identifier": "psid-111",
    "location": "Religious",
})
check("exact_match_fb_sent", r.get("sent") is True and r.get("channel") == "Facebook", str(r))
check("exact_match_fb_2_msgs", len(agent.sent) == 2, f"sent={len(agent.sent)}")
check("msg1_order_content", len(agent.sent) == 2 and agent.sent[0][2] == EXPECTED_MSG_1, "msg1 mismatch")
check("msg2_order_content", len(agent.sent) == 2 and agent.sent[1][2] == EXPECTED_MSG_2, "msg2 mismatch")

# 2) Exact match - WhatsApp -> رسالتين عبر واتساب
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-2", "message_body": "برنامج حج بري",
    "source": "whatsapp", "sender_identifier": "201001234567",
    "location": "Religious", "receiving_phone_id": "1029384756",
})
check("exact_match_wa_sent", r.get("sent") is True and r.get("channel") == "WhatsApp", str(r))
check("exact_match_wa_2_msgs", len(agent.sent) == 2 and all(m[0] == "whatsapp" for m in agent.sent), f"sent={len(agent.sent)}")
check("wa_msg1_content", len(agent.sent) == 2 and agent.sent[0][2] == EXPECTED_MSG_1, "wa msg1 mismatch")
check("wa_msg2_content", len(agent.sent) == 2 and agent.sent[1][2] == EXPECTED_MSG_2, "wa msg2 mismatch")

# 3) Non-Religious location MUST be skipped (قاعدة 15)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-3", "message_body": "برنامج حج بري",
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
    "chat_id": "test-chat-5", "message_body": "عايز اعرف برنامج حج بري من فضلك",
    "source": "Facebook", "sender_identifier": "psid-555",
    "location": "Religious",
})
check("extra_words_no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

# 6) Near-miss (حج جوي) -> NOT exact match (يجب ألا يرد على برنامج آخر)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-8", "message_body": "برنامج حج طيران",
    "source": "Facebook", "sender_identifier": "psid-888",
    "location": "Religious",
})
check("near_miss_no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

# 7) Duplicate delivery -> already_processed (Atomic claim) + رسالتان فقط إجمالاً
agent = MockAgent()
payload = {
    "chat_id": "test-chat-6", "message_body": "برنامج حج بري",
    "source": "Facebook", "sender_identifier": "psid-666",
    "location": "Religious",
}
r1 = mod.run(agent, payload)
r2 = mod.run(agent, payload)
check("dup_first_sent", r1.get("sent") is True and r1.get("sent_count") == 2, str(r1))
check("dup_second_skipped", r2.get("skipped") == "already_processed" and len(agent.sent) == 2, str(r2))

# 8) Normalized punctuation still matches (نفس المحتوى + نقطة)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-7", "message_body": "برنامج حج بري.",
    "source": "Facebook", "sender_identifier": "psid-777",
    "location": "Religious",
})
check("punct_normalized_match", r.get("sent") is True and len(agent.sent) == 2, str(r))

# 9) Emoji in message (مثل 👍 في طلب المدير) -> يزال الإيموجي ويتم التطابق
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-chat-9", "message_body": "برنامج حج بري 👍",
    "source": "Facebook", "sender_identifier": "psid-999",
    "location": "Religious",
})
check("emoji_normalized_match", r.get("sent") is True and len(agent.sent) == 2, str(r))

print("\n==================== TEST RESULTS ====================")
all_ok = True
for name, ok, detail in results:
    print(f"{'✅' if ok else '❌'} {name} | {detail}")
    if not ok:
        all_ok = False
print("======================================================")
print("ALL PASSED" if all_ok else "SOME FAILED")
