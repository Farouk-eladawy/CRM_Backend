# -*- coding: utf-8 -*-
"""Unit test for religious_parent_hajj_booking_autoreply workflow (Rule 7)."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, "workflows")

import religious_parent_hajj_booking_autoreply as wf

FAILED = []

def check(name, cond, detail=""):
    status = "✅" if cond else "❌"
    print(f"{status} {name} {detail}")
    if not cond:
        FAILED.append(name)

KEYWORD = "بحجز لوالدي/والدتي — إيه المطلوب؟"

# ---- 1) Exact match tests ----
check("exact keyword matches 100%",
      wf._match_keyword(KEYWORD) is not None)
check("keyword with trailing period matches (normalization)",
      wf._match_keyword("بحجز لوالدي/والدتي — إيه المطلوب؟.") is not None)
check("keyword with emoji stripped still matches",
      wf._match_keyword("بحجز لوالدي/والدتي — إيه المطلوب؟ 🙏") is not None)
check("keyword with different dash (hyphen) matches",
      wf._match_keyword("بحجز لوالدي/والدتي - إيه المطلوب") is not None)
check("extra word BEFORE breaks exact match",
      wf._match_keyword("لو سمحت بحجز لوالدي/والدتي — إيه المطلوب؟") is None)
check("extra word AFTER breaks exact match",
      wf._match_keyword("بحجز لوالدي/والدتي — إيه المطلوب؟ من فضلك") is None)
check("only one parent (والدي فقط) does NOT match",
      wf._match_keyword("بحجز لوالدي — إيه المطلوب؟") is None)
check("different phrase does NOT match",
      wf._match_keyword("ابعتلي البرامج والأسعار") is None)
check("empty message does NOT match",
      wf._match_keyword("") is None)
check("non-text media does NOT match",
      wf._match_keyword("[customer sent an audio message.]") is None)

# ---- 2) Reply texts exactly as manager requested ----
entry = wf._match_keyword(KEYWORD)
replies = entry["replies"]
check("exactly 3 replies", len(replies) == 3, f"got {len(replies)}")

r1, r2, r3 = replies[0], replies[1], replies[2]

# Message 1 — reassurance (field supervisor)
for needle in ["ربنا يتقبل منك 🌹 دي أجمل هدية ممكن تقدمها لحد في الدنيا",
               "وأهم حاجة نطمنك عليها من الأول: والدك/والدتك مش هيتسابوا",
               "لوحدهم ولا لحظة — مشرفنا الميداني معاهم بالاسم من المطار للمطار",
               "في السكن، في المشاعر، في التنقلات",
               "هيكون معاك رقمه تتواصل معاه وتطمن عليهم أول بأول 👥📞"]:
    check(f"MSG1 contains: {needle[:40]}", needle in r1)

# Message 2 — Tahseen flight program + price
for needle in ["وعشان راحتهم، أنسب برامجنا لكبار السن هو حج الطيران تحسين:",
               "⭐ ٧ أيام إقامة ٥ نجوم على ساحة الحرم مباشرة بعد المناسك — يسمعوا الأذان وينزلوا يصلوا من غير مشي ولا مواصلات",
               "🚆 الانتقال من المدينة لمكة بقطار الحرمين السريع — من غير عناء الطريق",
               "⛺ مخيمات ألماني مكيفة في المشاعر | 🍽 وجبات طوال الرحلة | 📅 ١٩ يوم",
               "💰 السعر للفرد: ٢٥٠ ألف بدلًا من ٢٧٩ — ميزة الـ٢٩,٠٠٠ بتتحفظ باسمهم كتابيًا",
               "وبتتخصم من السعر الرسمي أيًا كان بعد الضوابط",
               "✈️ تذكرة الطيران بسعرها المعلن وقت الحجز | 📌 السعر على أساس الموسم السابق لحين ضوابط ١٤٤٨"]:
    check(f"MSG2 contains: {needle[:40]}", needle in r2)

# Message 3 — requirements + questions + family linking
for needle in ["المطلوب عشان نحجزلهم ونحفظ الميزة باسمهم:",
               "1️⃣ صورة بطاقة والدك/والدتك (لازم تكون سارية ٦ شهور على الأقل)",
               "2️⃣ رقم موبايلك — عليه هيوصلك إثبات الحفظ، وهتصل بحضرتك اظبط معاك كل التفاصيل",
               "⚠️ ومهم نعرف منك حاجتين: سنهم كام؟ وهل سبق لهم الحج قبل كده؟",
               "(شرط التقديم إنها تكون أول مرة)",
               "ولو حابب الاتنين يسافروا مع بعض في نفس المجموعة — بنعمل ربط عائلي",
               "وده بنشرحهولك في المكالمة 😊"]:
    check(f"MSG3 contains: {needle[:40]}", needle in r3)

# ---- 3) run() with mock agent (exact match -> 3 sends, religious only) ----
class FakeAgent:
    def __init__(self):
        self.sent = []
    def send_facebook_message(self, recipient, text=None, **kw):
        self.sent.append(text)
        return True, None
    def send_whatsapp_message(self, recipient, text=None, **kw):
        self.sent.append(text)
        return True, None

# import chat_db stub
import types, chat_db
orig_add = chat_db.add_message
orig_mark = chat_db.mark_conversation_read
orig_del = chat_db.delete_proposed_drafts
orig_get = chat_db.get_conversation
orig_cairo = chat_db.get_cairo_time
chat_db.add_message = lambda *a, **k: True
chat_db.mark_conversation_read = lambda *a, **k: True
chat_db.delete_proposed_drafts = lambda *a, **k: True
chat_db.get_conversation = lambda cid: {}
chat_db.get_cairo_time = lambda: "2026-08-20T12:00:00+03:00"
try:
    chat_db.update_auto_reply_hold_until = lambda *a, **k: True
except Exception:
    pass

agent = FakeAgent()
res = wf.run(agent, {
    "chat_id": "test-chat-parent-1",
    "message_body": KEYWORD,
    "source": "facebook",
    "sender_identifier": "psid-parent-1",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid-parent-1",
})
check("run() sent flag True", res.get("sent") is True, str(res))
check("run() sent exactly 3 messages", len(agent.sent) == 3, f"got {len(agent.sent)}")
check("run() order: msg1 first", agent.sent and agent.sent[0].startswith("ربنا يتقبل منك 🌹"))
check("run() order: msg2 second", agent.sent and agent.sent[1].startswith("وعشان راحتهم"))
check("run() order: msg3 third", agent.sent and agent.sent[2].startswith("المطلوب عشان نحجزلهم"))

# dedup: same message again -> skipped
agent2 = FakeAgent()
res2 = wf.run(agent2, {
    "chat_id": "test-chat-parent-1",
    "message_body": KEYWORD,
    "source": "facebook",
    "sender_identifier": "psid-parent-1",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid-parent-1b",  # different mid -> same unified key
})
check("dedup blocks duplicate (different mid)", res2.get("skipped") == "already_processed", str(res2))
check("dedup: no second send", len(agent2.sent) == 0, f"got {len(agent2.sent)}")

# different chat + exact phrase -> allowed
agent3 = FakeAgent()
res3 = wf.run(agent3, {
    "chat_id": "test-chat-parent-2",
    "message_body": KEYWORD,
    "source": "facebook",
    "sender_identifier": "psid-parent-2",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid-parent-2",
})
check("different chat gets reply", res3.get("sent") is True, str(res3))
check("different chat sends 3", len(agent3.sent) == 3, f"got {len(agent3.sent)}")

# non-religious location -> skipped
agent4 = FakeAgent()
res4 = wf.run(agent4, {
    "chat_id": "test-chat-parent-3",
    "message_body": KEYWORD,
    "source": "facebook",
    "sender_identifier": "psid-parent-3",
    "location": "Hurghada",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid-parent-3",
})
check("non-Religious location skipped", res4.get("skipped") == "not_religious", str(res4))
check("non-Religious sends nothing", len(agent4.sent) == 0)

# near-match phrase -> no send
agent5 = FakeAgent()
res5 = wf.run(agent5, {
    "chat_id": "test-chat-parent-4",
    "message_body": "بحجز لوالدي/والدتي",
    "source": "facebook",
    "sender_identifier": "psid-parent-4",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid-parent-4",
})
check("partial phrase skipped", res5.get("skipped") == "no_keyword_match", str(res5))
check("partial phrase sends nothing", len(agent5.sent) == 0)

# WhatsApp source -> whatsapp channel used
agent6 = FakeAgent()
res6 = wf.run(agent6, {
    "chat_id": "test-chat-parent-5",
    "message_body": KEYWORD,
    "source": "whatsapp",
    "sender_identifier": "201001234567",
    "location": "Religious",
    "receiving_phone_id": "1234567890",
    "incoming_external_message_id": "wamid-parent-5",
})
check("whatsapp source sends 3", res6.get("sent") is True, str(res6))
check("whatsapp sends 3 messages", len(agent6.sent) == 3, f"got {len(agent6.sent)}")

# restore chat_db stubs
chat_db.add_message = orig_add
chat_db.mark_conversation_read = orig_mark
chat_db.delete_proposed_drafts = orig_del
chat_db.get_conversation = orig_get
chat_db.get_cairo_time = orig_cairo

print()
if FAILED:
    print("RESULT: FAILED -", len(FAILED), "checks failed")
    for f in FAILED:
        print("  -", f)
    sys.exit(1)
print("RESULT: ALL CHECKS PASSED ✅")
