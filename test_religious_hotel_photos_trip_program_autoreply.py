# -*- coding: utf-8 -*-
"""Unit test for religious_hotel_photos_trip_program_autoreply workflow (Rule 7)."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, "workflows")

import religious_hotel_photos_trip_program_autoreply as wf

FAILED = []

def check(name, cond, detail=""):
    status = "✅" if cond else "❌"
    print(f"{status} {name} {detail}")
    if not cond:
        FAILED.append(name)

# ---- 1) Exact match tests ----
check("exact keyword matches 100%",
      wf._match_keyword("ابعتولي صور الفندق وبرنامج الرحلة") is not None)
check("keyword with trailing period matches (normalization)",
      wf._match_keyword("ابعتولي صور الفندق وبرنامج الرحلة.") is not None)
check("keyword with emoji stripped still matches",
      wf._match_keyword("ابعتولي صور الفندق وبرنامج الرحلة 📷") is not None)
check("extra word BEFORE breaks exact match",
      wf._match_keyword("لو سمحت ابعتولي صور الفندق وبرنامج الرحلة") is None)
check("extra word AFTER breaks exact match",
      wf._match_keyword("ابعتولي صور الفندق وبرنامج الرحلة من فضلك") is None)
check("different phrase does NOT match",
      wf._match_keyword("ابعتلي البرامج والأسعار") is None)
check("empty message does NOT match",
      wf._match_keyword("") is None)
check("non-text media does NOT match",
      wf._match_keyword("[customer sent an audio message.]") is None)

# ---- 2) Reply texts exactly as manager requested ----
entry = wf._match_keyword("ابعتولي صور الفندق وبرنامج الرحلة")
replies = entry["replies"]
check("exactly 2 replies", len(replies) == 2, f"got {len(replies)}")

r1 = replies[0]
r2 = replies[1]
for needle in ["تفاصيل البرنامج:", "٧ أيام إقامة ٥ نجوم", "تسمع الأذان، تنزل تصلي، تطلع ترتاح",
               "📅 المدة: ١٩ يوم", "⛺ مخيمات ألماني مكيفة", "🚆 الانتقال من المدينة لمكة بقطار الحرمين السريع",
               "🍽 وجبات طوال الرحلة", "👥 مشرفين من الشركة معاك", "💰 السعر: ٢٥٠ ألف بدلًا من ٢٧٩ ألف",
               "بميزة حجز مبكر ٢٩,٠٠٠ ج بتتحفظ باسمك كتابيًا", "تتخصم من السعر الرسمي أيًا كان بعد نزول الضوابط",
               "✈️ تذكرة الطيران تُضاف بسعرها المعلن وقت الحجز",
               "📌 السعر على أساس الموسم السابق لحين إعلان ضوابط ١٤٤٨ الرسمية"]:
    check(f"MSG1 contains: {needle[:40]}", needle in r1)

for needle in ["⚠️ ومعلومة مهمة قبل أي قرار", "التقديم للحج مسموح من جهة واحدة فقط",
               "والاختيار نهائي طول الموسم", "عشان كده اللي بيحجزوا معانا بدري",
               "بنحفظلهم ميزة الـ٢٩,٠٠٠ باسمهم وترتيبهم في القايمة من دلوقتي",
               "تحب نحفظهالك انت كمان؟ 😊", "محتاجين بس صورة بطاقتك ورقم موبايلك",
               "ولو تحب تشوف خط سير الرحلة يوم بيوم الأول، ابعت \"خط السير\"."]:
    check(f"MSG2 contains: {needle[:40]}", needle in r2)

# ---- 3) run() with mock agent (exact match -> 2 sends, religious only) ----
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
    "chat_id": "test-chat-1",
    "message_body": "ابعتولي صور الفندق وبرنامج الرحلة",
    "source": "facebook",
    "sender_identifier": "psid-123",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid-test-1",
})
check("run() sent flag True", res.get("sent") is True, str(res))
check("run() sent exactly 2 messages", len(agent.sent) == 2, f"got {len(agent.sent)}")
check("run() order: msg1 first", agent.sent and agent.sent[0].startswith("تفاصيل البرنامج:"))
check("run() order: msg2 second", agent.sent and agent.sent[1].startswith("⚠️ ومعلومة مهمة"))

# dedup: same message again -> skipped
agent2 = FakeAgent()
res2 = wf.run(agent2, {
    "chat_id": "test-chat-1",
    "message_body": "ابعتولي صور الفندق وبرنامج الرحلة",
    "source": "facebook",
    "sender_identifier": "psid-123",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid-test-2",  # different mid -> same unified key
})
check("dedup blocks duplicate (different mid)", res2.get("skipped") == "already_processed", str(res2))
check("dedup: no second send", len(agent2.sent) == 0, f"got {len(agent2.sent)}")

# different chat + exact phrase -> allowed
agent3 = FakeAgent()
res3 = wf.run(agent3, {
    "chat_id": "test-chat-2",
    "message_body": "ابعتولي صور الفندق وبرنامج الرحلة",
    "source": "facebook",
    "sender_identifier": "psid-456",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid-test-3",
})
check("different chat gets reply", res3.get("sent") is True, str(res3))
check("different chat sends 2", len(agent3.sent) == 2, f"got {len(agent3.sent)}")

# non-religious location -> skipped
agent4 = FakeAgent()
res4 = wf.run(agent4, {
    "chat_id": "test-chat-3",
    "message_body": "ابعتولي صور الفندق وبرنامج الرحلة",
    "source": "facebook",
    "sender_identifier": "psid-789",
    "location": "Hurghada",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid-test-4",
})
check("non-Religious location skipped", res4.get("skipped") == "not_religious", str(res4))
check("non-Religious sends nothing", len(agent4.sent) == 0)

# near-match phrase -> no send
agent5 = FakeAgent()
res5 = wf.run(agent5, {
    "chat_id": "test-chat-4",
    "message_body": "ابعتولي صور الفندق",
    "source": "facebook",
    "sender_identifier": "psid-999",
    "location": "Religious",
    "receiving_phone_id": None,
    "incoming_external_message_id": "mid-test-5",
})
check("partial phrase skipped", res5.get("skipped") == "no_keyword_match", str(res5))
check("partial phrase sends nothing", len(agent5.sent) == 0)

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
