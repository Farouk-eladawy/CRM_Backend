# -*- coding: utf-8 -*-
"""
اختبار شامل لسير عمل Religious Umrah 8-Day Follow-Up - ديني
=============================================================
يختبر:
  1) تصنيف رسائل العميل (رقم / حجز / إيقاف / موعد / رد عادي).
  2) منطق المراحل الزمنية (1-3h / 6-9h / 21-22h) + حد الـ 23 ساعة.
  3) إعادة ضبط العدّاد عند رد العميل (الرسائل الثلاث تعود متاحة).
  4) run() في وضع dry_run ضد قاعدة بيانات حقيقية (لا إرسال فعلي).
"""
import sys, os, io, json, tempfile, importlib.util
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

WORKFLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workflows", "religious_umrah_8day_followup.py")
spec = importlib.util.spec_from_file_location("w8", WORKFLOW_PATH)
w8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w8)

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
print("1) تصنيف رسائل العميل")
print("=" * 70)

# رقم موبايل (يبدأ بـ 01 ويتكون من 11 رقماً)
cat, phone = w8._classify_customer_message("01012345678")
check("رقم 11 خانة يبدأ بـ 01 → phone", cat == "phone" and phone == "01012345678", f"{cat}/{phone}")
cat, phone = w8._classify_customer_message("رقمي هو 010 1234 5678 ابعتلي")
check("رقم مع مسافات → phone", cat == "phone" and phone == "01012345678", f"{cat}/{phone}")
cat, phone = w8._classify_customer_message("٠١٠٩٨٧٦٥٤٣٢")
check("رقم بأرقام عربية (11 خانة) → phone", cat == "phone" and phone == "01098765432", f"{cat}/{phone}")
cat, phone = w8._classify_customer_message("+20 101 234 5678")
check("رقم ببادئة +20 → phone", cat == "phone" and phone == "01012345678", f"{cat}/{phone}")
cat, _ = w8._classify_customer_message("01288427370 في خدمة حضرتك")
check("رقم 012 → phone", cat == "phone", f"{cat}")
cat, _ = w8._classify_customer_message("عايز اعرف السعر")
check("بدون رقم → ليس phone", cat != "phone", f"{cat}")

# تأكيد الحجز / تحويل العربون
cat, _ = w8._classify_customer_message("أكدت الحجز من فضلك")
check("تأكيد الحجز → booking", cat == "booking", f"{cat}")
cat, _ = w8._classify_customer_message("حولت العربون دلوقتي")
check("تحويل العربون → booking", cat == "booking", f"{cat}")
cat, _ = w8._classify_customer_message("دفعت العربون")
check("دفع العربون → booking", cat == "booking", f"{cat}")
cat, _ = w8._classify_customer_message("حجزت مكانين")
check("حجزت → booking", cat == "booking", f"{cat}")

# رفض / طلب عدم التواصل
cat, _ = w8._classify_customer_message("مش مهتم شكرا")
check("مش مهتم → opt_out", cat == "opt_out", f"{cat}")
cat, _ = w8._classify_customer_message("متبعتليش تاني")
check("متبعتليش → opt_out", cat == "opt_out", f"{cat}")
cat, _ = w8._classify_customer_message("stop please")
check("stop → opt_out", cat == "opt_out", f"{cat}")

# كلمة «موعد»
cat, _ = w8._classify_customer_message("موعد")
check("«موعد» → dates", cat == "dates", f"{cat}")
cat, _ = w8._classify_customer_message("ابعتلي المواعيد")
check("المواعيد → dates", cat == "dates", f"{cat}")
cat, _ = w8._classify_customer_message("عايز اعرف مواعيد السفر")
check("مواعيد السفر → dates", cat == "dates", f"{cat}")
cat, _ = w8._classify_customer_message("تمام شكرا")
check("رد عادي → reply", cat == "reply", f"{cat}")

