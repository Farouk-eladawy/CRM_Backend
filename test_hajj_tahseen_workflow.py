# -*- coding: utf-8 -*-
"""
Isolated simulation test for workflows/hajj_tahseen_followup.py
Uses a TEMP database (FTS_DATA_DIR env) + mock agent => ZERO real sends.
"""
import os, sys, io, json, uuid, sqlite3, shutil, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from datetime import datetime, timedelta

TMP = tempfile.mkdtemp(prefix="hajj_tahseen_test_")
os.environ["FTS_DATA_DIR"] = TMP
print("TEMP DATA DIR:", TMP)

# ملاحظة: fts_paths.get_data_path يتحقق من وجود الملف في مجلد البيانات قبل
# الرجوع للمجلد الأصلي للملفات من نوع .json — لذا نُنشئ ملف الحالة في TMP
# مسبقاً حتى لا يقع الـ fallback على ملف الحالة الحقيقي في جذر المشروع
# (حماية من تلويث حالة الإنتاج أثناء الاختبار).
_state_guard = os.path.join(TMP, "hajj_tahseen_followup_state.json")
with open(_state_guard, "w", encoding="utf-8") as _f:
    _f.write("{}")

import chat_db
now = datetime.fromisoformat(chat_db.get_cairo_time()).replace(tzinfo=None)
print("NOW (Cairo):", now.isoformat())

DBP = os.path.join(TMP, "chat_history.db")
conn = sqlite3.connect(DBP)
c = conn.cursor()
c.execute("""CREATE TABLE conversations (
  chat_id TEXT PRIMARY KEY, source TEXT, sender_identifier TEXT, contact_name TEXT,
  airtable_record_id TEXT, last_message_time TIMESTAMP, unread_count INTEGER DEFAULT 0,
  location TEXT DEFAULT 'Unknown', needs_help INTEGER DEFAULT 0, thread_id TEXT,
  receiving_phone_id TEXT, force_read_at TIMESTAMP, is_closed INTEGER DEFAULT 0,
  closed_by TEXT, booking_number TEXT, lead_owner_user_id TEXT, lead_owner_name TEXT,
  lead_owner_assigned_at TIMESTAMP, sales_inbox INTEGER DEFAULT 0,
  last_customer_channel TEXT, auto_reply_hold_until TIMESTAMP, is_deleted INTEGER DEFAULT 0,
  deleted_at TIMESTAMP, deleted_by TEXT, deleted_reason TEXT, quality_from_location TEXT,
  email_account_id TEXT, department TEXT DEFAULT 'general', assigned_to TEXT,
  recipient_phone TEXT, customer_phone TEXT, facebook_ad_source TEXT, facebook_ad_type TEXT,
  facebook_ad_id TEXT, facebook_ad_ref TEXT, facebook_ad_title TEXT, facebook_post_id TEXT,
  facebook_ad_media_url TEXT
)""")
c.execute("""CREATE TABLE messages (
  msg_id TEXT PRIMARY KEY, chat_id TEXT, sender_type TEXT, text TEXT,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT, source TEXT,
  external_message_id TEXT, reaction_to_external_message_id TEXT, reaction_emoji TEXT,
  staff_note TEXT
)""")
c.execute("""CREATE TABLE IF NOT EXISTS sales_customer_state (
  chat_id TEXT PRIMARY KEY, lead_status TEXT, priority TEXT, ai_priority TEXT,
  tags TEXT, ai_tags TEXT, lead_score INTEGER, follow_up_date TEXT, last_contact_date TEXT,
  next_action TEXT, ai_next_action TEXT, sales_notes TEXT, ai_sales_summary TEXT,
  is_starred INTEGER DEFAULT 0, reason_for_marking TEXT, assigned_sales_user TEXT,
  needs_ai_review INTEGER DEFAULT 0, overdue_followup INTEGER DEFAULT 0,
  ready_to_close INTEGER DEFAULT 0, updated_at TEXT, created_at TEXT
)""")
conn.commit()

AD = "120246971083710757"
_mid = [0]
def iso(hours_ago):
    return (now - timedelta(hours=hours_ago)).isoformat()

