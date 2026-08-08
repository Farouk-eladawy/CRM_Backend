# -*- coding: utf-8 -*-
"""
اختبار شامل لسير عمل Religious Hajj Early-Booking Follow-Up - ديني
=====================================================================
يختبر:
  1) تصنيف رسائل العميل (رقم واتساب / حجز / جدية حجز / إيقاف / رد عادي).
  2) جدول القرارات الزمنية (1-6h / 6-21h / 21-24h / 24h+ / أقل من 1 ساعة)
     + قاعدة «لا تُعوَّض الرسالة 1» + الحد الأقصى 3 متابعات.
  3) إعادة ضبط المرساة عند رد العميل مع بقاء sent_count (الحد الأقصى 3).
  4) نصوص الرسائل مطابقة لنص برومبت المدير حرفياً.
  5) run() في وضع dry_run ضد قاعدة بيانات حقيقية (لا إرسال فعلي).
"""
import sys, os, io, json, tempfile, importlib.util
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

WORKFLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workflows", "religious_hajj_earlybooking_followup.py")
spec = importlib.util.spec_from_file_location("wh", WORKFLOW_PATH)
wh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wh)

passed = 0
failed = 0

def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [OK] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} {detail}")

print("=" * 70)
print("0) نصوص الرسائل مطابقة لنص برومبت المدير (لا تعديل)")
print("=" * 70)
check("المتابعة 1 تبدأ بـ «حضرتك لسه معانا؟»",
      wh.MSG_STAGE1.startswith("حضرتك لسه معانا؟ 🕋"))
check("المتابعة 1 لا تحتوي سعراً",
      "جنيه" not in wh.MSG_STAGE1 and "٢٢٠" not in wh.MSG_STAGE1 and "ألف" not in wh.MSG_STAGE1)
check("المتابعة 2 تبدأ بـ «عشان محدش يفوته الخصم»",
      wh.MSG_STAGE2.startswith("عشان محدش يفوته الخصم 🧡"))
check("المتابعة 2 النص المحدث: «حج البري السنادي اكتمل بالفعل من كتر الإقبال»",
      "السنادي اكتمل بالفعل من كتر الإقبال" in wh.MSG_STAGE2)
check("المتابعة 2 تذكر البرامج المتاحة «حج الطيران تحسين»",
      "حج الطيران تحسين" in wh.MSG_STAGE2)
check("المتابعة 2 لا تذكر النص القديم «الموسم اللي فات»",
      "الموسم اللي فات" not in wh.MSG_STAGE2)
check("المتابعة 3 تبدأ بـ «آخر رسالة مني النهارده»",
      wh.MSG_STAGE3.startswith("آخر رسالة مني النهارده وعدًا 🙏"))
check("المتابعة 3 النص المحدث: «وهتواصل بكل التفاصيل والعروض»",
      "وهتواصل بكل التفاصيل والعروض" in wh.MSG_STAGE3)
check("المتابعة 3 لا تحتوي الرقم المباشر (حُذف بطلب المدير)",
      "٠١٢٧٩٤٧١٦١٩" not in wh.MSG_STAGE3 and "أو كلمنا مباشرة" not in wh.MSG_STAGE3)
check("رسالة تأكيد الرقم مخصصة", wh.MSG_PHONE_CONFIRM.startswith("تمام يا فندم، وصلني رقم حضرتك 🧡"))
check("رسالة الختام المهذب", wh.MSG_POLITE_CLOSE.startswith("تحت أمر حضرتك في أي وقت 🧡"))

print("=" * 70)
print("1) تصنيف رسائل العميل")
print("=" * 70)

# رقم واتساب / موبايل (يبدأ بـ 01 ويتكون من 11 رقماً)
cat, phone = wh._classify_customer_message("01012345678")
check("رقم 11 خانة يبدأ بـ 01 → phone", cat == "phone" and phone == "01012345678", f"{cat}/{phone}")
cat, phone = wh._classify_customer_message("رقمي هو 010 1234 5678 ابعتلي")
check("رقم مع مسافات → phone", cat == "phone" and phone == "01012345678", f"{cat}/{phone}")
cat, phone = wh._classify_customer_message("٠١٠٩٨٧٦٥٤٣٢")
check("رقم بأرقام عربية (11 خانة) → phone", cat == "phone" and phone == "01098765432", f"{cat}/{phone}")
cat, phone = wh._classify_customer_message("+20 101 234 5678")
check("رقم ببادئة +20 → phone", cat == "phone" and phone == "01012345678", f"{cat}/{phone}")
cat, _ = wh._classify_customer_message("عايز اعرف السعر")
check("بدون رقم → ليس phone", cat != "phone", f"{cat}")

