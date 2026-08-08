# -*- coding: utf-8 -*-
"""
Test: religious_umrah_phrases_autoreply.py (قبل التسجيل الرسمي)
=================================================================
يختبر:
  1) منطق المطابقة الدقيقة (Exact Match) للجمل الثلاث مع حالات إيجابية وسلبية.
  2) التدفق الكامل لـ run() عبر Agent وهمي (محاكاة الإرسال والتسجيل).
  3) فلترة Religious الصارمة (لا يلمس أي قسم آخر).
  4) منع التكرار (الحجز الذري) — نفس الرسالة مرتين = إرسال واحد فقط.
"""
import sys
import io
import json
import tempfile
import os
import logging

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
logging.basicConfig(level=logging.CRITICAL)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "workflows"))
import religious_umrah_phrases_autoreply as wf

# =============================================================================
# 1) اختبار منطق المطابقة الدقيقة
# =============================================================================
print("=" * 60)
print("1) EXACT MATCH LOGIC")
print("=" * 60)

cases = [
    # (نص الرسالة, هل يجب أن تُطابق؟, وصف)
    ("٨ أيام — اقتصادي", True, "الجملة الأولى بالظبط"),
    ("١٥ يوم — اقتصادي", True, "الجملة الثانية بالظبط"),
    ("١٠ أيام — ٤ نجوم ⭐", True, "الجملة الثالثة بالظبط (بالنجمة)"),
    ("١٠ أيام — ٤ نجوم", True, "الثالثة بدون النجمة (النجمة رمز غير حرفي يُحذف)"),
    ("٨ أيام—اقتصادي", True, "الشرطة ملتصقة بدون مسافات (الشرطة رمز غير حرفي)"),
    ("٨ أيام اقتصادي", True, "بدون شرطة نهائياً"),
    (" ٨ أيام — اقتصادي ", True, "مسافات زائدة حول النص (تُقصّ)"),
    # --- حالات سلبية: ممنوع Contains / تغيير حرفي ---
    ("٨ أيام — اقتصادي ممتاز", False, "كلمة إضافية بعد النص (Contains ممنوع)"),
    ("عايز ٨ أيام — اقتصادي", False, "كلمات إضافية قبل النص (Contains ممنوع)"),
    ("٨ ايام — اقتصادي", False, "همزة مختلفة: ايام بدل أيام (لا توحيد همزات)"),
    ("٨ أيام — اقتصادي؟", True, "علامة استفهام إضافية (الترقيم رمز غير حرفي يُحذف بنفس منطق المحرك الرسمي)"),
    ("١٥ يوم اقتصادي ممتاز", False, "الثانية مع كلمة إضافية"),
    ("مرحبا", False, "رسالة عامة"),
]

all_ok = True
for text, expected, desc in cases:
    m = wf._match_keyword(text)
    got = m is not None
    status = "PASS" if got == expected else "FAIL"
    if got != expected:
        all_ok = False
    print(f"[{status}] {desc!r}")
    print(f"    msg={text!r} -> matched={got} (expected={expected})")

# =============================================================================
# 2) فحص الرد الثابت (مطابق حرفياً لطلب المدير)
# =============================================================================
print()
print("=" * 60)
print("2) FIXED REPLY TEXT")
print("=" * 60)
expected_reply = (
    "تمام ✅ متاح ان شاء الله— والغرفة نوعها إيه (رباعي ولا ثلاثي ولا ثنائي )\n"
    "وعددكم كام؟"
)
for entry in wf.KEYWORDS:
    same = entry["reply"] == expected_reply
    if not same:
        all_ok = False
    print(f"[{'PASS' if same else 'FAIL'}] keyword={entry['keyword']!r}")
print("Expected reply repr:")
print(repr(expected_reply))
print("Actual reply repr (keyword 1):")
print(repr(wf.KEYWORDS[0]["reply"]))

# =============================================================================
# 3) التدفق الكامل لـ run() مع Agent وهمي
# =============================================================================
print()
print("=" * 60)
print("3) FULL run() FLOW (fake agent)")
print("=" * 60)

