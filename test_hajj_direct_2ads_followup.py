# -*- coding: utf-8 -*-
"""
اختبار شامل لسير عمل hajj_direct_2ads_followup باستخدام قاعدة بيانات مؤقتة ومُرسِل وهمي.
لا يُرسل أي رسالة حقيقية ولا يلمس قاعدة البيانات الحقيقية (FTS_DATA_DIR مؤقت).
"""
import os
import sys
import json
import tempfile
import importlib.util
from datetime import datetime, timedelta

TMP = tempfile.mkdtemp(prefix="hajj_direct_test_")
os.environ["FTS_DATA_DIR"] = TMP

# استيراد chat_db بعد ضبط مسار البيانات المؤقت
import chat_db
chat_db.init_db()

import sqlite3
from fts_paths import get_data_path

DB = get_data_path("chat_history.db")
ADS = ["120248934377370757", "120248934520430757"]

# تهيئة الأعمدة المطلوبة (init_db ينشئ مخططاً أساسياً، وبقية الأعمدة تُضاف بالترحيل)
_NEEDED_COLS = {
    "conversations": {
        "is_closed": "INTEGER DEFAULT 0",
        "sales_inbox": "INTEGER DEFAULT 0",
        "auto_reply_hold_until": "TIMESTAMP",
        "customer_phone": "TEXT",
        "facebook_ad_id": "TEXT",
        "is_deleted": "INTEGER DEFAULT 0",
    },
}
_conn = sqlite3.connect(DB, timeout=15)
for tbl, cols in _NEEDED_COLS.items():
    have = [r[1] for r in _conn.execute(f"PRAGMA table_info({tbl})").fetchall()]
    for col, decl in cols.items():
        if col not in have:
            _conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {decl}")
_conn.commit()
_conn.close()


def now_cairo():
    return datetime.fromisoformat(chat_db.get_cairo_time())


def iso(dt):
    return dt.isoformat()


def add_conv(chat_id, ad, hours_ago_last_msg, source="Facebook", location="Religious",
             needs_help=0, is_closed=0, sales_inbox=0, sender=None):
    conn = sqlite3.connect(DB, timeout=15)
    c = conn.cursor()
    c.execute(
        """INSERT OR REPLACE INTO conversations
           (chat_id, source, sender_identifier, contact_name, location, last_message_time,
            needs_help, is_closed, sales_inbox, facebook_ad_id, is_deleted)
           VALUES (?,?,?,?,?,?,?,?,?,?,0)""",
        (chat_id, source, sender or chat_id, "Test " + chat_id, location,
         iso(now_cairo() - timedelta(hours=hours_ago_last_msg)), needs_help, is_closed,
         sales_inbox, ad),
    )
    conn.commit()
    conn.close()


def add_msg(chat_id, sender_type, text, hours_ago, source="Facebook"):
    conn = sqlite3.connect(DB, timeout=15)
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (msg_id, chat_id, sender_type, text, timestamp, status, source) VALUES (?,?,?,?,?,?,?)",
        (f"{chat_id}-{sender_type}-{hours_ago}", chat_id, sender_type, text,
         iso(now_cairo() - timedelta(hours=hours_ago)), "sent", source),
    )
    conn.commit()
    conn.close()


def add_conv_abs(chat_id, ad, last_dt, source="Facebook", location="Religious"):
    conn = sqlite3.connect(DB, timeout=15)
    c = conn.cursor()
    c.execute(
        """INSERT OR REPLACE INTO conversations
           (chat_id, source, sender_identifier, contact_name, location, last_message_time,
            needs_help, is_closed, sales_inbox, facebook_ad_id, is_deleted)
           VALUES (?,?,?,?,?,?,0,0,0,?,0)""",
        (chat_id, source, chat_id, "Test " + chat_id, location, last_dt.isoformat(), ad),
    )
    conn.commit()
    conn.close()


def add_msg_abs(chat_id, sender_type, text, dt, source="Facebook"):
    conn = sqlite3.connect(DB, timeout=15)
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (msg_id, chat_id, sender_type, text, timestamp, status, source) VALUES (?,?,?,?,?,?,?)",
        (f"{chat_id}-{sender_type}-abs-{dt.timestamp()}", chat_id, sender_type, text,
         dt.isoformat(), "sent", source),
    )
    conn.commit()
    conn.close()


