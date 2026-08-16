# -*- coding: utf-8 -*-
"""
End-to-end simulation test for religious_price_changes_autoreply.py
(💰 إيه اللي اتغير في الأسعار؟ - Exact Match لحظي)
"""
import sys
import io
import importlib.util

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

spec = importlib.util.spec_from_file_location(
    "wf_price_changes", "workflows/religious_price_changes_autoreply.py"
)
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)

passed = 0
failed = 0

def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} {detail}")

KEYWORD = "💰 إيه اللي اتغير في الأسعار؟"
REPLY = wf.KEYWORDS[0]["reply"]

print("=" * 70)
print("1) اختبار المطابقة الدقيقة (Exact Match 100%)")
print("=" * 70)
m = wf._match_keyword(KEYWORD)
check("الكلمة المفتاحية كما كتبها المدير تُطابق", m is not None)
check("النص بدون إيموجي/استفهام يُطابق", wf._match_keyword("إيه اللي اتغير في الأسعار؟") is not None)
check("كلمات إضافية بعد النص -> لا تطابق", wf._match_keyword(f"{KEYWORD} دلوقتي") is None)
check("كلمات إضافية قبل النص -> لا تطابق", wf._match_keyword(f"تمام، {KEYWORD}") is None)
check("نص فارغ -> لا تطابق", wf._match_keyword("") is None)

print()
print("=" * 70)
print("2) اختبار سلامة نص الرد (مطابق حرفياً لطلب المدير)")
print("=" * 70)
checks_reply = {
    "السطر الأول (المقدمة 👇)": "هقولك بالظبط إيه اللي حصل من آخر مرة 👇",
    "🕋 الحج البري ١٩٠ أكتمل ✅": "🕋 الحج البري (١٩٠ ألف): اكتمل ✅ — قبل ما الضوابط تنزل أصلًا",
    "✈️ اقتصادي ٢٢٠ بدل ٢٤٥ + قطار الحرمين": "✈️ طيران اقتصادي: ٢٢٠ ألف بدلًا من ٢٤٥ (خصم الحجز المبكر شغال) + قطار الحرمين هدية",
    "⭐ تحسين ٢٥٠ بدل ٢٧٩ + ٧ أيام ساحة الحرم": "⭐ طيران تحسين: ٢٥٠ ألف بدلًا من ٢٧٩ (خصم الحجز المبكر شغال) + ٧ أيام على ساحة الحرم بعد المناسك",
    "👑 ٥ نجوم / مميز / كدانة": "👑 ٥ نجوم: ٤٩٠ — مميز: ٥٥٠ — كدانة: ٦٤٠",
    "توضيح السعر النهائي مع الضوابط": "(اللي بتحجزه دلوقتي هو مستوى البرنامج والخصم — والسعر النهائي بيتأكد مع صدور الضوابط، وهتعرفه قبل أي حد وقبل ما تلتزم بأي مبلغ)",
    "سؤال الختام 😊": "أنهي برنامج كان في بالك من ساعتها؟ قولي اسمه وأبعتلك تفاصيله كاملة 😊",
}
for name, snippet in checks_reply.items():
    check(f"الرد يحتوي: {name}", snippet in REPLY)

print()
print("=" * 70)
print("3) اختبار فلترة القسم (Religious فقط)")
print("=" * 70)
class FakeAgent:
    def __init__(self):
        self.sent = []
    def send_facebook_message(self, sender, text):
        self.sent.append(("fb", sender, text))
        return True, None
    def send_whatsapp_message(self, sender, text, location=None, receiving_phone_id=None):
        self.sent.append(("wa", sender, text))
        return True, None

agent = FakeAgent()
res = wf.run(agent, {"chat_id": "c1", "message_body": KEYWORD,
                     "sender_identifier": "fbuser1", "source": "Facebook", "location": "Hurghada"})
check("قسم Hurghada -> يُتخطى ولا يُرسل", res.get("skipped") == "not_religious" and len(agent.sent) == 0, str(res))

res = wf.run(agent, {"chat_id": "c1", "message_body": KEYWORD,
                     "sender_identifier": "fbuser1", "source": "Facebook", "location": "Sales"})
