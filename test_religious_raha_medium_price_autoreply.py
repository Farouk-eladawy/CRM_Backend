# -*- coding: utf-8 -*-
"""اختبار شامل لـ workflows/religious_raha_medium_price_autoreply.py
قبل الإعلان عن اكتمال العمل (قاعدة النظام 7: Test Before Saving)."""
import sys, io, json, importlib.util
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# تحميل السكربت كوحدة (بدون استيراد مسبق)
spec = importlib.util.spec_from_file_location(
    "religious_raha_medium_price_autoreply",
    "workflows/religious_raha_medium_price_autoreply.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

EXPECTED_REPLY = (
    "تمام 🌙 اللي يناسبك غالبًا هو برنامج التحسين ٥ نجوم (أسعار الموسم الماضي بدون الطيران، "
    "والرسمية لـ١٤٤٨ بتصدر خلال أيام):\n"
    "\n"
    "🏨 تحسين ٧ أيام — ٢٥٠ ألف بدلًا من ٢٧٩ ألف (خصم ٢٩ ألف)\n"
    "بتحج بمسار الاقتصادي طيران، وبعد المناسك بتقضي ٧ أيام في فندق ٥ نجوم قريب من الحرم. "
    "يعني راحة الـ٥ نجوم في الجزء اللي بتحتاجها فيه، من غير ما تدفع سعر برنامج ٥ نجوم كامل.\n"
    "\n"
    "💡 وهو أكبر برنامج من حيث أعداد التأشيرات المتوقعة السنة دي.\n"
    "\n"
    "يناسبك لو: عايز قرب من الحرم وراحة بعد التعب، أو بتحجز لوالدك أو والدتك، "
    "أو مش عايز تدفع ٤٠٠ ألف وأكتر.\n"
    "\n"
    "🎁 الخصم ده محفوظ ليك لو سجلت قبل صدور الضوابط، حتى لو السعر الرسمي زاد.\n"
    "\n"
    "نكلمك على الموبايل نشرحلك الفندق والمسافة والتفاصيل — إمتى مناسب؟ 👇"
)

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"{'✅' if cond else '❌'} {name}" + (f"  → {detail}" if detail else ""))

# ============ 1) اختبار الرد الثابت مطابق حرفياً للنص المطلوب ============
actual = mod.KEYWORDS[0]["reply"]
check("الرد الثابت مطابق 100% لنص المدير", actual == EXPECTED_REPLY,
      f"len actual={len(actual)} len expected={len(EXPECTED_REPLY)}")
check("الكلمة المفتاحية = راحة بسعر متوسط", mod.KEYWORDS[0]["keyword"] == "راحة بسعر متوسط",
      repr(mod.KEYWORDS[0]["keyword"]))

# ============ 2) اختبار المطابقة الدقيقة (Exact Match 100%) ============
m = mod._match_keyword("راحة بسعر متوسط")
check("Exact: 'راحة بسعر متوسط' يطابق", m is not None)
m2 = mod._match_keyword("راحة بسعر متوسط.")
check("Exact: 'راحة بسعر متوسط.' (بنقطة) يطابق (التطبيع يزيل الترقيم)", m2 is not None)
m3 = mod._match_keyword(" راحة بسعر متوسط ")
check("Exact: مسافات إضافية يطابق", m3 is not None)

# ============ 3) اختبار الرفض (ممنوع Contains / Startswith / Endswith) ============
reject_cases = [
    "عايز راحة بسعر متوسط",          # كلمة قبل → Contains يكسر
    "راحة بسعر متوسط دلوقتي",        # كلمة بعد → Contains يكسر
    "انا عايز راحة بسعر متوسط لو سمحت",  # جملة كاملة → لا تطابق
    "سعر معقول وراحة",               # كلمة أخرى قريبة → لا تطابق (تعارض محتمل)
    "الراحة والقرب من الحرم",        # كلمة أخرى → لا تطابق
    "راحة",                          # كلمة واحدة → لا تطابق
    "برنامج التحسين ٥ نجوم",         # لا علاقة → لا تطابق
    "",                              # فارغة
]
for case in reject_cases:
    r = mod._match_keyword(case)
    check(f"رفض (لا Exact): {case!r}", r is None)

