# -*- coding: utf-8 -*-
"""
Test for workflows/religious_applied_already_1448_autoreply.py
- Uses a MOCK agent + MOCK chat_db (no real message sends, no real DB writes)
- Verifies exact matching, byte-exact reply text, location filter, dedup, guards
"""
import sys
import io
import os
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Point state files to a temp dir BEFORE importing the module
_tmp = tempfile.mkdtemp(prefix="applied_already_1448_test_")
import workflows.religious_applied_already_1448_autoreply as wf
wf.DEDUP_DB = os.path.join(_tmp, "test_dedup.db")
wf.STATE_FILE = os.path.join(_tmp, "test_state.json")

PASS = 0
FAIL = 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")

# ===== expected reply (copied byte-exact from manager request 2026-08-19) =====
# ملاحظة: المسافة المزدوجة في "٤٩٥  ألف" مقصودة (كما كتبها المدير بالظبط)
EXPECTED_REPLY = (
    "ربنا يتقبّل منك ويكتبلك الحج بإذن الله 🤍\n"
    "\n"
    "بما إن التقديم في جهة واحدة بس، فللأسف مش هنقدر نسجّلك معانا في قرعة الحج السياحي الموسم ده.\n"
    "\n"
    "لكن لو ما كسبتش في القرعة، عندنا برامج الحج المباشر بتأشيرة خارج حصة القرعة (حسب التوافر)، وأسعارها بتبدأ من ٤٩٥  ألف للفرد.\n"
    "\n"
    "لو حابب نبلغك بالتفاصيل أول ما نتايج القرعة تظهر، ابعتلي رقم موبايلك 📱 وهنكلمك وقتها."
)

print("== 1) KEYWORD DEFINITIONS vs MANAGER TEXT (byte-exact) ==")
kw_by_id = {k["keyword"]: k for k in wf.KEYWORDS}
check("1 keyword defined", len(wf.KEYWORDS) == 1, f"got {len(wf.KEYWORDS)}")
for kw in ["قدّمت خلاص"]:
    entry = kw_by_id.get(kw)
    check(f"keyword present: {kw!r}", entry is not None)
    if entry:
        check(f"reply byte-exact for {kw!r}", entry["reply"] == EXPECTED_REPLY,
              f"\nGOT: {entry['reply']!r}\nEXP: {EXPECTED_REPLY!r}")

print("== 2) EXACT MATCH LOGIC ==")
check("match: 'قدّمت خلاص' -> kw1", (wf._match_keyword("قدّمت خلاص") or {}).get("keyword") == "قدّمت خلاص")
check("match: 'قدمت خلاص' (no shadda) -> kw1", (wf._match_keyword("قدمت خلاص") or {}).get("keyword") == "قدّمت خلاص")
check("match: 'قدّمت خلاص ' (trailing space) -> kw1", (wf._match_keyword("قدّمت خلاص ") or {}).get("keyword") == "قدّمت خلاص")
# Negative cases: extra words must break exact match
check("NO match: 'قدّمت خلاص يلا' (extra word after)", wf._match_keyword("قدّمت خلاص يلا") is None)
check("NO match: 'انا قدّمت خلاص' (extra word before)", wf._match_keyword("انا قدّمت خلاص") is None)
check("NO match: 'قدّمت' (shorter)", wf._match_keyword("قدّمت") is None)
check("NO match: 'قدّمت خلاصي' (wrong word)", wf._match_keyword("قدّمت خلاصي") is None)
check("NO match: 'لما قدّمت خلاص كنت مبسوط' (long sentence)", wf._match_keyword("لما قدّمت خلاص كنت مبسوط") is None)
check("NO match: empty", wf._match_keyword("") is None)
check("NO match: media stub", wf._match_keyword("[customer sent an audio message.") is None)

print("== 3) FULL run() with MOCK agent ==")
class MockAgent:
    def __init__(self):
        self.fb_sent = []
        self.wa_sent = []
        self.cancelled = []
    def send_facebook_message(self, recipient, text):
        self.fb_sent.append((recipient, text))
        return True, None
    def send_whatsapp_message(self, recipient, text, location=None, receiving_phone_id=None):
        self.wa_sent.append((recipient, text))
        return True, None
    def cancel_whatsapp_ai_processing(self, chat_id=None, reason=None):
        self.cancelled.append((chat_id, reason))

# Fake chat_db module (never touches real DB)
class FakeChatDB:
    def get_conversation(self, chat_id):
        return {"needs_help": 0, "auto_reply_hold_until": None}
    def get_cairo_time(self):
        return "2026-08-19 15:00:00"
    def update_auto_reply_hold_until(self, chat_id, val):
        return None
    def add_message(self, **kw):
        return None
    def mark_conversation_read(self, chat_id):
        return None
    def delete_proposed_drafts(self, chat_id):
        return None
