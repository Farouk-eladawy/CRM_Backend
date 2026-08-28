# -*- coding: utf-8 -*-
"""اختبار شامل لـ workflows/religious_haram_comfort_autoreply.py"""
import sys, io, json, importlib.util, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

spec = importlib.util.spec_from_file_location(
    "religious_haram_comfort_autoreply",
    os.path.join("workflows", "religious_haram_comfort_autoreply.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# الرسالة المتوقعة (من طلب المدير — حرفياً)
EXPECTED_MSG = (
    "اختيار موفق 👍 الأنسب لحضرتك غالبًا برنامج التحسين.\n"
    "\n"
    "ومعلومة مهمة من خبرتنا: أكتر وقت الحاج بيحس فيه بالتعب مش في المناسك نفسها — في الأيام اللي بعد عرفات ومنى. "
    "وده بالظبط اللي البرنامج بيحله: أطول فترة تحسين — ٧ أيام كاملة في فندق ٥ نجوم على ساحة الحرم — يعني مش كل صلاة محتاجة باص وانتظار.\n"
    "\n"
    "💰 البرنامج كان في الموسم السابق بـ ٢٧٩,٠٠٠ جنيه، وبعد خصم ٢٩,٠٠٠ جنيه بيبقى ٢٥٠,٠٠٠ جنيه بس — "
    "والسعر النهائي لموسم ١٤٤٨ بيتحدد بعد صدور الضوابط الرسمية.\n"
    "\n"
    "لو الرقم مناسب لحضرتك، ابعتلي رقم تليفونك وهيكلمك متخصص يشرحلك مكونات التحسين بالتفصيل "
    "ويحجزلك مكانك قبل اكتمال العدد. 📞"
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

# 0) نص الرد مطابق تماماً لطلب المدير
check("reply_text_exact", mod.REPLY_HARAM_COMFORT == EXPECTED_MSG,
      f"len={len(mod.REPLY_HARAM_COMFORT)} vs {len(EXPECTED_MSG)}")

# 1) Exact match بالكلمة مع الإيموجي - Facebook -> إرسال رسالة واحدة بالرد الصحيح
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-haram-1", "message_body": "🕋 الراحة والقرب من الحرم",
    "source": "Facebook", "sender_identifier": "psid-111",
    "location": "Religious",
})
check("exact_match_fb_sent", r.get("sent") is True and r.get("channel") == "Facebook", str(r))
check("exact_match_fb_1_msg", len(agent.sent) == 1, f"sent={len(agent.sent)}")
check("exact_match_fb_content", len(agent.sent) == 1 and agent.sent[0][2] == EXPECTED_MSG, "content mismatch")
check("exact_match_fb_keyword", r.get("keyword") == "🕋 الراحة والقرب من الحرم", str(r.get("keyword")))

# 2) Exact match بدون الإيموجي (التطبيع يزيل الإيموجي - نفس سلوك المحرك)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-haram-2", "message_body": "الراحة والقرب من الحرم",
    "source": "Facebook", "sender_identifier": "psid-222",
    "location": "Religious",
})
check("exact_match_no_emoji", r.get("sent") is True and len(agent.sent) == 1, str(r))

# 3) Non-Religious location MUST be skipped (قاعدة 15 - فلترة صارمة)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-haram-3", "message_body": "🕋 الراحة والقرب من الحرم",
    "source": "Facebook", "sender_identifier": "psid-333",
    "location": "Hurghada",
})
check("skip_other_dept", r.get("skipped") == "not_religious" and len(agent.sent) == 0, str(r))

# 4) Different message -> no keyword match
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-haram-4", "message_body": "عايز أسعار العمرة",
    "source": "Facebook", "sender_identifier": "psid-444",
    "location": "Religious",
})
check("no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

# 5) Extra words -> NOT exact match (Contains ممنوع - أي كلمة إضافية تكسر المساواة)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-haram-5", "message_body": "عايز اعرف الراحة والقرب من الحرم من فضلك",
    "source": "Facebook", "sender_identifier": "psid-555",
    "location": "Religious",
})
check("extra_words_no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

# 6) Near-miss "الراحة والقرب من الحرمين" -> لا تطابق (لا نتعارض مع عبارات أخرى)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-haram-6", "message_body": "الراحة والقرب من الحرمين",
    "source": "Facebook", "sender_identifier": "psid-666",
    "location": "Religious",
})
check("near_miss_no_match", r.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(r))