print("=" * 70)
print("2) منطق المراحل الزمنية")
print("=" * 70)
from datetime import datetime, timedelta

base = datetime(2026, 8, 3, 12, 0, 0)

def entry_with(**kw):
    e = w8._init_entry({"sender_identifier": "123"}, base, "msg", base.isoformat())
    for k, v in kw.items():
        e[k] = v
    return e

# 30 دقيقة → لا مرحلة
e = entry_with()
check("0.5 ساعة → لا مرحلة", w8._due_stage(e, base + timedelta(minutes=30), base) == 0)
# ساعتان → مرحلة 1
e = entry_with()
check("2 ساعات → مرحلة 1", w8._due_stage(e, base + timedelta(hours=2), base) == 1)
# 4 ساعات → لا مرحلة (فجوة)
e = entry_with()
check("4 ساعات → لا مرحلة (فجوة)", w8._due_stage(e, base + timedelta(hours=4), base) == 0)
# 7 ساعات → مرحلة 2
e = entry_with()
check("7 ساعات → مرحلة 2", w8._due_stage(e, base + timedelta(hours=7), base) == 2)
# 21.5 ساعة → مرحلة 3
e = entry_with()
check("21.5 ساعة → مرحلة 3", w8._due_stage(e, base + timedelta(hours=21.5), base) == 3)
# 23 ساعة → لا مرحلة (لا إرسال بعد 23)
e = entry_with()
check("23 ساعة → لا مرحلة (حد الإرسال)", w8._due_stage(e, base + timedelta(hours=23), base) == 0)
# المرحلة 1 أُرسلت → لا تكرار
e = entry_with(stage1_sent=True)
check("مرحلة 1 أُرسلت → لا تكرار", w8._due_stage(e, base + timedelta(hours=2), base) == 0)

print("=" * 70)
print("3) إعادة ضبط العدّاد عند رد العميل")
print("=" * 70)
# محادثة أُرسلت فيها المرحلة 1، ثم رد العميل → تصفير
e = entry_with(stage1_sent=True, stage2_sent=True, stage3_sent=True)
new_reply_ts = base + timedelta(hours=5)
w8._reset_counter(e, new_reply_ts, "تمام", new_reply_ts.isoformat())
check("بعد الرد: المراحل تُصفَّر", not e["stage1_sent"] and not e["stage2_sent"] and not e["stage3_sent"])
check("بعد الرد: المرساة = وقت الرد الجديد", e["last_customer_reply"] == new_reply_ts.isoformat())
check("بعد الرد بعد ساعة → مرحلة 1 متاحة", w8._due_stage(e, new_reply_ts + timedelta(hours=1), new_reply_ts) == 1)

print("=" * 70)
print("4) run() في وضع dry_run ضد قاعدة البيانات الحقيقية")
print("=" * 70)
class MockAgent:
    def __init__(self):
        self.sent = []
    def send_facebook_message(self, psid, text=None, **kw):
        self.sent.append(("fb", psid, text))
        return True, None
    def send_whatsapp_message(self, phone, text=None, **kw):
        self.sent.append(("wa", phone, text))
        return True, None

agent = MockAgent()
res = w8.run(agent, {"dry_run": True, "limit": 15})
print("  result:", json.dumps({k: v for k, v in res.items() if k != "errors"}, ensure_ascii=False, default=str))
check("run() يعيد ok", res.get("ok") is not None)
check("dry_run لا يرسل فعلياً (mock لا شيء)", len(agent.sent) == 0, f"sent={len(agent.sent)}")
check("processed_chats > 0", int(res.get("processed_chats") or 0) > 0)
check("عدد الأخطاء 0 في dry_run", len(res.get("errors") or []) == 0, str(res.get("errors"))[:300])

print("=" * 70)
print(f"النتيجة: {passed} نجح / {failed} فشل")
print("=" * 70)
sys.exit(1 if failed else 0)
