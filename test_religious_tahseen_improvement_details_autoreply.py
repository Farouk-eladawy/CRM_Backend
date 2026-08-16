# -*- coding: utf-8 -*-
"""
اختبار شامل لـ Workflow (⭐ تفاصيل التحسين) — بدون إرسال أي رسالة فعلية.
يختبر: المطابقة الدقيقة (Exact Match 100%)، نص الرد الحرفي، فلترة القسم
الديني، منع التكرار، واستقرار السكربت.
"""
import sys
import io
import json
import os
import importlib.util

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

spec = importlib.util.spec_from_file_location(
    "wf",
    "workflows/religious_tahseen_improvement_details_autoreply.py",
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

print("=" * 70)
print("1) اختبار المطابقة الدقيقة (Exact Match 100%) — يجب أن يُطابق")
print("=" * 70)
match_cases = [
    ("⭐ تفاصيل التحسين", "الكلمة بالضبط كما كتبها المدير (مع الإيموجي ⭐)"),
    ("تفاصيل التحسين", "بدون الإيموجي (الإيموجي رمز غير حرفي يُحذف بالتطبيع)"),
    ("⭐  تفاصيل  التحسين", "مسافات إضافية (تُوحَّد بالتطبيع)"),
]
for text, desc in match_cases:
    m = wf._match_keyword(text)
    check(f"'{text}' -> يجب أن يُطابق ({desc})", m is not None, f"got: {m}")

print()
print("=" * 70)
print("2) اختبار عدم المطابقة — ممنوع Contains/StartsWith/EndsWith — يجب ألا يُطابق")
print("=" * 70)
no_match_cases = [
    ("عايز أعرف تفاصيل التحسين", "كلمة إضافية في البداية (Contains يمنع)"),
    ("تفاصيل التحسين يا فندم", "كلمة إضافية في النهاية (EndsWith يمنع)"),
    ("ابعتلي تفاصيل التحسين من فضلك", "جملة أطول"),
    ("عايز أعرف تفاصيل البرنامج", "كلمة Workflow آخر مختلف"),
    ("⭐ تفاصيل الطيران الاقتصادي", "كلمة Workflow آخر مختلف"),
    ("إيه مميزات طيران تحسين؟", "كلمة Workflow آخر مختلف"),
    ("سعر طيران التحسين كام؟", "مختلفة"),
    ("", "فارغة"),
    ("[customer sent an audio message. mp3]", "ميديا غير نصية"),
]
for text, desc in no_match_cases:
    m = wf._match_keyword(text)
    check(f"'{text}' -> يجب ألا يُطابق ({desc})", m is None, f"got: {m}")

print()
print("=" * 70)
print("3) التحقق من نص الرد الحرفي (مطابقة لطلب المدير)")
print("=" * 70)
m = wf._match_keyword("⭐ تفاصيل التحسين")
reply = m["reply"]
required_parts = [
    "اختيار اللي بيدور على الراحة الحقيقية ⭐",
    "طيران تحسين — ٢٥٠ ألف بدلًا من ٢٧٩ (خصم الحجز المبكر)",
    "🕌 الميزة اللي مالهاش مثيل: من ١٤ لـ ٢٠ ذو الحجة",
    "٧ أيام إقامة على/بجوار ساحة الحرم بعد المناسك",
    "بعد أصعب أيام الرحلة، الحرم على بعد خطوات: مشاوير أقل وصلاة أسهل وختام هادي",
    "⛺ مخيمات ألماني مُكيّفة + مشرف مرافق + متابعة يومية لأسرتك",
    "(غير شامل تذكرة الطيران)",
    "لو عاوز تستمتع بالحج خاصة بعد فترة المناسك وترجع تقول ديه حجة العمر",
    "ده تحديدًا البرنامج اللي بننصح بيه لراحتك",
    "تحب تسجل اهتمامك بيه من دلوقتي بصورة البطاقة ولا عندك سؤال الأول؟",
]
for part in required_parts:
    check(f"يحتوي: {part[:60]}...", part in reply)
# الصيغة بدون إيموجي ترجع نفس الرد
m2 = wf._match_keyword("تفاصيل التحسين")
check("الصيغة بدون إيموجي ترجع نفس الرد", m2 is not None and m2["reply"] == reply)

print()
print("=" * 70)
print("4) اختبار فلترة القسم (Religious فقط)")
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

# قسم مختلف -> يجب أن يُتخطى بدون إرسال
agent = FakeAgent()
res = wf.run(agent, {"chat_id": "c1", "message_body": "⭐ تفاصيل التحسين",
                     "sender_identifier": "fbuser1", "source": "Facebook", "location": "Hurghada"})
check("قسم Hurghada -> يُتخطى ولا يُرسل", res.get("skipped") == "not_religious" and len(agent.sent) == 0, str(res))

res = wf.run(agent, {"chat_id": "c1", "message_body": "⭐ تفاصيل التحسين",
                     "sender_identifier": "fbuser1", "source": "Facebook", "location": "Sales"})
check("قسم Sales -> يُتخطى ولا يُرسل", res.get("skipped") == "not_religious" and len(agent.sent) == 0, str(res))

# بيانات ناقصة
res = wf.run(agent, {"chat_id": "c2", "message_body": "⭐ تفاصيل التحسين",
                     "sender_identifier": "", "source": "Facebook", "location": "Religious"})
check("بيانات ناقصة -> يُتخطى", res.get("skipped") == "missing_data" and len(agent.sent) == 0, str(res))

# ميديا غير نصية
res = wf.run(agent, {"chat_id": "c3", "message_body": "[customer sent an audio message. mp3]",
                     "sender_identifier": "fbuser3", "source": "Facebook", "location": "Religious"})
check("ميديا غير نصية -> يُتخطى", res.get("skipped") == "non_text_media" and len(agent.sent) == 0, str(res))

# رسالة غير مطابقة -> تُترك للنظام الأساسي
res = wf.run(agent, {"chat_id": "c4", "message_body": "عايز أعرف تفاصيل التحسين",
                     "sender_identifier": "fbuser4", "source": "Facebook", "location": "Religious"})
check("كلمة إضافية -> لا رد (no_keyword_match)", res.get("skipped") == "no_keyword_match" and len(agent.sent) == 0, str(res))

print()
print("=" * 70)
print("5) اختبار الإرسال الفعلي (المطابقة الكاملة -> يُرسل الرد)")
print("=" * 70)
# محادثة فريدة لضمان عدم تصادم منع التكرار
agent = FakeAgent()
res = wf.run(agent, {"chat_id": "c_match_1", "message_body": "⭐ تفاصيل التحسين",
                     "sender_identifier": "fbuser5", "source": "Facebook", "location": "Religious"})
check("رسالة مطابقة -> تم الإرسال", res.get("sent") is True, str(res))
check("أُرسل عبر فيسبوك", len(agent.sent) == 1 and agent.sent[0][0] == "fb", str(agent.sent))
if agent.sent:
    sent_text = agent.sent[0][2]
    check("نص المرسل يحتوي: 'طيران تحسين — ٢٥٠ ألف بدلًا من ٢٧٩'",
          "طيران تحسين — ٢٥٠ ألف بدلًا من ٢٧٩ (خصم الحجز المبكر)" in sent_text)
    check("نص المرسل يحتوي سؤال الختام",
          "تحب تسجل اهتمامك بيه من دلوقتي بصورة البطاقة ولا عندك سؤال الأول؟" in sent_text)

print()
print("=" * 70)
print("6) اختبار منع التكرار (Atomic Dedup)")
print("=" * 70)
# نفس الرسالة مرة ثانية لنفس المحادثة -> يجب ألا تُرسل
res2 = wf.run(agent, {"chat_id": "c_match_1", "message_body": "⭐ تفاصيل التحسين",
                      "sender_identifier": "fbuser5", "source": "Facebook", "location": "Religious"})
check("إعادة نفس الرسالة -> ممنوع التكرار", res2.get("skipped") == "already_processed", str(res2))
check("لم يُرسل أي رد ثانٍ", len(agent.sent) == 1, f"sent count: {len(agent.sent)}")

# محادثة مختلفة بنفس النص -> يجب أن تُرسل (لكل محادثة رد واحد)
res3 = wf.run(agent, {"chat_id": "c_match_2", "message_body": "تفاصيل التحسين",
                      "sender_identifier": "fbuser6", "source": "Facebook", "location": "Religious"})
check("محادثة أخرى بنفس النص -> تُرسل مرة واحدة", res3.get("sent") is True and len(agent.sent) == 2, str(res3))

print()
print("=" * 70)
print("7) اختبار WhatsApp channel")
print("=" * 70)
agent = FakeAgent()
res = wf.run(agent, {"chat_id": "c_wa_1", "message_body": "⭐ تفاصيل التحسين",
                     "sender_identifier": "201000000000", "source": "WhatsApp",
                     "location": "Religious", "receiving_phone_id": "12345"})
check("WhatsApp -> يُرسل عبر واتساب", res.get("sent") is True and len(agent.sent) == 1 and agent.sent[0][0] == "wa", str(agent.sent))

print()
print("=" * 70)
print("النتيجة النهائية")
print("=" * 70)
print(f"Passed: {passed} | Failed: {failed}")
sys.exit(1 if failed else 0)