sent_messages = []
logged_messages = []
cancelled = []

class FakeAgent:
    def send_facebook_message(self, sender_id, text):
        sent_messages.append(("facebook", sender_id, text))
        return True, None
    def send_whatsapp_message(self, sender_id, text, location=None, receiving_phone_id=None):
        sent_messages.append(("whatsapp", sender_id, text))
        return True, None
    def cancel_whatsapp_ai_processing(self, chat_id=None, reason=None):
        cancelled.append((chat_id, reason))
        return None

agent = FakeAgent()

# 3.1 رسالة مطابقة من قسم Religious (Facebook)
res = wf.run(agent, {
    "chat_id": "test-chat-101",
    "message_body": "١٥ يوم — اقتصادي",
    "sender_identifier": "psid_101",
    "source": "Facebook",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid_101",
})
print("Result 3.1:", {k: v for k, v in res.items() if k != "reply_preview"})
print("reply_preview:", res.get("reply_preview"))

# 3.2 نفس الرسالة مرة ثانية (Webhook duplicate) → يجب ألا يُرسل مجدداً
res2 = wf.run(agent, {
    "chat_id": "test-chat-101",
    "message_body": "١٥ يوم — اقتصادي",
    "sender_identifier": "psid_101",
    "source": "Facebook",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid_101_DUP",
})
print("Result 3.2 (dup):", res2)

# 3.3 رسالة مطابقة من قسم آخر (Hurghada) → skip نهائي (لا يمس أقساماً أخرى)
res3 = wf.run(agent, {
    "chat_id": "test-chat-999",
    "message_body": "٨ أيام — اقتصادي",
    "sender_identifier": "psid_999",
    "source": "Facebook",
    "location": "Hurghada",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid_999",
})
print("Result 3.3 (Hurghada):", res3)

# 3.4 رسالة غير مطابقة من Religious → skip بدون إرسال
res4 = wf.run(agent, {
    "chat_id": "test-chat-202",
    "message_body": "١٥ يوم — اقتصادي ومسافر",
    "sender_identifier": "psid_202",
    "source": "Facebook",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid_202",
})
print("Result 3.4 (no match):", res4)

# 3.5 رسالة مطابقة عبر WhatsApp
res5 = wf.run(agent, {
    "chat_id": "test-chat-303",
    "message_body": "١٠ أيام — ٤ نجوم ⭐",
    "sender_identifier": "201012345678",
    "source": "WhatsApp",
    "location": "Religious",
    "receiving_phone_id": "phone-id-1",
    "incoming_external_message_id": "",
})
print("Result 3.5 (WhatsApp):", {k: v for k, v in res5.items() if k != "reply_preview"})

print()
print("sent_messages count:", len(sent_messages))
for s in sent_messages:
    print("  ->", s[0], s[1], repr(s[2]))
print("cancelled AI processing:", len(cancelled))

# =============================================================================
# 4) التلخيص
# =============================================================================
print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
checks = [
    (all_ok, "جميع حالات المطابقة صحيحة (موجب/سالب) والرد حرفي"),
    (len(sent_messages) == 2, f"أُرسل ردّان فقط (فيسبوك + واتساب)، وليس {len(sent_messages)}"),
    (res.get("sent") is True and res2.get("skipped") == "already_processed", "منع التكرار يعمل (الرسالة المكررة لم تُرسل)"),
    (res3.get("skipped") == "not_religious", "فلترة Religious الصارمة تعمل (Hurghada لم تُمس)"),
    (res4.get("skipped") == "no_keyword_match", "رسالة غير مطابقة لا تسبب رداً"),
    (len(cancelled) >= 1, "تم إلغاء مؤقت AI processing بعد الإرسال"),
]
final_ok = True
for ok, desc in checks:
    if not ok:
        final_ok = False
    print(f"[{'PASS' if ok else 'FAIL'}] {desc}")
print()
print("FINAL:", "ALL PASS ✅" if final_ok else "FAILURES ❌")