def add_conv(chat_id, last_msg_time, ad=AD, source="Facebook", needs_help=0, is_closed=0):
    c.execute("INSERT INTO conversations (chat_id, source, sender_identifier, contact_name, location, last_message_time, needs_help, is_closed, facebook_ad_id) VALUES (?,?,?,?,?,?,?,?,?)",
              (chat_id, source, "psid_" + chat_id, "TestCustomer", "Religious", last_msg_time, needs_help, is_closed, ad))

def add_msg(chat_id, sender_type, text, ts):
    _mid[0] += 1
    c.execute("INSERT INTO messages (msg_id, chat_id, sender_type, text, timestamp, status, source) VALUES (?,?,?,?,?,?,?)",
              (f"m{_mid[0]}", chat_id, sender_type, text, ts, "received" if sender_type == "customer" else "sent", "Facebook"))

def init_conv(chat_id, customer_msgs, agent_last_ts, needs_help=0, is_closed=0, ad=AD):
    add_conv(chat_id, agent_last_ts, ad=ad, needs_help=needs_help, is_closed=is_closed)
    for text, ts in customer_msgs:
        add_msg(chat_id, "customer", text, ts)
    add_msg(chat_id, "agent", "أهلًا بحضرتك 🌿", agent_last_ts)

# ===== Seed =====
# A: normal lead, last customer msg 2.5h ago => stage 1 (normal)
init_conv("chat_A", [("تفاصيل البرنامج", iso(2.6))], iso(2.5))
# B: HOT lead (pressed "إزاي أحجز؟"), last customer msg 54min ago => stage 1 (hot) at 45min
init_conv("chat_B", [("إزاي أحجز؟", iso(1.0))], iso(0.9))
# C: last customer msg 9h ago => stage 2 (catch-up, skip stage1)
init_conv("chat_C", [("مميزات طيران تحسين؟", iso(9.2))], iso(9.1))
# D: last customer msg 21.5h ago => stage 3
init_conv("chat_D", [("عايز أعرف التفاصيل", iso(21.6))], iso(21.5))
# E: last customer msg 25h ago => window closed, no stage ever => dropped from state
init_conv("chat_E", [("إيه السعر؟", iso(25.5))], iso(25.0))
# F: replied 3h ago with normal msg (for later keyword test)
init_conv("chat_F", [("عايز أعرف التفاصيل", iso(3.2))], iso(3.1))
# G: replied 3h ago (for later 'أحجز' test)
init_conv("chat_G", [("ممكن تفاصيل", iso(3.2))], iso(3.1))
# H: replied 3h ago (for later phone test)
init_conv("chat_H", [("سعر ايه", iso(3.2))], iso(3.1))
# I: replied 3h ago (for later opt-out test)
init_conv("chat_I", [("تمام شكرا", iso(3.2))], iso(3.1))
# J: replied 3h ago (for later other-reply reset test)
init_conv("chat_J", [("ايه البرامج المتاحة؟", iso(3.2))], iso(3.1))
# K: needs_help=1 => must be skipped entirely
init_conv("chat_K", [("ممكن تفاصيل", iso(2.5))], iso(2.4), needs_help=1)
# L: DIFFERENT ad => must NOT appear
init_conv("chat_L", [("تفاصيل", iso(2.5))], iso(2.4), ad="999999999999999999")
conn.commit()

# ===== Mock agent =====
class MockAgent:
    def __init__(self):
        self.sent = []
        self.whatsapp = []
    def send_facebook_message(self, recipient_psid, text=None, media_url=None, media_type=None):
        self.sent.append({"channel": "facebook", "to": recipient_psid, "text": text})
        return True, None
    def send_whatsapp_message(self, recipient_phone, text=None, location="Unknown", media_url=None, media_type=None,
                              template_name=None, template_language="en", booking_data=None, template_variables=None,
                              receiving_phone_id=None, template_header_media_url=None, template_header_media_type=None):
        self.whatsapp.append({"to": recipient_phone, "text": text})
        return True, None