# تأكيد الحجز / دفع جدية الحجز
cat, _ = wh._classify_customer_message("أكدت الحجز من فضلك")
check("تأكيد الحجز → booking", cat == "booking", f"{cat}")
cat, _ = wh._classify_customer_message("دفعت جدية الحجز دلوقتي")
check("دفع جدية الحجز → booking", cat == "booking", f"{cat}")
cat, _ = wh._classify_customer_message("حولت العربون")
check("تحويل العربون → booking", cat == "booking", f"{cat}")
cat, _ = wh._classify_customer_message("حجزت مكانين")
check("حجزت → booking", cat == "booking", f"{cat}")

# رفض / عدم اهتمام واضح (أمثلة المدير حرفياً)
cat, _ = wh._classify_customer_message("مش مهتم شكرا")
check("«مش مهتم» → opt_out", cat == "opt_out", f"{cat}")
cat, _ = wh._classify_customer_message("شكرًا مش عايز")
check("«شكرًا مش عايز» → opt_out", cat == "opt_out", f"{cat}")
cat, _ = wh._classify_customer_message("بطلوا رسايل")
check("«بطلوا رسايل» → opt_out", cat == "opt_out", f"{cat}")
cat, _ = wh._classify_customer_message("متبعتليش تاني")
check("متبعتليش → opt_out", cat == "opt_out", f"{cat}")
cat, _ = wh._classify_customer_message("stop please")
check("stop → opt_out", cat == "opt_out", f"{cat}")

# رد عادي
cat, _ = wh._classify_customer_message("تمام شكرا")
check("رد عادي → reply", cat == "reply", f"{cat}")
cat, _ = wh._classify_customer_message("عندي سؤال عن الفنادق")
check("سؤال عن الفنادق → reply (يرد عليه المساعد الأساسي)", cat == "reply", f"{cat}")

print("=" * 70)
print("2) جدول القرارات الزمنية")
print("=" * 70)
from datetime import datetime, timedelta

base = datetime(2026, 8, 3, 12, 0, 0)

def entry_with(count=0, stopped=False, reason=""):
    e = wh._init_entry({"sender_identifier": "123"}, base, "msg", base.isoformat())
    e["sent_count"] = count
    e["stopped"] = stopped
    e["stop_reason"] = reason
    return e

# أقل من 1 ساعة → لا ترسل شيئاً (أي عدد)
e = entry_with(0)
check("0.5 ساعة + 0 متابعات → 0 (انتظر)", wh._due_stage(e, base + timedelta(minutes=30), base) == 0)
e = entry_with(2)
check("0.5 ساعة + 2 متابعات → 0 (انتظر)", wh._due_stage(e, base + timedelta(minutes=30), base) == 0)

# 1 إلى أقل من 6 ساعات + 0 → المتابعة 1
e = entry_with(0)
check("2 ساعات + 0 → المتابعة 1", wh._due_stage(e, base + timedelta(hours=2), base) == 1)
e = entry_with(1)
check("2 ساعات + 1 متابعة → 0 (الجدول: 0 فقط)", wh._due_stage(e, base + timedelta(hours=2), base) == 0)
e = entry_with(2)
check("5 ساعات + 2 متابعات → 0", wh._due_stage(e, base + timedelta(hours=5), base) == 0)

# 6 إلى أقل من 21 ساعة + 0 أو 1 → المتابعة 2 (لا تُعوَّض الرسالة 1)
e = entry_with(0)
check("7 ساعات + 0 → المتابعة 2 مباشرة (لا تُعوَّض 1)", wh._due_stage(e, base + timedelta(hours=7), base) == 2)
e = entry_with(1)
check("7 ساعات + 1 → المتابعة 2", wh._due_stage(e, base + timedelta(hours=7), base) == 2)
e = entry_with(2)
check("20 ساعة + 2 → 0 (الجدول: 0 أو 1 فقط)", wh._due_stage(e, base + timedelta(hours=20), base) == 0)

