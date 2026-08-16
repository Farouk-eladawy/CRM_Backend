# -*- coding: utf-8 -*-
"""
Test: religious_hajj_programs_prices_whatsapp_autoreply.py
محاكاة كاملة لسيناريوهات الرد اللحظي قبل الاعتماد النهائي (قاعدة النظام 7).
"""
import sys
import io
import importlib.util

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SPEC_PATH = "workflows/religious_hajj_programs_prices_whatsapp_autoreply.py"

# ===== تحميل السكربت (نفس آلية محرك الأتمتة run_automation_script) =====
spec = importlib.util.spec_from_file_location("wf_under_test", SPEC_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# الرد المتوقع حرفياً من طلب المدير (يُقارن به للتحقق من سلامة النص)
EXPECTED_REPLY = (
    "ربنا يكرمك يا فندم 🤲 دي برامج حج ١٤٤٨ عندنا:\n"
    "\n"
    "✈️ البرنامج الاقتصادي (طيران) — يبدأ من ٢٢٠,٠٠٠ ج\n"
    "✈️ برنامج التحسين (طيران – مستوى أعلى في السكن والخدمة) — يبدأ من ٢٥٠,٠٠٠ ج\n"
    "🏨 برنامج الـ ٥ نجوم — حوالي ٤٩٠,٠٠٠ ج\n"
    "\n"
    "📌 البرنامج البري كان بيبدأ من ١٩٠,٠٠٠ ج واتحجز بالكامل — الأماكن فعلاً بتخلص بدري.\n"
    "\n"
    "وحضرتك ضمن حصة عملاء الموسم الماضي، فالخصم مطبق ومحفوظ ليك✅\n"
    "الأسعار دي استرشادية بناءً على الموسم الماضي — والأسعار النهائية بتتأكد فور صدور ضوابط الوزارة، وأي حد محجوز في الحصة خصمه ومكانه محفوظين في كل الأحوال.\n"
    "\n"
    "🪪 التسجيل المبدئي بصورة البطاقة بس — من غير أي مقدم دلوقتي.\n"
    "شركة FTS مرخصة من وزارة السياحة فئة (أ) — ترخيص رقم ٢٠٨٩.\n"
    "\n"
    "تحب أثبتلك مكانك في أنهي برنامج؟ 😊"
)


class FakeAgent:
    """يحاكي الـ agent الحقيقي (send_whatsapp_message / send_facebook_message)."""

    def __init__(self):
        self.whatsapp_sent = []
        self.facebook_sent = []
        self.cancel_calls = []

    def send_whatsapp_message(self, sender_identifier, text=None, location=None, receiving_phone_id=None):
        self.whatsapp_sent.append({"to": sender_identifier, "text": text, "location": location, "receiving_phone_id": receiving_phone_id})
        return True, None

    def send_facebook_message(self, sender_identifier, text=None):
        self.facebook_sent.append({"to": sender_identifier, "text": text})
        return True, None

    def cancel_whatsapp_ai_processing(self, **kwargs):
        self.cancel_calls.append(kwargs)


PASS = []
FAIL = []


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print(f"  ✅ {name}")
    else:
        FAIL.append(name)
        print(f"  ❌ {name}  {detail}")


def base_payload(**overrides):
    p = {
        "chat_id": "chat_test_hajj_wa_001",
        "message_body": "ابعتلي البرامج والأسعار",
        "source": "whatsapp",
        "sender_identifier": "201001234567",
        "location": "Religious",
        "receiving_phone_id": "123456789012345",
        "incoming_external_message_id": "wamid.UNIQUE_TEST_001",
    }
    p.update(overrides)
    return p


# ===== اختبار 1: مطابقة دقيقة 100% عبر واتساب → إرسال فوري =====
print("Test 1: Exact match (WhatsApp) -> instant reply")
agent = FakeAgent()
res = mod.run(agent, base_payload())
check("sent=True", res.get("sent") is True, str(res))
check("channel=WhatsApp", res.get("channel") == "WhatsApp", str(res))
check("1 whatsapp msg", len(agent.whatsapp_sent) == 1, str(agent.whatsapp_sent))
check("1 facebook msg (0)", len(agent.facebook_sent) == 0)
sent_text = agent.whatsapp_sent[0]["text"] if agent.whatsapp_sent else ""
check("reply text == exact requested text", sent_text == EXPECTED_REPLY,
      f"\nGOT: {sent_text[:300]!r}\nEXP: {EXPECTED_REPLY[:300]!r}")
check("whatsapp routing to correct phone", agent.whatsapp_sent and agent.whatsapp_sent[0]["to"] == "201001234567")
check("receiving_phone_id passed", agent.whatsapp_sent and agent.whatsapp_sent[0]["receiving_phone_id"] == "123456789012345")

# ===== اختبار 2: منع التكرار (نفس الرسالة مرة ثانية خلال النافذة) =====
print("Test 2: Duplicate delivery -> already_processed (no re-send)")
res2 = mod.run(agent, base_payload(incoming_external_message_id="wamid.DUPLICATE_002"))
check("skip already_processed", res2.get("skipped") == "already_processed", str(res2))
check("still 1 whatsapp msg only", len(agent.whatsapp_sent) == 1, str(len(agent.whatsapp_sent)))

# ===== اختبار 3: كلمات إضافية → لا رد (Exact فقط) =====
print("Test 3: Extra words -> no_keyword_match (Exact match ممنوع Contains)")
agent3 = FakeAgent()
res3 = mod.run(agent3, base_payload(chat_id="chat_test_hajj_wa_003",
                                    message_body="عايز ابعتلي البرامج والأسعار دلوقتي",
                                    incoming_external_message_id="wamid.EXTRA_003"))
check("skip no_keyword_match", res3.get("skipped") == "no_keyword_match", str(res3))
check("0 messages sent", len(agent3.whatsapp_sent) == 0 and len(agent3.facebook_sent) == 0)

# ===== اختبار 4: قسم آخر → لا رد (فلترة صارمة) =====
print("Test 4: Other location (Hurghada) -> not_religious (لا نمس أقساماً أخرى)")
agent4 = FakeAgent()
res4 = mod.run(agent4, base_payload(chat_id="chat_test_hajj_wa_004", location="Hurghada",
                                    incoming_external_message_id="wamid.OTHER_004"))
check("skip not_religious", res4.get("skipped") == "not_religious", str(res4))
check("0 messages sent", len(agent4.whatsapp_sent) == 0 and len(agent4.facebook_sent) == 0)

# ===== اختبار 5: رسالة عبر فيسبوك (نفس الكلمة) → توجيه فيسبوك =====
print("Test 5: Same keyword via Facebook -> facebook channel")
agent5 = FakeAgent()
res5 = mod.run(agent5, base_payload(chat_id="chat_test_hajj_wa_005",
                                    source="facebook",
                                    sender_identifier="fb_user_987",
                                    incoming_external_message_id="mid.FB_005"))
check("sent=True", res5.get("sent") is True, str(res5))
check("channel=Facebook", res5.get("channel") == "Facebook", str(res5))
check("1 facebook msg", len(agent5.facebook_sent) == 1, str(agent5.facebook_sent))

# ===== اختبار 6: مطابقة حتى مع إيموجي/ترقيم إضافي حول النص (التطبيع يحذف الرموز فقط) =====
print("Test 6: Exact match with emoji/punctuation only (normalization) -> reply")
agent6 = FakeAgent()
res6 = mod.run(agent6, base_payload(chat_id="chat_test_hajj_wa_006",
                                    message_body="ابعتلي البرامج والأسعار 🙏",
                                    incoming_external_message_id="wamid.EMOJI_006"))
check("sent=True", res6.get("sent") is True, str(res6))

# ===== اختبار 7: نص مختلف تماماً → لا رد =====
print("Test 7: Unrelated text -> no_keyword_match")
agent7 = FakeAgent()
res7 = mod.run(agent7, base_payload(chat_id="chat_test_hajj_wa_007",
                                    message_body="عايز حجز عمرة",
                                    incoming_external_message_id="wamid.UNREL_007"))
check("skip no_keyword_match", res7.get("skipped") == "no_keyword_match", str(res7))

# ===== اختبار 8: إعادة تحميل السكربت عبر محرك الأتمتة (run_automation_script) =====
print("Test 8: Engine reload path (import same as ai_agent.run_automation_script)")
import os
import importlib.util as ilu
import sys as _sys
script_path = os.path.join(os.getcwd(), "workflows", "religious_hajj_programs_prices_whatsapp_autoreply.py")
mod_name = "dynamic_workflow_religious_hajj_programs_prices_whatsapp_autoreply"
spec8 = ilu.spec_from_file_location(mod_name, script_path)
mod8 = ilu.module_from_spec(spec8)
_sys.modules[mod_name] = mod8
spec8.loader.exec_module(mod8)
check("module has run()", hasattr(mod8, "run"))
check("KEYWORDS[0].keyword == 'ابعتلي البرامج والأسعار'",
      mod8.KEYWORDS[0]["keyword"] == "ابعتلي البرامج والأسعار",
      repr(mod8.KEYWORDS[0]["keyword"]))

print()
print(f"=== RESULT: {len(PASS)} passed / {len(FAIL)} failed ===")
if FAIL:
    sys.exit(1)
