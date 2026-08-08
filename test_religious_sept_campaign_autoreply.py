# -*- coding: utf-8 -*-
"""
Test for workflows/religious_sept_campaign_autoreply.py
- Uses a MOCK agent + MOCK chat_db (no real message sends, no real DB writes)
- Verifies exact matching, byte-exact reply texts, location filter, dedup, guards
"""
import sys
import io
import os
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Point state files to a temp dir BEFORE importing the module
_tmp = tempfile.mkdtemp(prefix="sept_campaign_test_")
import workflows.religious_sept_campaign_autoreply as wf
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

# ===== expected replies (copied byte-exact from manager request) =====
EXPECTED = {
    "٢ سبتمبر ✈️": (
        "الله يكرمك 🌹 يبقى نأمّن مقعد حضرتك قبل [٢٠ أغسطس].\n"
        "\n"
        "المطلوب ٣ حاجات بس:\n"
        "1️⃣ صورة جواز السفر (ساري ٦ شهور من تاريخ السفر)\n"
        "2️⃣ صورة شخصية بخلفية بيضا\n"
        "3️⃣ مقدم ٥٠٪ — كاش في مقرنا بالمعادي، إيداع بنكي، أو إنستاباي\n"
        "\n"
        "ابعت صورة الجواز هنا دلوقتي، وقولي حضرتك ناوي على أنهي برنامج وعددكم كام — وهبعتلك قيمة المقدم بالظبط ✅"
    ),
    "٢٣ سبتمبر 🗓": (
        "اختيار مريح 🌹 رحلة ٢٣ سبتمبر بنفس البرامج والأسعار، وقدام حضرتك وقت كافي للتجهيز من غير أي ضغط.\n"
        "\n"
        "ونصيحة : نفس نظام الحجز شغال (٥٠٪ مقدم والباقي قبل السفر بـ١٥ يوم) — واللي بيحجز بدري بيختار غرفته وفندقه على مهله بدل زحمة آخر أسبوع.\n"
        "\n"
        "تحب أبعتلك برنامج أنهي رحلة؟\n"
        "٨ أيام» / «١٥ يوم» / «١٠ أيام ٤ نجوم ⭐"
    ),
    "عندي سؤال الأول": (
        "اسأل براحتك 🌹 وأنا هجاوبك كتابةً عشان تحتفظ بالرد.\n"
        "\n"
        "ولو سؤالك حاجة تانية، اكتبه وهرد عليك فورًا — أو ابعت رقمك ونكلمك صوت أسهل ☎️"
    ),
}

print("== 1) KEYWORD DEFINITIONS vs MANAGER TEXT (byte-exact) ==")
kw_by_id = {k["keyword"]: k for k in wf.KEYWORDS}
check("3 keywords defined", len(wf.KEYWORDS) == 3, f"got {len(wf.KEYWORDS)}")
for kw, expected_reply in EXPECTED.items():
    entry = kw_by_id.get(kw)
    check(f"keyword present: {kw!r}", entry is not None)
    if entry:
        check(f"reply byte-exact for {kw!r}", entry["reply"] == expected_reply,
              f"\nGOT: {entry['reply']!r}\nEXP: {expected_reply!r}")

print("== 2) EXACT MATCH LOGIC ==")
check("match: '٢ سبتمبر ✈️' -> kw1", (wf._match_keyword("٢ سبتمبر ✈️") or {}).get("keyword") == "٢ سبتمبر ✈️")
check("match: '٢ سبتمبر' (no emoji) -> kw1", (wf._match_keyword("٢ سبتمبر") or {}).get("keyword") == "٢ سبتمبر ✈️")
check("match: '٢٣ سبتمبر 🗓' -> kw2", (wf._match_keyword("٢٣ سبتمبر 🗓") or {}).get("keyword") == "٢٣ سبتمبر 🗓")
check("match: '٢٣ سبتمبر' (no emoji) -> kw2", (wf._match_keyword("٢٣ سبتمبر") or {}).get("keyword") == "٢٣ سبتمبر 🗓")
check("match: 'عندي سؤال الأول' -> kw3", (wf._match_keyword("عندي سؤال الأول") or {}).get("keyword") == "عندي سؤال الأول")
# Negative cases: extra words must break exact match
check("NO match: '٢ سبتمبر ✈️ يلا' (extra word)", wf._match_keyword("٢ سبتمبر ✈️ يلا") is None)
check("NO match: 'عندي سؤال' (shorter)", wf._match_keyword("عندي سؤال") is None)
check("NO match: 'عندي سؤال الاول' (hamza diff)", wf._match_keyword("عندي سؤال الاول") is None)
check("NO match: '٢٤ سبتمبر ✈️' (wrong date)", wf._match_keyword("٢٤ سبتمبر ✈️") is None)
check("NO match: '٢ سبتمبر ✈️2' (trailing char)", wf._match_keyword("٢ سبتمبر ✈️2") is None)
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
        return "2026-08-07 15:00:00"
    def update_auto_reply_hold_until(self, chat_id, val):
        return None
    def add_message(self, **kw):
        return None
    def mark_conversation_read(self, chat_id):
        return None
    def delete_proposed_drafts(self, chat_id):
        return None
sys.modules["chat_db"] = FakeChatDB()

