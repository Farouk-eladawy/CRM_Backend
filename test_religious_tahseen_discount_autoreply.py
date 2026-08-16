# -*- coding: utf-8 -*-
"""
اختبار شامل لـ Workflow (⭐ التحسين بالخصم) — بدون إرسال أي رسالة فعلية.
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
    "workflows/religious_tahseen_discount_autoreply.py",
)
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)

# تنظيف قواعد الحالة المؤقتة قبل الاختبار حتى تبدأ كل جولة اختبار من الصفر
# (لا يمس أي بيانات إنتاجية — هذه ملفات منع تكرار خاصة بهذا السكربت فقط)
for _f in ("religious_tahseen_discount_autoreply_dedup.db", "religious_tahseen_discount_autoreply_state.json"):
    _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), _f)
    if os.path.exists(_p):
        try:
            os.remove(_p)
        except Exception:
            pass

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
    ("⭐ التحسين بالخصم", "الكلمة بالضبط كما كتبها المدير (مع الإيموجي ⭐)"),
    ("التحسين بالخصم", "بدون الإيموجي (الإيموجي رمز غير حرفي يُحذف بالتطبيع)"),
    ("⭐  التحسين  بالخصم", "مسافات إضافية (تُوحَّد بالتطبيع)"),
]
for text, desc in match_cases:
    m = wf._match_keyword(text)
    check(f"'{text}' -> يجب أن يُطابق ({desc})", m is not None, f"got: {m}")

print()
print("=" * 70)
print("2) اختبار عدم المطابقة — ممنوع Contains/StartsWith/EndsWith — يجب ألا يُطابق")
print("=" * 70)
no_match_cases = [
    ("عايز التحسين بالخصم", "كلمة إضافية في البداية (Contains يمنع)"),
    ("التحسين بالخصم من فضلك", "كلمة إضافية في النهاية (EndsWith يمنع)"),
    ("ابعتلي التحسين بالخصم دلوقتي", "جملة أطول"),
    ("⭐ التحسين", "نص ناقص (أقصر من الكلمة)"),
    ("⭐ التحسين بالخصم يا فندم", "كلمة إضافية في النهاية"),
    ("⭐ تفاصيل التحسين", "كلمة Workflow آخر مختلف (Tahseen Improvement Details)"),
    ("عايز تفاصيل برنامج التحسين", "مختلفة (Tahseen Program Details)"),
    ("سعر برنامج التحسين كام؟", "مختلفة"),
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
m = wf._match_keyword("⭐ التحسين بالخصم")
reply = m["reply"]
required_parts = [
    "اختيار اللي فاهم يعني إيه راحة بعد المناسك ⭐",
    "٢٥٠ ألف بدلًا من ٢٧٩ (خصم الحجز المبكر)",
    "🕌 من ١٤ لـ ٢٠ ذو الحجة: ٧ أيام إقامة على/بجوار ساحة الحرم — بعد أصعب أيام الرحلة: مشاوير أقل، صلاة أسهل، وختام هادي",
    "⛺ مخيمات ألماني مُكيّفة + مشرف مرافق + متابعة يومية لأسرتك",
    "(غير شامل تذكرة الطيران)",
    "لو عاوز ترجع من الحج تقول ديه فعلا حجة العمر",
    "سجل اهتمامك بيه بصورة البطاقة",
    "ولا فيه سؤال واقف معاك من المرة اللي فاتت؟",
]
for part in required_parts:
    check(f"الرد يحتوي: '{part}'", part in reply, f"missing: {part}")
check("الرد هو نفس نص KEYWORDS", reply == wf.KEYWORDS[0]["reply"])

print()
print("=" * 70)
print("4) اختبار run() بوكيل وهمي (بدون إرسال فعلي) - فلترة القسم الديني")
print("=" * 70)

class FakeAgent:
    def __init__(self):
        self.sent = []
    def send_facebook_message(self, recipient, text):
        self.sent.append(("fb", recipient, text))
        return True, None
    def send_whatsapp_message(self, recipient, text, location=None, receiving_phone_id=None):
        self.sent.append(("wa", recipient, text))
        return True, None
    def cancel_whatsapp_ai_processing(self, chat_id=None, reason=None):
        return None

base_payload = {
    "chat_id": "wf_test_tahseen_discount_1001",
    "message_body": "⭐ التحسين بالخصم",
    "source": "Facebook",
    "sender_identifier": "100000000000001",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": None,
}

agent = FakeAgent()
res = wf.run(agent, dict(base_payload))
check("قسم Religious + كلمة مطابقة -> إرسال ناجح (sent=True)", bool(res.get("sent")), f"got: {res}")
check("تم إرسال رسالة واحدة فعلياً", len(agent.sent) == 1, f"got: {len(agent.sent)}")
check("المرسل إليه صحيح", agent.sent[0][1] == "100000000000001" if agent.sent else False)
check("القناة Facebook", agent.sent[0][0] == "fb" if agent.sent else False)
check("الرد الفعلي هو نفس الرد الحرفي", (agent.sent[0][2] if agent.sent else "") == wf.KEYWORDS[0]["reply"])

# إعادة نفس الرسالة -> منع التكرار (already_processed)
res2 = wf.run(FakeAgent(), dict(base_payload))
check("إعادة نفس الرسالة -> لا يُرسل مرة أخرى (already_processed)", res2.get("skipped") == "already_processed", f"got: {res2}")

# قسم آخر (Hurghada) -> لا يمس أي قسم آخر
p_hurghada = dict(base_payload)
p_hurghada["location"] = "Hurghada"
res3 = wf.run(FakeAgent(), dict(p_hurghada))
check("قسم Hurghada -> skipped (not_religious) بدون إرسال", res3.get("skipped") == "not_religious", f"got: {res3}")

# رسالة غير مطابقة -> يتركها للنظام الأساسي
p_nomatch = dict(base_payload)
p_nomatch["message_body"] = "عايز أعرف تفاصيل برنامج التحسين"
res4 = wf.run(FakeAgent(), dict(p_nomatch))
check("رسالة غير مطابقة -> skipped (no_keyword_match)", res4.get("skipped") == "no_keyword_match", f"got: {res4}")

# WhatsApp source -> قناة WhatsApp (chat_id مختلف لتجنب تعارض منع التكرار مع اختبار فيسبوك)
p_wa = dict(base_payload)
p_wa["chat_id"] = "wf_test_tahseen_discount_1002"
p_wa["source"] = "WhatsApp"
p_wa["sender_identifier"] = "201000000000"
agent_wa = FakeAgent()
res5 = wf.run(agent_wa, dict(p_wa))
check("مصدر WhatsApp -> إرسال عبر WhatsApp", bool(res5.get("sent")) and agent_wa.sent and agent_wa.sent[0][0] == "wa", f"got: {res5} / sent: {agent_wa.sent}")

print()
print("=" * 70)
print(f"النتيجة النهائية: {passed} نجحت / {failed} فشلت")
print("=" * 70)
sys.exit(1 if failed else 0)
