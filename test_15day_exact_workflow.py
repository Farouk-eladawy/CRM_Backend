# -*- coding: utf-8 -*-
"""Test the new 15 Days Exact Keyword workflow (matching + run flow with mock agent)."""
import sys, io, importlib.util, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load the workflow script as a module
spec = importlib.util.spec_from_file_location("wf_test", os.path.join("workflows", "religious_15day_exact_keyword_autoreply.py"))
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)

passed = 0
failed = 0

def check(label, cond, extra=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS: {label}")
    else:
        failed += 1
        print(f"  FAIL: {label} {extra}")

K1 = "ابعتولي برنامج الـ١٥ يوم بالتفصيل 📋"
K2 = "إيه أقرب مواعيد السفر المتاحة؟ 🗓"
K3 = "السعر ٤٠٬٩٥٠ شامل إيه بالظبط؟ 💰"

print("=== 1. Exact match tests (keyword equals message) ===")
m = wf._match_keyword(K1)
check("K1 matches rule 1", m and m["keyword"] == K1, str(m and m.get("keyword")))
m = wf._match_keyword(K2)
check("K2 matches rule 2", m and m["keyword"] == K2, str(m and m.get("keyword")))
m = wf._match_keyword(K3)
check("K3 matches rule 3", m and m["keyword"] == K3, str(m and m.get("keyword")))

print("=== 2. Exact match: emoji/punctuation tolerant (same normalized text) ===")
m = wf._match_keyword("ابعتولي برنامج الـ١٥ يوم بالتفصيل")
check("K1 without emoji still exact-matches", m and m["keyword"] == K1)
m = wf._match_keyword("إيه أقرب مواعيد السفر المتاحة؟")
check("K2 without emoji still exact-matches", m and m["keyword"] == K2)
m = wf._match_keyword("السعر ٤٠٬٩٥٠ شامل إيه بالظبط؟")
check("K3 without emoji still exact-matches", m and m["keyword"] == K3)

print("=== 3. NO Contains / extra words / partial (must NOT match) ===")
m = wf._match_keyword("ابعتولي برنامج الـ١٥ يوم بالتفصيل من فضلك")
check("K1 + extra trailing words -> NO match", m is None, str(m and m.get("keyword")))
m = wf._match_keyword("ابعتولي برنامج الـ١٥ يوم بالتفصيل 📋 لو سمحت")
check("K1 + extra words after emoji -> NO match", m is None, str(m and m.get("keyword")))
m = wf._match_keyword("ابعتولي برنامج الـ١٥ يوم")
check("Partial K1 -> NO match", m is None, str(m and m.get("keyword")))
m = wf._match_keyword("إيه أقرب مواعيد السفر المتاحة في أقرب وقت")
check("K2 + extra words -> NO match", m is None, str(m and m.get("keyword")))
m = wf._match_keyword("السعر ٤٠٬٩٥٠ شامل إيه بالظبط يا فندم")
check("K3 + extra words -> NO match", m is None, str(m and m.get("keyword")))
m = wf._match_keyword("السعر كام لبرنامج العمرة")
check("Different question -> NO match", m is None)
m = wf._match_keyword("أهلا بيكم")
check("Generic greeting -> NO match", m is None)

print("=== 4. Run flow with mock agent (Facebook) ===")
class MockAgent:
    def __init__(self):
        self.sent = []
        self.kb = None
    def send_facebook_message(self, psid, text=None, media_url=None, media_type=None):
        self.sent.append(("fb", psid, text))
        return (True, None)
    def send_whatsapp_message(self, phone, text=None, location="Unknown", receiving_phone_id=None, **kw):
        self.sent.append(("wa", phone, text))
        return (True, None)

# Simulate chat_db so we don't touch the real DB during tests
import types
fake = types.ModuleType("chat_db")
fake.get_conversation = lambda chat_id: {"chat_id": chat_id, "needs_help": 0, "auto_reply_hold_until": "", "location": "Religious"}
fake.get_cairo_time = lambda: __import__('datetime').datetime.now().isoformat()
fake.update_auto_reply_hold_until = lambda *a, **k: None
fake.add_message = lambda **k: None
fake.mark_conversation_read = lambda *a, **k: None
import sys as _sys
_sys.modules["chat_db"] = fake

agent = MockAgent()
payload = {
    "chat_id": "test_chat_exact_1",
    "message_body": K1,
    "source": "Facebook",
    "sender_identifier": "psid_111",
    "location": "Religious",
    "receiving_phone_id": "",
    "incoming_external_message_id": "mid_test_1",
}
res = wf.run(agent, payload, )
print("  run result:", res)
check("run() ok and sent", res.get("ok") and res.get("sent"))
check("reply sent once", len(agent.sent) == 1)
check("keyword returned = K1", res.get("keyword") == K1)

print("=== 5. Dedup: same message again -> already_processed ===")
agent2 = MockAgent()
res2 = wf.run(agent2, payload, )
check("second identical message not re-sent", res2.get("skipped") == "already_processed" and len(agent2.sent) == 0, str(res2))

print("=== 6. Different keyword in same chat -> sends its own reply ===")
agent3 = MockAgent()
payload3 = dict(payload, message_body=K2, incoming_external_message_id="mid_test_2")
res3 = wf.run(agent3, payload3, )
check("K2 sent its own reply", res3.get("sent") and res3.get("keyword") == K2 and len(agent3.sent) == 1, str(res3))

print("=== 7. Non-religious location -> skipped ===")
agent4 = MockAgent()
payload4 = dict(payload, location="Hurghada", message_body=K1, incoming_external_message_id="mid_test_3")
res4 = wf.run(agent4, payload4, )
check("Hurghada skipped, nothing sent", res4.get("skipped") == "not_religious" and len(agent4.sent) == 0, str(res4))

print("=== 8. WhatsApp source -> sent via WhatsApp ===")
agent5 = MockAgent()
payload5 = dict(payload, source="WhatsApp", sender_identifier="201001234567", message_body=K3, incoming_external_message_id="mid_test_4")
res5 = wf.run(agent5, payload5, )
check("WhatsApp sent via wa", res5.get("sent") and agent5.sent and agent5.sent[0][0] == "wa", str(res5))

print()
print(f"RESULTS: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