# 21 إلى أقل من 24 ساعة + 0/1/2 → المتابعة 3 (رسالة الإغلاق)
e = entry_with(0)
check("22 ساعة + 0 → المتابعة 3 مباشرة", wh._due_stage(e, base + timedelta(hours=22), base) == 3)
e = entry_with(1)
check("22 ساعة + 1 → المتابعة 3", wh._due_stage(e, base + timedelta(hours=22), base) == 3)
e = entry_with(2)
check("22 ساعة + 2 → المتابعة 3", wh._due_stage(e, base + timedelta(hours=22), base) == 3)
e = entry_with(3)
check("22 ساعة + 3 → 0 (الحد الأقصى)", wh._due_stage(e, base + timedelta(hours=22), base) == 0)

# 24 ساعة أو أكثر → توقف نهائي (-1)
e = entry_with(0)
check("24.5 ساعة → -1 (نافذة مغلقة)", wh._due_stage(e, base + timedelta(hours=24.5), base) == -1)
e = entry_with(1)
check("30 ساعة + 1 → -1", wh._due_stage(e, base + timedelta(hours=30), base) == -1)

# قاعدة صارمة: دورة واحدة = متابعة واحدة فقط (قيمة واحدة دائماً)
e = entry_with(0)
stage = wh._due_stage(e, base + timedelta(hours=22), base)
check("دورة واحدة = متابعة واحدة فقط", isinstance(stage, int) and stage in (-1, 0, 1, 2, 3))

print("=" * 70)
print("3) إعادة ضبط المرساة عند رد العميل (sent_count لا ينقص)")
print("=" * 70)
e = entry_with(count=2)
new_reply_ts = base + timedelta(hours=8)
wh._reset_anchor(e, new_reply_ts, "تمام", new_reply_ts.isoformat())
check("المرساة = وقت رد العميل الجديد", e["last_customer_reply"] == new_reply_ts.isoformat())
check("sent_count يبقى 2 (تُحتسب ضمن الحد الأقصى)", e["sent_count"] == 2, f"count={e['sent_count']}")
check("بعد الرد بـ 2 ساعات (count=2) → 0 (الجدول: 1-6h + 0 فقط)",
      wh._due_stage(e, new_reply_ts + timedelta(hours=2), new_reply_ts) == 0)
check("بعد الرد بـ 7 ساعات (count=2) → 0 (الجدول: 6-21h + 0/1 فقط)",
      wh._due_stage(e, new_reply_ts + timedelta(hours=7), new_reply_ts) == 0)
check("بعد الرد بـ 22 ساعة (count=2) → المتابعة 3 (آخر متابعة متاحة)",
      wh._due_stage(e, new_reply_ts + timedelta(hours=22), new_reply_ts) == 3)

# حد أقصى 3: بعد إرسال 3 متابعات لا يوجد أي مرحلة مهما مر الوقت
e = entry_with(count=3)
check("count=3 + أي وقت → 0 إطلاقاً", wh._due_stage(e, base + timedelta(hours=10), base) == 0)

# إعادة فتح السلسلة بعد إغلاق النافذة (window_closed) عند رسالة عميل جديدة
e = entry_with(count=2, stopped=True, reason="window_closed")
wh._reset_anchor(e, new_reply_ts, "انا موجود", new_reply_ts.isoformat())
check("رسالة عميل جديدة تفتح النافذة (إلغاء window_closed)",
      not e.get("stopped") and e.get("stop_reason") == "")
check("العدّاد الكلي يبقى 2 بعد إعادة الفتح", e["sent_count"] == 2)

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
res = wh.run(agent, {"dry_run": True, "limit": 15})
print("  result:", json.dumps({k: v for k, v in res.items() if k != "errors"}, ensure_ascii=False, default=str))
check("run() يعيد dict كامل", isinstance(res, dict) and "ok" in res)
check("dry_run لا يرسل فعلياً (mock لا شيء)", len(agent.sent) == 0, f"sent={len(agent.sent)}")
check("processed_chats > 0", int(res.get("processed_chats") or 0) > 0)
check("لا أخطاء في dry_run", len(res.get("errors") or []) == 0, str(res.get("errors"))[:300])

print("=" * 70)
print(f"النتيجة: {passed} نجح / {failed} فشل")
print("=" * 70)
sys.exit(1 if failed else 0)