class MockAgent:
    def __init__(self):
        self.sent = []      # (channel, sender, text)
    def send_facebook_message(self, sid, text):
        self.sent.append(("Facebook", sid, text))
        return True, "ok"
    def send_whatsapp_message(self, sid, text=None, location=None, receiving_phone_id=None):
        self.sent.append(("WhatsApp", sid, text))
        return True, "ok"


def load_module():
    # اسم موديول فريد حتى لا يتعارض مع الاستيراد الحقيقي
    spec = importlib.util.spec_from_file_location(
        "wf_test_direct", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "workflows", "hajj_direct_2ads_followup.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def reset_state(m):
    if os.path.exists(m.STATE_FILE):
        os.remove(m.STATE_FILE)


def clear_db():
    conn = sqlite3.connect(DB, timeout=15)
    conn.execute("DELETE FROM conversations")
    conn.execute("DELETE FROM messages")
    conn.commit()
    conn.close()


def fresh(m):
    clear_db()
    reset_state(m)


def main():
    m = load_module()
    failures = []

    def check(name, cond, extra=""):
        print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra else ""))
        if not cond:
            failures.append(name)

    # ================= سيناريو 1: 4 ساعات → الرسالة ١ =================
    fresh(m)
    add_conv("c1", ADS[0], 4.0)
    add_msg("c1", "customer", "عايز تفاصيل الحج المباشر", 4.0)
    add_msg("c1", "agent", "شرح برنامج الحج المباشر ...", 3.5)
    agent = MockAgent()
    r = m.run(agent, {})
    check("stage1 sent at 4h", any("فاضل معانا آخر ١٠ أماكن" in t for _, _, t in agent.sent), r)
    check("only one message sent (c1)", len(agent.sent) == 1, len(agent.sent))

    # ================= سيناريو 2: 12 ساعة → الرسالة ٢ =================
    fresh(m)
    add_conv("c2", ADS[0], 12.0)
    add_msg("c2", "customer", "تفاصيل من فضلك", 12.0)
    add_msg("c2", "agent", "شرح برنامج الحج المباشر ...", 11.0)
    agent = MockAgent()
    m.run(agent, {})
    check("stage2 sent at 12h", any("تأشيرات الحج المباشر" in t for _, _, t in agent.sent), agent.sent)

    # ================= سيناريو 3: 22 ساعة → الرسالة ٣ =================
    fresh(m)
    add_conv("c3", ADS[0], 22.0)
    add_msg("c3", "customer", "تفاصيل", 22.0)
    add_msg("c3", "agent", "شرح ...", 21.5)
    agent = MockAgent()
    m.run(agent, {})
    check("stage3 sent at 22h", any("فاضل معانا ١٠ أماكن بس" in t for _, _, t in agent.sent), agent.sent)

    # ================= سيناريو 4: 25 ساعة → لا إرسال =================
    fresh(m)
    add_conv("c4", ADS[0], 25.0)
    add_msg("c4", "customer", "تفاصيل", 25.0)
    add_msg("c4", "agent", "شرح ...", 24.5)
    agent = MockAgent()
    m.run(agent, {})
    check("no send after 24h", len(agent.sent) == 0, agent.sent)

    # ================= سيناريو 5: العميل رد → إيقاف بدون رسالة =================
    fresh(m)
    add_conv("c5", ADS[0], 1.0)
    add_msg("c5", "customer", "تفاصيل", 6.0)
    add_msg("c5", "agent", "شرح ...", 5.0)
    add_msg("c5", "customer", "تمام", 1.0)
    add_msg("c5", "agent", "رد على العميل", 0.5)
    agent = MockAgent()
    m.run(agent, {})
    check("customer reply stops sequence (no follow-up)", len(agent.sent) == 0, agent.sent)
    st = json.load(open(m.STATE_FILE, encoding="utf-8"))["chats"]["c5"]
    check("c5 marked stopped", st.get("stopped") is True, st.get("stopped_reason"))

    # ================= سيناريو 6: العميل أرسل رقم → تأكيد + تحويل =================
    fresh(m)
    add_conv("c6", ADS[0], 1.0)
    add_msg("c6", "customer", "تفاصيل", 6.0)
    add_msg("c6", "agent", "شرح ...", 5.0)
    add_msg("c6", "customer", "01012345678", 1.0)
    agent = MockAgent()
    m.run(agent, {})
    check("phone confirm sent", any("وصلني رقم حضرتك" in t for _, _, t in agent.sent), agent.sent)
    st = json.load(open(m.STATE_FILE, encoding="utf-8"))["chats"]["c6"]
    check("c6 transferred", st.get("transferred") is True, st.get("stopped_reason"))
    conv = chat_db.get_conversation_info("c6")
    check("c6 needs_help set", int((conv or {}).get("needs_help") or 0) == 1, conv)

    # ================= سيناريو 7: "السنة دي مش مناسبة" → tag السنة الجاية =================
    fresh(m)
    add_conv("c7", ADS[0], 1.0)
    add_msg("c7", "customer", "تفاصيل", 6.0)
    add_msg("c7", "agent", "شرح ...", 5.0)
    add_msg("c7", "customer", "السنة دي مش مناسبة", 1.0)
    agent = MockAgent()
    m.run(agent, {})
    check("next-year msg sent", any("مش مناسبة" in t or "السنة الجاية" in t for _, _, t in agent.sent), agent.sent)
    st = json.load(open(m.STATE_FILE, encoding="utf-8"))["chats"]["c7"]
    check("c7 next year interested", st.get("next_year_interested") is True, st.get("stopped_reason"))

    # ================= سيناريو 8: إعلان غير مستهدف → لا شيء =================
    fresh(m)
    add_conv("c8", "999999999999999999", 4.0)
    add_msg("c8", "customer", "تفاصيل", 4.0)
    add_msg("c8", "agent", "شرح ...", 3.5)
    agent = MockAgent()
    m.run(agent, {})
    check("other ad ignored", len(agent.sent) == 0, agent.sent)

    # ================= سيناريو 9: needs_help=1 → لا إرسال =================
    fresh(m)
    add_conv("c9", ADS[0], 5.0, needs_help=1)
    add_msg("c9", "customer", "تفاصيل", 5.0)
    add_msg("c9", "agent", "شرح ...", 4.5)
    agent = MockAgent()
    m.run(agent, {})
    check("needs_help skips send", len(agent.sent) == 0, agent.sent)

    # ================= سيناريو 10: sales_inbox=1 → لا إرسال =================
    fresh(m)
    add_conv("c10", ADS[0], 5.0, sales_inbox=1)
    add_msg("c10", "customer", "تفاصيل", 5.0)
    add_msg("c10", "agent", "شرح ...", 4.5)
    agent = MockAgent()
    m.run(agent, {})
    check("sales_inbox skips send", len(agent.sent) == 0, agent.sent)

    # ================= سيناريو 11: بعد ٣٠ سبتمبر → لا إرسال نهائياً =================
    fresh(m)
    mocked_now = datetime(2026, 10, 1, 10, 0, 0)
    add_conv_abs("c11", ADS[0], mocked_now - timedelta(hours=5))
    add_msg_abs("c11", "customer", "تفاصيل", mocked_now - timedelta(hours=5))
    add_msg_abs("c11", "agent", "شرح ...", mocked_now - timedelta(hours=4.5))
    real_now = m._now
    m._now = lambda: mocked_now
    agent = MockAgent()
    m.run(agent, {})
    m._now = real_now
    check("deadline (after Sep 30) blocks send", len(agent.sent) == 0, agent.sent)
    st = json.load(open(m.STATE_FILE, encoding="utf-8"))["chats"]["c11"]
    check("c11 sequence_done after deadline", st.get("sequence_done") is True, st)

    # ================= سيناريو 12: اختيار برنامج "١" =================
    fresh(m)
    add_conv("c12", ADS[0], 1.0)
    add_msg("c12", "customer", "تفاصيل", 6.0)
    add_msg("c12", "agent", "شرح ...", 5.0)
    add_msg("c12", "customer", "١", 1.0)
    agent = MockAgent()
    m.run(agent, {})
    check("program choice handled", any("رقم تليفونك" in t for _, _, t in agent.sent), agent.sent)
    st = json.load(open(m.STATE_FILE, encoding="utf-8"))["chats"]["c12"]
    check("c12 chosen program recorded", st.get("chosen_program") == "الطيران الاقتصادي", st.get("chosen_program"))

    print("\n==== RESULT ====")
    if failures:
        print(f"{len(failures)} FAILED:", failures)
        sys.exit(1)
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