check("قسم Sales -> يُتخطى ولا يُرسل", res.get("skipped") == "not_religious" and len(agent.sent) == 0, str(res))

res = wf.run(agent, {"chat_id": "c2", "message_body": KEYWORD,
                     "sender_identifier": "", "source": "Facebook", "location": "Religious"})
check("بيانات ناقصة -> يُتخطى", res.get("skipped") == "missing_data" and len(agent.sent) == 0, str(res))

res = wf.run(agent, {"chat_id": "c3", "message_body": "[customer sent an audio message. mp3]",
                     "sender_identifier": "fbuser3", "source": "Facebook", "location": "Religious"})
check("ميديا غير نصية -> يُتخطى", res.get("skipped") == "non_text_media" and len(agent.sent) == 0, str(res))

res = wf.run(agent, {"chat_id": "c4", "message_body": "إيه اللي اتغير في الأسعار دلوقتي",
                     "sender_identifier": "fbuser4", "source": "Facebook", "location": "Religious"})
check("كلمة إضافية -> لا رد (no_keyword_match)", res.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(res))

print()
print("=" * 70)
print("4) اختبار الإرسال الفعلي (المطابقة الكاملة -> يُرسل الرد)")
print("=" * 70)
agent = FakeAgent()
res = wf.run(agent, {"chat_id": "c_match_1", "message_body": KEYWORD,
                     "sender_identifier": "fbuser5", "source": "Facebook", "location": "Religious"})
check("رسالة مطابقة -> تم الإرسال", res.get("sent") is True, str(res))
check("أُرسل عبر فيسبوك", len(agent.sent) == 1 and agent.sent[0][0] == "fb", str(agent.sent))
if agent.sent:
    sent_text = agent.sent[0][2]
    check("نص المرسل يحتوي: 'هقولك بالظبط إيه اللي حصل من آخر مرة 👇'",
          "هقولك بالظبط إيه اللي حصل من آخر مرة 👇" in sent_text)
    check("نص المرسل يحتوي: '🕋 الحج البري (١٩٠ ألف): اكتمل ✅'",
          "🕋 الحج البري (١٩٠ ألف): اكتمل ✅" in sent_text)
    check("نص المرسل يحتوي: 'كدانة: ٦٤٠'", "كدانة: ٦٤٠" in sent_text)
    check("نص المرسل يحتوي سؤال الختام", "قولي اسمه وأبعتلك تفاصيله كاملة 😊" in sent_text)

print()
print("=" * 70)
print("5) اختبار منع التكرار (Atomic Dedup)")
print("=" * 70)
res2 = wf.run(agent, {"chat_id": "c_match_1", "message_body": KEYWORD,
                      "sender_identifier": "fbuser5", "source": "Facebook", "location": "Religious"})
check("إعادة نفس الرسالة -> ممنوع التكرار", res2.get("skipped") == "already_processed", str(res2))
check("لم يُرسل أي رد ثانٍ", len(agent.sent) == 1, f"sent count: {len(agent.sent)}")

res3 = wf.run(agent, {"chat_id": "c_match_2", "message_body": "إيه اللي اتغير في الأسعار؟",
                      "sender_identifier": "fbuser6", "source": "Facebook", "location": "Religious"})
check("محادثة أخرى بنفس النص -> تُرسل مرة واحدة", res3.get("sent") is True and len(agent.sent) == 2, str(res3))

print()
print("=" * 70)
print("6) اختبار WhatsApp channel")
print("=" * 70)
agent = FakeAgent()
res = wf.run(agent, {"chat_id": "c_wa_1", "message_body": KEYWORD,
                     "sender_identifier": "201012345678", "source": "WhatsApp",
                     "location": "Religious", "receiving_phone_id": "phoneid123"})
check("رسالة WhatsApp -> تم الإرسال", res.get("sent") is True, str(res))
check("أُرسل عبر WhatsApp", len(agent.sent) == 1 and agent.sent[0][0] == "wa", str(agent.sent))
check("channel=WhatsApp", res.get("channel") == "WhatsApp", str(res))

print()
print("=" * 70)
print(f"RESULT: {passed} passed, {failed} failed")
print("=" * 70)
sys.exit(1 if failed else 0)