# Import the workflow module AFTER setting FTS_DATA_DIR
import importlib.util
spec = importlib.util.spec_from_file_location("hajj_tahseen_followup", os.path.join(os.path.dirname(__file__), "workflows", "hajj_tahseen_followup.py"))
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)

agent = MockAgent()
failures = []

def check(name, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    if not cond:
        failures.append(name)
    print(f"  [{status}] {name} {extra}")

def sent_to(chat_id, text=None):
    target = "psid_" + chat_id
    return [s for s in agent.sent if s["to"] == target and (text is None or s["text"] == text)]

print("\n===== RUN 1 (initial scan: fresh chats init only, NO sends) =====")
r1 = wf.run(agent, {})
print("  result:", json.dumps(r1, ensure_ascii=False)[:400])
state1 = json.load(open(os.path.join(TMP, "hajj_tahseen_followup_state.json"), encoding="utf-8"))
chats1 = state1["chats"]
check("run1 sends nothing (init-only design)", r1.get("sent_count") == 0)
check("run1 processed 9 chats (E quick-skipped: 25h>window)", r1.get("processed_chats") == 9)
check("B marked hot_lead", chats1.get("chat_B", {}).get("hot_lead") is True)
check("A not hot_lead", chats1.get("chat_A", {}).get("hot_lead") is False)
check("A initialized", "chat_A" in chats1)
check("K not in state (needs_help skip)", "chat_K" not in chats1)
check("L not in state (different ad)", "chat_L" not in chats1)

print("\n===== RUN 2 (stage sends + customer replies + window closure) =====")
# F replies "ملخص"
add_msg("chat_F", "customer", "ملخص", iso(0.05))
# G replies "أحجز"
add_msg("chat_G", "customer", "أحجز", iso(0.05))
# H replies with phone number (Arabic-Indic digits to test normalization)
add_msg("chat_H", "customer", "رقمي ٠١٠١٢٣٤٥٦٧٨ واتصل بي", iso(0.05))
# I replies opt-out
add_msg("chat_I", "customer", "متبعتليش تاني", iso(0.05))
# J replies a normal question
add_msg("chat_J", "customer", "وايه بقي أسعار باقي البرامج؟", iso(0.05))
conn.commit()

r2 = wf.run(agent, {})
print("  result:", json.dumps(r2, ensure_ascii=False)[:400])
state2 = json.load(open(os.path.join(TMP, "hajj_tahseen_followup_state.json"), encoding="utf-8"))
chats2 = state2["chats"]

check("A sent stage1 normal", any("حضرتك لسه معانا؟ 🕋" in s["text"] for s in sent_to("chat_A")))
check("B sent stage1 HOT (booking content)", any("خطوات الحجز في برنامج طيران تحسين" in s["text"] for s in sent_to("chat_B")))
check("C sent stage2", any(s["text"] == wf.MSG_STAGE2 for s in sent_to("chat_C")))
check("D sent stage3 (elapsed 21.5h)", any(s["text"] == wf.MSG_STAGE3 for s in sent_to("chat_D")))
check("E dropped from state (never started, window closed)", "chat_E" not in chats2)
check("F got summary", any("ملخص برنامج طيران تحسين الكامل" in s["text"] for s in sent_to("chat_F")))
check("F counter reset (highest=0)", chats2.get("chat_F", {}).get("highest_stage_sent") == 0)
check("F last_customer_reply updated", chats2.get("chat_F", {}).get("last_customer_reply") == iso(0.05))
check("G got booking steps", any("خطوات الحجز في برنامج طيران تحسين" in s["text"] for s in sent_to("chat_G")))
check("G handled", chats2.get("chat_G", {}).get("handled") is True)
convG = chat_db.get_conversation_info("chat_G") or {}
check("G needs_help=1", int(convG.get("needs_help") or 0) == 1)
check("H got thanks + registered phone", any("تم استلام رقم حضرتك" in s["text"] for s in sent_to("chat_H")))
convH = chat_db.get_conversation_info("chat_H") or {}
check("H customer_phone saved", convH.get("customer_phone") == "01012345678")
check("H needs_help=1", int(convH.get("needs_help") or 0) == 1)
check("I opted out", chats2.get("chat_I", {}).get("opted_out") is True)
check("I no send", len(sent_to("chat_I")) == 0)
check("J no send (other reply reset)", len(sent_to("chat_J")) == 0)
check("J counter reset", chats2.get("chat_J", {}).get("highest_stage_sent") == 0)
check("A highest_stage_sent=1", chats2.get("chat_A", {}).get("highest_stage_sent") == 1)
check("B highest_stage_sent=1", chats2.get("chat_B", {}).get("highest_stage_sent") == 1)
check("C highest_stage_sent=2", chats2.get("chat_C", {}).get("highest_stage_sent") == 2)
check("D highest_stage_sent=3", chats2.get("chat_D", {}).get("highest_stage_sent") == 3)

print("\n===== RUN 3 (no duplicates) =====")
r3 = wf.run(agent, {})
print("  result:", json.dumps(r3, ensure_ascii=False)[:400])
check("A got exactly 1 message total", len(sent_to("chat_A")) == 1)
check("B got exactly 1 message total", len(sent_to("chat_B")) == 1)
check("C got exactly 1 message total", len(sent_to("chat_C")) == 1)
check("D got exactly 1 message total", len(sent_to("chat_D")) == 1)
check("F got exactly 1 message total", len(sent_to("chat_F")) == 1)
check("G got exactly 1 message total", len(sent_to("chat_G")) == 1)
check("H got exactly 1 message total", len(sent_to("chat_H")) == 1)
check("no messages sent in run3", r3.get("sent_count") == 0)

print("\n===== RUN 4 (simulate time passing: D's last reply ages to 25h => tag) =====")
# محاكاة مرور الوقت بشكل متسق: نُقدّم توقيت آخر رد D في الحالة وفي قاعدة البيانات
# إلى ما قبل 25 ساعة (لو قدّمنا الحالة فقط لبدا وكأن عميلاً أرسل رسالة أحدث لم تُرصد)
c.execute("UPDATE messages SET timestamp = ? WHERE chat_id = 'chat_D'", (iso(25.0),))
c.execute("UPDATE conversations SET last_message_time = ? WHERE chat_id = 'chat_D'", (iso(25.0),))
conn.commit()
st4 = json.load(open(os.path.join(TMP, "hajj_tahseen_followup_state.json"), encoding="utf-8"))
st4["chats"]["chat_D"]["last_customer_reply"] = iso(25.0)
json.dump(st4, open(os.path.join(TMP, "hajj_tahseen_followup_state.json"), "w", encoding="utf-8"), ensure_ascii=False)
r4 = wf.run(agent, {})
print("  result:", json.dumps(r4, ensure_ascii=False)[:400])
state4 = json.load(open(os.path.join(TMP, "hajj_tahseen_followup_state.json"), encoding="utf-8"))
chats4 = state4["chats"]
check("D tagged no-response", chats4.get("chat_D", {}).get("tagged") is True)
check("D sequence_done", chats4.get("chat_D", {}).get("sequence_done") is True)
salesD = chat_db.get_sales_state("chat_D") or {}
check("D sales tag contains no-response-hajj-tahseen", "no-response-hajj-tahseen" in str(salesD.get("tags") or ""))
# no further sends in run 4
check("run4 sends nothing", r4.get("sent_count") == 0)

# messages were logged into temp DB as agent 'sent' (only the workflow's 7 sends)
n_logged = c.execute("SELECT COUNT(*) FROM messages WHERE sender_type='agent' AND status='sent' AND (text LIKE '%لسه معانا%' OR text LIKE '%قرار الحج مش سهل%' OR text LIKE '%قبل ما اليوم يخلص%' OR text LIKE '%ملخص برنامج طيران تحسين الكامل%' OR text LIKE '%خطوات الحجز في برنامج طيران تحسين%' OR text LIKE '%تم استلام رقم حضرتك%')").fetchone()[0]
check(f"workflow messages logged in chat history ({n_logged})", n_logged == 7)

conn.close()
print("\n===== RESULT =====")
if failures:
    print("FAILED:", failures)
    sys.exit(1)
print("ALL TESTS PASSED ✅")
shutil.rmtree(TMP, ignore_errors=True)