def payload(msg, loc="Religious", src="Facebook", sid="1000000001", cid="test-chat-1"):
    return {
        "chat_id": cid,
        "message_body": msg,
        "source": src,
        "sender_identifier": sid,
        "location": loc,
        "receiving_phone_id": None,
        "incoming_external_message_id": "mid.12345",
    }

agent = MockAgent()
r = wf.run(agent, payload("٢ سبتمبر ✈️"))
check("run kw1 ok/sent", r.get("sent") is True and r.get("ok") is True, str(r))
check("run kw1 channel Facebook", r.get("channel") == "Facebook", str(r.get("channel")))
check("run kw1 reply byte-exact", agent.fb_sent and agent.fb_sent[0][1] == EXPECTED["٢ سبتمبر ✈️"],
      repr(agent.fb_sent[0][1]) if agent.fb_sent else "nothing sent")
check("run kw1 keyword reported", r.get("keyword") == "٢ سبتمبر ✈️", str(r))

agent2 = MockAgent()
r2 = wf.run(agent2, payload("٢٣ سبتمبر 🗓"))
check("run kw2 ok/sent", r2.get("sent") is True, str(r2))
check("run kw2 reply byte-exact", agent2.fb_sent and agent2.fb_sent[0][1] == EXPECTED["٢٣ سبتمبر 🗓"])
check("run kw2 channel Facebook", r2.get("channel") == "Facebook")

agent3 = MockAgent()
r3 = wf.run(agent3, payload("عندي سؤال الأول"))
check("run kw3 ok/sent", r3.get("sent") is True, str(r3))
check("run kw3 reply byte-exact", agent3.fb_sent and agent3.fb_sent[0][1] == EXPECTED["عندي سؤال الأول"])

# WhatsApp channel routing
agent4 = MockAgent()
r4 = wf.run(agent4, payload("٢ سبتمبر ✈️", src="WhatsApp", sid="201234567890", cid="test-chat-wa"))
check("run WhatsApp channel", r4.get("channel") == "WhatsApp" and agent4.wa_sent and agent4.fb_sent == [], str(r4))

# Duplicate delivery protection (atomic claim)
agent5 = MockAgent()
r5a = wf.run(agent5, payload("٢٣ سبتمبر 🗓", sid="dup-user-1", cid="test-chat-dup"))
r5b = wf.run(agent5, payload("٢٣ سبتمبر 🗓", sid="dup-user-1", cid="test-chat-dup"))
check("dedup: first sends", r5a.get("sent") is True, str(r5a))
check("dedup: second blocked", r5b.get("skipped") == "already_processed", str(r5b))

print("== 4) STRICT LOCATION FILTER (rule 15) ==")
agent6 = MockAgent()
r6 = wf.run(agent6, payload("٢ سبتمبر ✈️", loc="Hurghada"))
check("Hurghada skipped", r6.get("skipped") == "not_religious" and agent6.fb_sent == [], str(r6))
agent7 = MockAgent()
r7 = wf.run(agent7, payload("٢ سبتمبر ✈️", loc="Sales"))
check("Sales skipped", r7.get("skipped") == "not_religious" and agent7.fb_sent == [], str(r7))

print("== 5) GUARDS ==")
class HoldChatDB(FakeChatDB):
    def get_conversation(self, chat_id):
        return {"needs_help": 0, "auto_reply_hold_until": "2026-08-08 00:00:00"}
sys.modules["chat_db"] = HoldChatDB()
agent8 = MockAgent()
r8 = wf.run(agent8, payload("٢ سبتمبر ✈️", sid="hold-user-1"))
check("hold_until respected", r8.get("skipped") == "human_hold" and agent8.fb_sent == [], str(r8))

class HelpChatDB(FakeChatDB):
    def get_conversation(self, chat_id):
        return {"needs_help": 1, "auto_reply_hold_until": None}
sys.modules["chat_db"] = HelpChatDB()
agent9 = MockAgent()
r9 = wf.run(agent9, payload("٢ سبتمبر ✈️", sid="help-user-1"))
check("needs_help respected", r9.get("skipped") == "human_active" and agent9.fb_sent == [], str(r9))

print("== 6) NO overlap with existing keyword workflows ==")
import re as _re
def load_keywords(path):
    txt = open(path, encoding="utf-8").read()
    return _re.findall(r'"keyword":\s*"([^"]+)"', txt)
existing = []
for p in ["workflows/religious_keyword_autoreply.py",
          "workflows/religious_15day_exact_keyword_autoreply.py",
          "workflows/religious_umrah_phrases_autoreply.py"]:
    if os.path.exists(p):
        existing.extend(load_keywords(p))
mine = [k["keyword"] for k in wf.KEYWORDS]
overlap = [k for k in mine if k in existing]
check("no duplicate keywords vs other workflows", not overlap, f"overlap={overlap}")
# normalized overlap check too
def norm(s):
    s = s.strip().lower()
    s = _re.sub(r"[\u0610-\u061A\u0640\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)
    s = _re.sub(r"[^\w\s]", " ", s, flags=_re.UNICODE)
    return _re.sub(r"\s+", " ", s, flags=_re.UNICODE).strip()
n_overlap = [k for k in mine if norm(k) in {norm(x) for x in existing}]
check("no normalized-duplicate keywords", not n_overlap, f"overlap={n_overlap}")

print(f"\n===== RESULT: {PASS} passed, {FAIL} failed =====")
sys.exit(1 if FAIL else 0)