# 7) WhatsApp channel -> إرسال عبر واتساب بالمعاملات الصحيحة
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-haram-7", "message_body": "🕋 الراحة والقرب من الحرم",
    "source": "whatsapp", "sender_identifier": "201001234567",
    "location": "Religious", "receiving_phone_id": "1029384756",
})
check("wa_sent", r.get("sent") is True and r.get("channel") == "WhatsApp", str(r))
check("wa_channel_used", len(agent.sent) == 1 and agent.sent[0][0] == "whatsapp", f"sent={agent.sent}")
check("wa_content", len(agent.sent) == 1 and agent.sent[0][2] == EXPECTED_MSG, "wa content mismatch")

# 8) Duplicate delivery -> already_processed (حجز ذري يمنع تكرار الإرسال)
agent = MockAgent()
r1 = mod.run(agent, {
    "chat_id": "test-haram-8", "message_body": "🕋 الراحة والقرب من الحرم",
    "source": "Facebook", "sender_identifier": "psid-888",
    "location": "Religious",
})
r2 = mod.run(agent, {
    "chat_id": "test-haram-8", "message_body": "🕋 الراحة والقرب من الحرم",
    "source": "Facebook", "sender_identifier": "psid-888",
    "location": "Religious",
})
check("dup_first_sent", r1.get("sent") is True, str(r1))
check("dup_second_skipped", r2.get("skipped") == "already_processed", str(r2))
check("dup_total_1_msg", len(agent.sent) == 1, f"sent={len(agent.sent)}")

# 9) Missing data -> skipped
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "", "message_body": "🕋 الراحة والقرب من الحرم",
    "source": "Facebook", "sender_identifier": "psid-999",
    "location": "Religious",
})
check("missing_data", r.get("skipped") == "missing_data" and len(agent.sent) == 0, str(r))

# 10) Non-text media -> skipped
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-haram-10", "message_body": "[customer sent an audio message.",
    "source": "Facebook", "sender_identifier": "psid-1010",
    "location": "Religious",
})
check("media_skipped", r.get("skipped") == "non_text_media" and len(agent.sent) == 0, str(r))

# 11) طلب المدير: فيسبوك/واتساب فقط — مصدر Email يُتجاهل تماماً
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-haram-11", "message_body": "🕋 الراحة والقرب من الحرم",
    "source": "email", "sender_identifier": "user@example.com",
    "location": "Religious",
})
check("source_email_skipped", r.get("skipped") == "unsupported_source" and len(agent.sent) == 0, str(r))

# 12) مصدر Instagram يُتجاهل تماماً (غير فيسبوك/واتساب)
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-haram-12", "message_body": "🕋 الراحة والقرب من الحرم",
    "source": "instagram", "sender_identifier": "ig-user",
    "location": "Religious",
})
check("source_instagram_skipped", r.get("skipped") == "unsupported_source" and len(agent.sent) == 0, str(r))

# 13) مصدر "Facebook" بأحرف كبيرة (case-insensitive) -> يعمل
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-haram-13", "message_body": "🕋 الراحة والقرب من الحرم",
    "source": "Facebook", "sender_identifier": "psid-1313",
    "location": "Religious",
})
check("source_fb_case_insensitive", r.get("sent") is True and len(agent.sent) == 1, str(r))

# 14) مصدر "WhatsApp" بأحرف كبيرة (case-insensitive) -> يعمل
agent = MockAgent()
r = mod.run(agent, {
    "chat_id": "test-haram-14", "message_body": "🕋 الراحة والقرب من الحرم",
    "source": "WhatsApp", "sender_identifier": "201005555555",
    "location": "Religious", "receiving_phone_id": "1029384756",
})
check("source_wa_case_insensitive", r.get("sent") is True and len(agent.sent) == 1, str(r))

# ===== التقرير =====
print("\n" + "=" * 70)
print("نتائج اختبار Workflow: 🕋 الراحة والقرب من الحرم")
print("=" * 70)
all_ok = True
for name, ok, detail in results:
    status = "✅ PASS" if ok else "❌ FAIL"
    if not ok:
        all_ok = False
    print(f"{status}  {name}" + (f"  | {detail}" if detail else ""))
print("=" * 70)
print("النتيجة النهائية:", "ALL PASS ✅" if all_ok else "THERE ARE FAILURES ❌")
sys.exit(0 if all_ok else 1)
