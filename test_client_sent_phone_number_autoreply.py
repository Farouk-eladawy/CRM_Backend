# -*- coding: utf-8 -*-
"""
اختبار شامل لسكربت client_sent_phone_number_autoreply.py
(قاعدة النظام 7: اختبار قبل الحفظ النهائي).
"""
import sys
import io
import os
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# إجبار get_data_path على مجلد مؤقت حتى لا نلمس ملفات الحالة الحقيقية أثناء الاختبار
import fts_paths
_tmp = tempfile.mkdtemp(prefix="fts_test_phone_")
fts_paths.DATA_DIR = _tmp
fts_paths.SCRIPT_DIR = _tmp

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "workflows"))

import importlib.util
spec = importlib.util.spec_from_file_location(
    "client_sent_phone_number_autoreply",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "workflows", "client_sent_phone_number_autoreply.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class MockAgent:
    """Agent وهمي يسجل الرسائل المرسلة بدلاً من الإرسال الحقيقي."""
    def __init__(self):
        self.sent = []
        self.cancelled = []
        self.sends = 0

    def send_whatsapp_message(self, to, text=None, location=None, receiving_phone_id=None):
        self.sends += 1
        self.sent.append(("whatsapp", to, text))
        return True, None

    def send_facebook_message(self, to, text=None):
        self.sends += 1
        self.sent.append(("facebook", to, text))
        return True, None

    def cancel_whatsapp_ai_processing(self, **kwargs):
        self.cancelled.append(kwargs)


CASES = []

def case(name, payload, expect_sent, expect_skip=None, expect_channel=None, expect_reply=False):
    CASES.append((name, payload, expect_sent, expect_skip, expect_channel, expect_reply))


# 1) رقم محلي مباشر
case("رقم محلي 01012345678",
     {"chat_id": "c1", "message_body": "01012345678", "sender_identifier": "12345",
      "source": "Facebook", "location": "Religious", "receiving_phone_id": "999", "incoming_external_message_id": "m1"},
     True, None, "Facebook", True)

# 2) رقم محلي داخل جملة
case("رقم داخل جملة",
     {"chat_id": "c2", "message_body": "رقمي هو 01123456789 ياريت تكلمني", "sender_identifier": "12345",
      "source": "Facebook", "location": "Religious"},
     True, None, "Facebook", True)

# 3) أرقام هندية (٠-٩)
case("أرقام هندية",
     {"chat_id": "c3", "message_body": "الرقم ٠١٢٣٤٥٦٧٨٩٠", "sender_identifier": "12345",
      "source": "Facebook", "location": "Religious"},
     True, None, "Facebook", True)

# 4) صيغة دولية +20
case("صيغة دولية +20",
     {"chat_id": "c4", "message_body": "+201012345678", "sender_identifier": "12345",
      "source": "Facebook", "location": "Religious"},
     True, None, "Facebook", True)

# 5) صيغة دولية 0020 مع 0 قبل 1
case("صيغة 0020 مع 0",
     {"chat_id": "c5", "message_body": "002001012345678", "sender_identifier": "12345",
      "source": "Facebook", "location": "Religious"},
     True, None, "Facebook", True)

# 6) رقم بمسافات وشرطات
case("رقم بمسافات وشرطات",
     {"chat_id": "c6", "message_body": "010 1234 5678", "sender_identifier": "12345",
      "source": "Facebook", "location": "Religious"},
     True, None, "Facebook", True)

# 7) رقم 015 (فودافون)
case("رقم 015",
     {"chat_id": "c7", "message_body": "01512345678", "sender_identifier": "12345",
      "source": "Facebook", "location": "Religious"},
     True, None, "Facebook", True)

# 8) واتساب (source=whatsapp) → قناة WhatsApp
case("قناة واتساب",
     {"chat_id": "c8", "message_body": "01012345678", "sender_identifier": "201012345678",
      "source": "whatsapp", "location": "Religious", "receiving_phone_id": "999"},
     True, None, "WhatsApp", True)

# 9) الرقم القومي (14 رقمًا يبدأ بـ 30) → لا يعتبر رقم تليفون
case("الرقم القومي لا يُطابق",
     {"chat_id": "c9", "message_body": "الرقم القومي 30101123456789", "sender_identifier": "12345",
      "source": "Facebook", "location": "Religious"},
     False, "no_phone_found", None, False)

# 10) رسالة بدون رقم → skip
case("رسالة بدون رقم",
     {"chat_id": "c10", "message_body": "السلام عليكم عايز استفسر عن البرامج", "sender_identifier": "12345",
      "source": "Facebook", "location": "Religious"},
     False, "no_phone_found", None, False)

# 11) قسم آخر (Hurghada) → مرفوض من الجذور (قاعدة 15)
case("قسم آخر مرفوض",
     {"chat_id": "c11", "message_body": "01012345678", "sender_identifier": "12345",
      "source": "Facebook", "location": "Hurghada"},
     False, "not_religious", None, False)

# 12) بيانات ناقصة → skip
case("بيانات ناقصة",
     {"chat_id": "c12", "message_body": "01012345678", "sender_identifier": "",
      "source": "Facebook", "location": "Religious"},
     False, "missing_data", None, False)

# 13) تكرار نفس الرقم لنفس المحادثة خلال النافذة → يمنع التكرار
case("تكرار نفس الرقم يمنع",
     {"chat_id": "c1", "message_body": "01012345678", "sender_identifier": "12345",
      "source": "Facebook", "location": "Religious", "incoming_external_message_id": "m99"},
     False, "already_processed", None, False)

# 14) رقم مختلف لنفس المحادثة → يُسمح
case("رقم مختلف لنفس المحادثة يُسمح",
     {"chat_id": "c1", "message_body": "01287654321", "sender_identifier": "12345",
      "source": "Facebook", "location": "Religious"},
     True, None, "Facebook", True)

# 15) رقم 9 أرقام فقط → لا يُطابق
case("رقم ناقص لا يُطابق",
     {"chat_id": "c15", "message_body": "010123456", "sender_identifier": "12345",
      "source": "Facebook", "location": "Religious"},
     False, "no_phone_found", None, False)


def run_all():
    agent = MockAgent()
    results = []
    for name, payload, expect_sent, expect_skip, expect_channel, expect_reply in CASES:
        try:
            res = mod.run(agent, dict(payload))
            sent = bool(res.get("sent"))
            skip = res.get("skipped")
            ok = True
            if expect_sent and not sent:
                ok = False
            if not expect_sent and sent:
                ok = False
            if expect_skip is not None and skip != expect_skip:
                ok = False
            if expect_channel is not None:
                last = agent.sent[-1] if agent.sent else None
                if not last or str(last[0]).lower() != str(expect_channel).lower():
                    ok = False
            if expect_reply:
                last = agent.sent[-1] if agent.sent else None
                if not last or last[2] != mod.REPLY_TEXT:
                    ok = False
            results.append((name, ok, res))
        except Exception as e:
            results.append((name, False, f"EXCEPTION: {e}"))

    print("=" * 90)
    print("نتائج الاختبار (Test Results)")
    print("=" * 90)
    all_ok = True
    for name, ok, res in results:
        all_ok = all_ok and ok
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status} | {name}")
        if not ok:
            print(f"      result={res}")
    print("=" * 90)
    print(f"Total: {len(results)} | Passed: {sum(1 for _, ok, _ in results if ok)} | Failed: {sum(1 for _, ok, _ in results if not ok)}")
    print(f"Mock sends: {agent.sends} | Channels: {[s[0] for s in agent.sent]}")
    # التحقق من نص الرد الحرفي
    expected = "الغي الموضوع ده تمام يا فندم، وصلني رقم حضرتك 🧡 هيتواصل معاك على الواتساب في أقرب وقت بكل تفاصيل البرامج والخصم. شكرًا لثقة حضرتك في FTS للسياحة، وربنا يكتبلك الحج 🕋"
    if agent.sent:
        first_reply = agent.sent[0][2]
        print("Exact reply match:", "✅" if first_reply == expected else "❌")
        if first_reply != expected:
            print("REPLY SENT  :", repr(first_reply))
            print("REPLY EXPECT:", repr(expected))
        all_ok = all_ok and (first_reply == expected)
    return all_ok


ok = run_all()
print("=" * 90)
print("FINAL:", "ALL TESTS PASSED ✅" if ok else "SOME TESTS FAILED ❌")
sys.exit(0 if ok else 1)
