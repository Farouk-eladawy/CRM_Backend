# -*- coding: utf-8 -*-
"""
اختبار شامل لـ Workflow (إيه مميزات طيران تحسين؟) — بدون إرسال أي رسالة فعلية.
يختبر: المطابقة (Contains + الصيغ)، نص الرد الحرفي، فلترة القسم الديني،
منع التكرار، واستقرار السكربت.
"""
import sys
import io
import json
import importlib.util

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

spec = importlib.util.spec_from_file_location(
    "wf",
    "workflows/religious_tahseen_travel_advantages_autoreply.py",
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
print("1) اختبار المطابقة (Contains Match) — الهدف: يجب أن يُطابق")
print("=" * 70)
match_cases = [
    ("إيه مميزات طيران تحسين؟", "السؤال بعلامة استفهام (بالضبط كما كتبه المدير)"),
    ("إيه مميزات طيران تحسين", "بدون علامة الاستفهام"),
    ("عايز أعرف إيه مميزات طيران تحسين", "داخل جملة أطول"),
    ("ايه مميزات طيران تحسين", "بدون همزة (صيغة إضافية)"),
    ("مميزات طيران تحسين", "بدون كلمة السؤال (صيغة إضافية)"),
    ("إيه مميزات طيران تحسين؟ شكرًا", "مع كلمات إضافية بعدها"),
    ("إيه مميزات طيران تحسين ✈️🕋", "مع إيموجي"),
]
for text, desc in match_cases:
    m = wf._match_keyword(text)
    check(f"'{text}' -> يجب أن يُطابق ({desc})", m is not None, f"got: {m}")

print()
print("=" * 70)
print("2) اختبار عدم المطابقة — الهدف: يجب ألا يُطابق")
print("=" * 70)
no_match_cases = [
    ("عايز أعرف تفاصيل البرنامج", "كلمة Workflow آخر مختلف"),
    ("إيه مميزات برنامج العمرة", "مختلفة"),
    ("سعر برنامج تحسين كام؟", "لا تحتوي الجملة المفتاحية"),
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
m = wf._match_keyword("إيه مميزات طيران تحسين؟")
reply = m["reply"]
required_parts = [
    "سؤال ممتاز يا فندم 🕋",
    "٧ أيام إقامة ٥ نجوم على ساحة الحرم مباشرة بعد المناسك",
    "🚆 من المدينة لمكة بقطار الحرمين السريع بدل ساعات الطريق",
    "⛺ مخيمات ألماني مكيفة ومجهزة",
    "👥 مشرفين من الشركة معاك من مطار القاهرة لحد الرجوع بالسلامة",
    "عشان كده البرنامج ده كان أكتر برنامج ضيوف الرحمن شكرونا عليه الموسم اللي فات 🧡",
    "💰 السعر: ٢٥٠ ألف بدلًا من ٢٧٩ ألف (غير شامل الطيران)",
    "وزارة الداخلية فتحت تقديم حج القرعة من الأربعاء ١٢ أغسطس",
    "مسموح بالتقديم على جهة واحدة بس والاختيار نهائي",
    "إحنا بنسجلك مبدئيًا (بصورة البطاقة ومن غير مصاريف)",
    "حضرتك بتفكر في البرنامج لنفسك ولا لحد من الأسرة؟",
]
for part in required_parts:
    check(f"يحتوي: {part[:60]}...", part in reply)
# التحقق من أن كل الصيغ ترجع نفس الرد
m2 = wf._match_keyword("ايه مميزات طيران تحسين")
check("الصيغة بدون همزة ترجع نفس الرد", m2 is not None and m2["reply"] == reply)
m3 = wf._match_keyword("مميزات طيران تحسين")
check("الصيغة بدون كلمة السؤال ترجع نفس الرد", m3 is not None and m3["reply"] == reply)

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
res = wf.run(agent, {"chat_id": "c1", "message_body": "إيه مميزات طيران تحسين؟",
                     "sender_identifier": "fbuser1", "source": "Facebook", "location": "Hurghada"})
check("قسم Hurghada -> يُتخطى ولا يُرسل", res.get("skipped") == "not_religious" and len(agent.sent) == 0, str(res))

# بيانات ناقصة
res = wf.run(agent, {"chat_id": "c2", "message_body": "إيه مميزات طيران تحسين؟",
                     "sender_identifier": "", "source": "Facebook", "location": "Religious"})
check("بيانات ناقصة -> يُتخطى", res.get("skipped") == "missing_data" and len(agent.sent) == 0, str(res))

# ميديا غير نصية
res = wf.run(agent, {"chat_id": "c3", "message_body": "[customer sent an audio message. mp3]",
                     "sender_identifier": "fbuser3", "source": "Facebook", "location": "Religious"})
check("ميديا غير نصية -> يُتخطى", res.get("skipped") == "non_text_media" and len(agent.sent) == 0, str(res))

print()
print("=" * 70)
print("5) اختبار الإرسال الفعلي عبر Fake Agent (قسم Religious)")
print("=" * 70)
res = wf.run(agent, {"chat_id": "c100", "message_body": "إيه مميزات طيران تحسين؟",
                     "sender_identifier": "fbuser100", "source": "Facebook", "location": "Religious"})
check("يُرسل رد على فيسبوك", res.get("sent") is True and len(agent.sent) == 1, str(res))
check("القناة فيسبوك", agent.sent[0][0] == "fb", str(agent.sent))
check("الرد يبدأ بالترحيب", agent.sent[0][2].startswith("سؤال ممتاز يا فندم 🕋"))

# منع التكرار: نفس الرسالة مرة أخرى -> يجب ألا يُرسل مجدداً
res2 = wf.run(agent, {"chat_id": "c100", "message_body": "إيه مميزات طيران تحسين؟",
                      "sender_identifier": "fbuser100", "source": "Facebook", "location": "Religious"})
check("منع التكرار (نفس الرسالة) -> already_processed ولا يُرسل مجدداً",
      res2.get("skipped") == "already_processed" and len(agent.sent) == 1, str(res2))

# رسالة مختلفة -> يُسمح بالإرسال
res3 = wf.run(agent, {"chat_id": "c101", "message_body": "ايه مميزات طيران تحسين",
                      "sender_identifier": "fbuser101", "source": "Facebook", "location": "Religious"})
check("رسالة جديدة بصيغة أخرى -> يُرسل", res3.get("sent") is True and len(agent.sent) == 2, str(res3))

print()
print("=" * 70)
print(f"النتيجة النهائية: {passed} نجحت | {failed} فشلت")
print("=" * 70)
sys.exit(1 if failed else 0)