# ============ 4) اختبار تشغيل run() بالكامل مع agent وهمي ============
class FakeAgent:
    def __init__(self):
        self.sent = []
    def send_facebook_message(self, recipient, text):
        self.sent.append(("facebook", recipient, text))
        return True, None
    def send_whatsapp_message(self, recipient, text, location=None, receiving_phone_id=None):
        self.sent.append(("whatsapp", recipient, text))
        return True, None

agent = FakeAgent()
res = mod.run(agent, {
    "chat_id": "TEST_RAHA_1",
    "message_body": "راحة بسعر متوسط",
    "source": "facebook",
    "sender_identifier": "FB_SENDER_TEST",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid_test_1",
})
check("run(): إرسال ناجح للقسم Religious", res.get("sent") is True, json.dumps(res, ensure_ascii=False)[:200])
check("run(): أُرسلت رسالة واحدة فقط", len(agent.sent) == 1, f"sent={len(agent.sent)}")
if agent.sent:
    check("run(): نص الرسالة = الرد الثابت", agent.sent[0][2] == EXPECTED_REPLY)

# ============ 5) اختبار منع التكرار (Dedup ذري) ============
res2 = mod.run(agent, {
    "chat_id": "TEST_RAHA_1",
    "message_body": "راحة بسعر متوسط",
    "source": "facebook",
    "sender_identifier": "FB_SENDER_TEST",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid_test_1_DUPLICATE",  # mid مختلف (Webhook duplicate)
})
check("run(): نفس الرسالة مرة أخرى → ممنوع (already_processed)",
      res2.get("skipped") == "already_processed", json.dumps(res2, ensure_ascii=False)[:150])
check("run(): لم تُرسل رسالة ثانية", len(agent.sent) == 1, f"sent={len(agent.sent)}")

# ============ 6) اختبار الفلترة الصارمة للأقسام (قاعدة 15) ============
for other_loc in ["Hurghada", "Sharm", "Sales", "Drivers"]:
    agent2 = FakeAgent()
    r = mod.run(agent2, {
        "chat_id": f"TEST_{other_loc}",
        "message_body": "راحة بسعر متوسط",
        "source": "facebook",
        "sender_identifier": "FB_SENDER_X",
        "location": other_loc,
        "receiving_phone_id": None,
        "incoming_external_message_id": f"mid_{other_loc}",
    })
    check(f"رفض قسم {other_loc} (لا يُرسل شيء)", r.get("skipped") == "not_religious" and len(agent2.sent) == 0)

# ============ 7) اختبار كلمة قريبة لا تطابق في قسم آخر أيضاً ============
agent3 = FakeAgent()
r = mod.run(agent3, {
    "chat_id": "TEST_HUR_2",
    "message_body": "عايز راحة بسعر متوسط",
    "source": "facebook",
    "sender_identifier": "FB_Y",
    "location": "Hurghada",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid_hur_2",
})
check("جملة قريبة في قسم آخر → skip نهائي", r.get("skipped") == "not_religious" and len(agent3.sent) == 0)

# ============ 8) WhatsApp channel ============
agent4 = FakeAgent()
r = mod.run(agent4, {
    "chat_id": "WA_TEST_1",
    "message_body": "راحة بسعر متوسط",
    "source": "whatsapp",
    "sender_identifier": "201000000000",
    "location": "Religious",
    "receiving_phone_id": "1101234567890",
    "incoming_external_message_id": "wamid_test_1",
})
check("WhatsApp: إرسال عبر القناة الصحيحة", r.get("sent") is True and agent4.sent and agent4.sent[0][0] == "whatsapp")

# ============ 9) رسالة ميديا غير نصية ============
agent5 = FakeAgent()
r = mod.run(agent5, {
    "chat_id": "MEDIA_TEST",
    "message_body": "[customer sent an audio message. Enjoy listening!]",
    "source": "facebook",
    "sender_identifier": "FB_M",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid_media",
})
check("رسالة صوتية → skip (non_text_media)", r.get("skipped") == "non_text_media" and len(agent5.sent) == 0)

# ============ 10) نقص بيانات ============
r = mod.run(agent, {"chat_id": "", "message_body": "راحة بسعر متوسط", "location": "Religious"})
check("نقص بيانات → skip (missing_data)", r.get("skipped") == "missing_data")

print("\n" + "=" * 60)
failed = [n for n, ok, _ in results if not ok]
print(f"النتيجة: {len(results) - len(failed)}/{len(results)} نجح" + (" — كل الاختبارات نجحت ✅" if not failed else f" — فشل: {failed} ❌"))
sys.exit(1 if failed else 0)