sys.modules["chat_db"] = FakeChatDB()

def payload(msg, loc="Religious", src="Facebook", sid="1000000001", cid="test-chat-1", mid="mid-1"):
    return {
        "chat_id": cid,
        "message_body": msg,
        "source": src,
        "sender_identifier": sid,
        "location": loc,
        "receiving_phone_id": "123456789",
        "incoming_external_message_id": mid,
    }

agent = MockAgent()

# 3a) Religious + exact keyword -> should SEND on Facebook
r = wf.run(agent, payload("قدّمت خلاص"))
check("Religious exact kw -> sent=True", bool(r.get("sent")), str(r))
check("Facebook channel used", len(agent.fb_sent) == 1 and agent.wa_sent == [], str(agent.fb_sent))
check("Reply byte-exact sent", agent.fb_sent and agent.fb_sent[0][1] == EXPECTED_REPLY)

# 3b) WhatsApp channel detection (variant without shadda)
r = wf.run(agent, payload("قدمت خلاص", src="WhatsApp", sid="201000000000", cid="test-chat-wa", mid="mid-wa"))
check("WhatsApp exact kw -> sent=True", bool(r.get("sent")), str(r))
check("WhatsApp channel used", len(agent.wa_sent) == 1, str(agent.wa_sent))
check("WhatsApp reply byte-exact", agent.wa_sent and agent.wa_sent[0][1] == EXPECTED_REPLY)

# 3c) Non-religious location -> MUST be skipped (strict scope, rule 15)
r = wf.run(agent, payload("قدّمت خلاص", loc="Hurghada", cid="test-chat-hurghada", mid="mid-hurghada"))
check("Hurghada -> skipped not_religious", r.get("skipped") == "not_religious", str(r))

# 3d) Religious but non-matching message -> no reply
r = wf.run(agent, payload("عايز أسأل عن حاجة", cid="test-chat-nomatch", mid="mid-nomatch"))
check("Non-matching message -> skipped no_keyword_match", r.get("skipped") == "no_keyword_match", str(r))

# 3e) Dedup: same chat + same normalized text again -> no second send
before = len(agent.fb_sent)
r = wf.run(agent, payload("قدّمت خلاص", cid="test-chat-1", mid="mid-1-dup"))
check("Duplicate delivery -> skipped already_processed", r.get("skipped") == "already_processed", str(r))
check("No second send", len(agent.fb_sent) == before, f"{len(agent.fb_sent)} vs {before}")

# 3f) needs_help=1 -> human active guard
class FakeChatDBHelp(FakeChatDB):
    def get_conversation(self, chat_id):
        return {"needs_help": 1, "auto_reply_hold_until": None}
sys.modules["chat_db"] = FakeChatDBHelp()
r = wf.run(agent, payload("قدّمت خلاص", cid="test-chat-help", mid="mid-help"))
check("needs_help=1 -> skipped human_active", r.get("skipped") == "human_active", str(r))
sys.modules["chat_db"] = FakeChatDB()

print("== 4) REGISTERED WORKFLOW IN DB (read-only check) ==")
try:
    import automation_db
    w = automation_db.get_workflow("religious_applied_already_1448_autoreply_v1")
    check("Workflow exists in DB", w is not None)
    if w:
        check("Enabled = 1", int(w.get("enabled") or 0) == 1)
        check("trigger_type = message_received", str(w.get("trigger_type") or "").strip() == "message_received")
        name = str(w.get("name") or "")
        check("Name contains 'قدّمت خلاص 1448'", "قدّمت خلاص 1448" in name, name)
        check("Name contains 'Religious'", "Religious" in name, name)
        check("Name contains 'ديني'", "ديني" in name, name)
        steps = __import__("json").loads(str(w.get("steps_json") or "[]"))
        check("Has 2 steps (guard + http_request)", len(steps) == 2, str(len(steps)))
        urls = [s.get("url") for s in steps if s.get("type") == "http_request"]
        check("http_request -> run_script endpoint", any("/api/automation/run_script" in str(u) for u in urls), str(urls))
        scripts = [s.get("body", {}).get("script_name") for s in steps if s.get("type") == "http_request"]
        check("script_name = religious_applied_already_1448_autoreply.py",
              any(str(s) == "religious_applied_already_1448_autoreply.py" for s in scripts), str(scripts))
except Exception as e:
    check(f"DB check failed: {e}", False)

print(f"\n===== RESULT: {PASS} passed, {FAIL} failed =====")
sys.exit(1 if FAIL else 0)
