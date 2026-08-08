# -*- coding: utf-8 -*-
"""
اختبار معزول (Isolated) لـ workflows/religious_umrah_10day_followup.py
=====================================================================
كل مجموعة سيناريوهات تعمل في بيئة معزولة خاصة بها (قاعدة بيانات مؤقتة جديدة +
ملف حالة جديد + ساعة قاهرة قابلة للتحكم) حتى لا يحدث تلوث بين السيناريوهات.

السيناريوهات:
  1) التسلسل العادي: M1 بعد 60 دقيقة → M2 بعد 7 ساعات → M3 بعد 22 ساعة
     + لا تكرار + sequence_done بعد إغلاق نافذة 24 ساعة.
  2) محادثة قديمة صامتة (3 ساعات) → M1 تُرسل في أول دورة.
  3) أي رد من العميل → إيقاف السلسلة نهائياً (لا M2 ولا M3).
  4) رقم تليفون في أول رسالة → رد تأكيد + تسجيل customer_phone + needs_help=1.
  5) رقم تليفون أثناء السلسلة → رد تأكيد + تسجيل + إيقاف (لا M2).
  6) طلب عدم التواصل → اعتذار قصير + إيقاف دائم يمتد لمحادثة جديدة من نفس المرسل.
  7) نية حجز → تحويل لمسار الحجز (needs_help=1) بدون رسالة نصية للعميل.
  8) قاعدة الليل: M1 مستحقة 02:10 → تأجيل؛ تُرسل 08:05 (بلا تخطي مرحلة).
  9) استثناء الليل: M3 مستحقة 05:30 ونافذة 24 ساعة تُغلق 07:30 (قبل 8) → فوراً.
  10) M3 ليلاً والنافذة تُغلق بعد 8 صباحاً → تأجيل ثم إرسال 08:05.
  11) نافذة 24 ساعة مغلقة → لا إرسال إطلاقاً.
  12) محادثة من إعلان آخر → لا تُلمس.
  13) محادثة needs_help=1 (موظف بشري) → تخطي.
  14) تكرار received/sent → رسالة التأكيد مرة واحدة فقط.
  15) اختبارات الوحدة (توقيت/مراحل/أرقام/كلمات).
"""
import os
import sys
import json
import sqlite3
import tempfile
import importlib
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import chat_db  # noqa: E402

PASS = 0
FAIL = 0
GROUP = ""


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {extra}")


def section(title):
    global GROUP
    GROUP = title
    print(f"== {title} ==")


# ===== بيئة معزولة لكل مجموعة =====
class Env:
    def __init__(self, base_time: datetime):
        self.tmpdir = tempfile.mkdtemp(prefix="umrah10_env_")
        self.db_file = os.path.join(self.tmpdir, "test_chat.db")
        self.state_file = os.path.join(self.tmpdir, "test_state.json")
        self.now = base_time
        self.conn = self._make_db(self.db_file)
        self.agent = MockAgent()
        WF.DB_FILE = self.db_file
        WF.STATE_FILE = self.state_file
        WF._now = lambda: self.now
        chat_db.DB_FILE = self.db_file

    @staticmethod
    def _make_db(path):
        conn = sqlite3.connect(path, timeout=30)
        c = conn.cursor()
        c.execute("""CREATE TABLE conversations (
            chat_id TEXT PRIMARY KEY, source TEXT, sender_identifier TEXT, contact_name TEXT,
            last_message_time TIMESTAMP, unread_count INTEGER DEFAULT 0, location TEXT,
            needs_help INTEGER DEFAULT 0, receiving_phone_id TEXT, facebook_ad_id TEXT,
            is_deleted INTEGER DEFAULT 0, is_closed INTEGER DEFAULT 0,
            auto_reply_hold_until TIMESTAMP, customer_phone TEXT)""")
        c.execute("""CREATE TABLE messages (
            msg_id TEXT PRIMARY KEY, chat_id TEXT, sender_type TEXT, text TEXT,
            timestamp TIMESTAMP, status TEXT, source TEXT, external_message_id TEXT)""")
        c.execute("""CREATE TABLE sales_customer_state (
            chat_id TEXT PRIMARY KEY, tags TEXT, priority TEXT, lead_status TEXT,
            sales_notes TEXT, updated_at TEXT, created_at TEXT)""")
        conn.commit()
        return conn

    def add_conv(self, chat_id, sender, ad_id="120248068201650757", last_ts=None, needs_help=0):
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO conversations (chat_id, source, sender_identifier, contact_name, last_message_time, location, facebook_ad_id, needs_help) "
            "VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(chat_id) DO UPDATE SET last_message_time = excluded.last_message_time",
            (chat_id, "Facebook", sender, "", last_ts, "Religious", ad_id, needs_help),
        )
        self.conn.commit()

    def add_msg(self, chat_id, sender_type, text, ts, status="received"):
        import uuid
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO messages (msg_id, chat_id, sender_type, text, timestamp, status, source) VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), chat_id, sender_type, text, ts, status, "Facebook"),
        )
        self.conn.commit()

    def run(self, dry=False):
        return WF.run(self.agent, {"dry_run": dry})

    def state(self):
        with open(self.state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def conv(self, chat_id, col):
        return self.conn.execute(f"SELECT {col} FROM conversations WHERE chat_id=?", (chat_id,)).fetchone()

    def sales(self, chat_id):
        return self.conn.execute("SELECT tags FROM sales_customer_state WHERE chat_id=?", (chat_id,)).fetchone()


class MockAgent:
    def __init__(self):
        self.sent_fb = []
        self.sent_wa = []

    def send_facebook_message(self, recipient_psid, text=None, **kw):
        self.sent_fb.append({"to": recipient_psid, "text": text})
        return True, "ok"

    def send_whatsapp_message(self, recipient_phone, text=None, **kw):
        self.sent_wa.append({"to": recipient_phone, "text": text})
        return True, "ok"


def _to(env, psid):
    return [m for m in env.agent.sent_fb if m["to"] == psid]


def main():
    global WF
    spec = importlib.util.spec_from_file_location(
        "umrah_relaxed_10day_followup_test", os.path.join(BASE, "workflows", "religious_umrah_10day_followup.py")
    )
    WF = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(WF)

    # ---------------------------------------------------------------
    section("1) التسلسل العادي M1 → M2 → M3 + نافذة 24 ساعة")
    base = datetime(2026, 8, 2, 12, 0, 0)
    env = Env(base)
    c1 = "c1"
    t0 = base - timedelta(minutes=30)
    env.add_conv(c1, "psid_1", last_ts=t0.isoformat())
    env.add_msg(c1, "customer", "عاوز اعرف التفاصيل والمواعيد", t0.isoformat())
    env.add_msg(c1, "agent", "أهلًا بحضرتك 🕋 اتفضل تفاصيل البرنامج", (t0 + timedelta(minutes=2)).isoformat())
    env.run()
    check("لا تُرسل M1 قبل 60 دقيقة", len(_to(env, "psid_1")) == 0)

    env.now = base + timedelta(minutes=70)
    env.run()
    m1 = [m for m in _to(env, "psid_1") if "حضرتك لسه معانا؟ 🕋" in m["text"]]
    check("M1 بعد 60 دقيقة من آخر رسالة", len(m1) == 1)
    check("نص M1 مطابق حرفياً", m1 and m1[0]["text"] == WF.MSG_STAGE1)

    env.now = base + timedelta(hours=8)
    env.run()
    m2 = [m for m in _to(env, "psid_1") if "غالبًا حضرتك بتفكر" in m["text"]]
    check("M2 بعد 7 ساعات من آخر رسالة عميل", len(m2) == 1)
    check("نص M2 مطابق حرفياً", m2 and m2[0]["text"] == WF.MSG_STAGE2)

    env.now = base + timedelta(hours=22, minutes=30)
    env.run()
    m3 = [m for m in _to(env, "psid_1") if "آخر رسالة من طرفنا وعدًا 🤝" in m["text"]]
    check("M3 بعد 22 ساعة (قبل إغلاق النافذة)", len(m3) == 1)
    check("نص M3 مطابق حرفياً", m3 and m3[0]["text"] == WF.MSG_STAGE3)

    env.now = base + timedelta(hours=24, minutes=10)
    env.run()
    st = env.state()
    e1 = st["chats"].get(c1, {})
    check("sequence_done بعد إغلاق النافذة",
          e1.get("stopped") is True and e1.get("stop_reason") == "window_closed", str(e1))
    before = len(env.agent.sent_fb)
    env.run()
    check("لا تكرار بعد الاكتمال", len(env.agent.sent_fb) == before)

    # ---------------------------------------------------------------
    section("2) محادثة قديمة صامتة (3 ساعات) → M1 في أول دورة")
    base = datetime(2026, 8, 2, 12, 0, 0)
    env = Env(base)
    c2 = "c2"
    t2 = base - timedelta(hours=3)
    env.add_conv(c2, "psid_2", last_ts=t2.isoformat())
    env.add_msg(c2, "customer", "عايز أعرف تفاصيل البرنامج", t2.isoformat())
    env.run()
    m1old = [m for m in _to(env, "psid_2") if "حضرتك لسه معانا؟ 🕋" in m["text"]]
    check("M1 تُرسل فوراً لمحادثة صامتة منذ 3 ساعات", len(m1old) == 1)

    # ---------------------------------------------------------------
    section("3) أي رد من العميل → إيقاف السلسلة نهائياً")
    base = datetime(2026, 8, 2, 12, 0, 0)
    env = Env(base)
    c3 = "c3"
    t3 = base - timedelta(hours=1, minutes=10)
    env.add_conv(c3, "psid_3", last_ts=t3.isoformat())
    env.add_msg(c3, "customer", "عايز أعرف التفاصيل", t3.isoformat())
    env.run()  # تهيئة + M1 (مرّ أكثر من 60 دقيقة)
    check("M1 أُرسلت أولاً", len([m for m in _to(env, "psid_3") if "حضرتك لسه معانا؟ 🕋" in m["text"]]) == 1)
    env.now = base + timedelta(hours=1, minutes=20)
    env.add_msg(c3, "customer", "تمام شكراً", env.now.isoformat())
    env.run()
    st = env.state()
    e3 = st["chats"].get(c3, {})
    check("السلسلة أُوقفت (customer_replied)", e3.get("stopped") is True and e3.get("stop_reason") == "customer_replied", str(e3))
    env.now = base + timedelta(hours=9)
    env.run()
    m2c = [m for m in _to(env, "psid_3") if "غالبًا حضرتك" in m["text"]]
    check("لا M2 بعد رد العميل", len(m2c) == 0)

    # ---------------------------------------------------------------
    section("4) رقم تليفون في أول رسالة — بلا رسالة تأكيد (تحديث المدير)")
    base = datetime(2026, 8, 2, 12, 0, 0)
    env = Env(base)
    c4 = "c4"
    t4 = base - timedelta(minutes=10)
    env.add_conv(c4, "psid_4", last_ts=t4.isoformat())
    env.add_msg(c4, "customer", "رقمي 01012345678 كلموني", t4.isoformat())
    env.run()
    conf = [m for m in _to(env, "psid_4") if "وصلنا رقم حضرتك ✅" in m["text"]]
    check("لا تُرسل رسالة تأكيد الرقم للعميل (تحديث المدير)", len(conf) == 0, str(len(conf)))
    check("لا أي رسالة للعميل إطلاقاً", len(_to(env, "psid_4")) == 0)
    row = env.conv(c4, "customer_phone, needs_help")
    check("الرقم سُجّل في customer_phone", row and row[0] == "01012345678", str(row))
    check("needs_help=1 (إشعار للفريق البشري)", row and row[1] == 1, str(row))
    st = env.state()
    check("السلسلة أُوقفت للرقم", st["chats"][c4].get("stopped") is True and str(st["chats"][c4].get("stop_reason", "")).startswith("phone_received"), str(st["chats"][c4]))
    env.now = base + timedelta(hours=8)
    env.run()
    check("لا متابعات بعد تسجيل الرقم", len(_to(env, "psid_4")) == 0)

    # ---------------------------------------------------------------
    section("5) رقم تليفون أثناء السلسلة — بلا رسالة تأكيد")
    base = datetime(2026, 8, 2, 12, 0, 0)
    env = Env(base)
    c5 = "c5"
    t5 = base - timedelta(hours=2)
    env.add_conv(c5, "psid_5", last_ts=t5.isoformat())
    env.add_msg(c5, "customer", "عايز أعرف أسعار البرنامج", t5.isoformat())
    env.run()  # M1
    env.now = base + timedelta(hours=2, minutes=30)
    env.add_msg(c5, "customer", "دى 01288427370", env.now.isoformat())
    env.run()
    conf5 = [m for m in _to(env, "psid_5") if "وصلنا رقم حضرتك ✅" in m["text"]]
    check("لا رسالة تأكيد الرقم أثناء السلسلة", len(conf5) == 0, str(len(conf5)))
    row5 = env.conv(c5, "customer_phone, needs_help")
    check("الرقم سُجّل + needs_help=1", row5 and row5[0] == "01288427370" and row5[1] == 1, str(row5))
    st5 = env.state()
    check("السلسلة أُوقفت للرقم", st5["chats"][c5].get("stopped") is True, str(st5["chats"][c5].get("stopped")))
    env.now = base + timedelta(hours=8, minutes=30)
    env.run()
    m2x = [m for m in _to(env, "psid_5") if "غالبًا حضرتك" in m["text"]]
    check("لا M2 بعد تسجيل الرقم", len(m2x) == 0)

    # ---------------------------------------------------------------
    section("6) طلب عدم التواصل → إيقاف دائم حتى لمحادثة جديدة")
    base = datetime(2026, 8, 2, 12, 0, 0)
    env = Env(base)
    c6 = "c6"
    t6 = base - timedelta(minutes=5)
    env.add_conv(c6, "psid_6", last_ts=t6.isoformat())
    env.add_msg(c6, "customer", "متبعتليش حاجة تاني شكراً", t6.isoformat())
    env.run()
    ap = [m for m in _to(env, "psid_6") if "آسفين" in m["text"]]
    check("اعتذار لطيف في رسالة واحدة", len(ap) == 1)
    st = env.state()
    check("opt-out سُجّل على مستوى المرسل", "psid_6" in st.get("opted_out_senders", {}))
    check("opt-out سُجّل على مستوى المحادثة", st["chats"][c6].get("opted_out") is True)
    # محادثة جديدة من نفس المرسل بعد ساعة
    c6b = "c6b"
    t6b = base + timedelta(hours=1)
    env.add_conv(c6b, "psid_6", last_ts=t6b.isoformat())
    env.add_msg(c6b, "customer", "تفاصيل البرنامج من فضلك", t6b.isoformat())
    env.now = t6b + timedelta(hours=2)
    before6 = len(env.agent.sent_fb)
    env.run()
    check("لا متابعات للمحادثة الجديدة من مرسل مُوقَف", len(env.agent.sent_fb) == before6)

    # ---------------------------------------------------------------
    section("7) نية حجز → تحويل لمسار الحجز")
    base = datetime(2026, 8, 2, 12, 0, 0)
    env = Env(base)
    c7 = "c7"
    t7 = base - timedelta(minutes=30)
    env.add_conv(c7, "psid_7", last_ts=t7.isoformat())
    env.add_msg(c7, "customer", "عايز أحجز مكان دلوقتي", t7.isoformat())
    env.run()
    row7 = env.conv(c7, "needs_help")
    st = env.state()
    check("needs_help=1 (تحويل لمسار الحجز)", row7 and row7[0] == 1, str(row7))
    check("السلسلة أُوقفت (booking_intent)",
          st["chats"][c7].get("stopped") is True and st["chats"][c7].get("stop_reason") == "booking_intent")
    check("لا رسالة ترويجية أُرسلت للعميل", len(_to(env, "psid_7")) == 0)

    # ---------------------------------------------------------------
    section("8) قاعدة الليل: تأجيل M1 حتى 8 صباحاً (بلا تخطي مرحلة)")
    base = datetime(2026, 8, 2, 2, 10)
    env = Env(base)
    c8 = "c8"
    t8 = base - timedelta(hours=1, minutes=10)  # آخر رسالة 01:00
    env.add_conv(c8, "psid_8", last_ts=t8.isoformat())
    env.add_msg(c8, "customer", "عايز أعرف التفاصيل", t8.isoformat())
    env.run()
    check("لا إرسال أثناء ساعات الهدوء (02:10)", len(_to(env, "psid_8")) == 0)
    env.now = datetime(2026, 8, 2, 8, 5)
    env.run()
    m1n = [m for m in _to(env, "psid_8") if "حضرتك لسه معانا؟ 🕋" in m["text"]]
    m2n = [m for m in _to(env, "psid_8") if "غالبًا حضرتك" in m["text"]]
    check("M1 أُرسلت أول دورة بعد 8 صباحاً", len(m1n) == 1)
    check("لا تخطي مرحلة: M2 لم تُرسل قبل M1", len(m2n) == 0)

    # ---------------------------------------------------------------
    section("9) استثناء الليل: M3 ونافذة تُغلق قبل 8 صباحاً → إرسال فوري")
    base = datetime(2026, 8, 1, 7, 30)
    env = Env(base)
    c9 = "c9"
    env.add_conv(c9, "psid_9", last_ts=base.isoformat())
    env.add_msg(c9, "customer", "عايز أعرف التفاصيل", base.isoformat())
    env.now = datetime(2026, 8, 1, 8, 40)
    env.run()  # M1
    env.now = datetime(2026, 8, 1, 15, 30)
    env.run()  # M2
    env.now = datetime(2026, 8, 2, 5, 30)  # M3 مستحقة ليلاً — النافذة تغلق 07:30
    env.run()
    m3n = [m for m in _to(env, "psid_9") if "آخر رسالة من طرفنا وعدًا 🤝" in m["text"]]
    check("M3 أُرسلت ليلاً (النافذة ستُغلق قبل 8 صباحاً)", len(m3n) == 1)

    # ---------------------------------------------------------------
    section("10) M3 ليلاً والنافذة تُغلق بعد 8 صباحاً → تأجيل ثم إرسال")
    base = datetime(2026, 8, 1, 8, 30)
    env = Env(base)
    c10 = "c10"
    env.add_conv(c10, "psid_10", last_ts=base.isoformat())
    env.add_msg(c10, "customer", "عايز أعرف مواعيد الرحلات", base.isoformat())
    env.now = datetime(2026, 8, 1, 9, 40)
    env.run()  # M1
    env.now = datetime(2026, 8, 1, 16, 0)
    env.run()  # M2
    env.now = datetime(2026, 8, 2, 6, 30)  # M3 مستحقة ليلاً — النافذة تغلق 08:30
    env.run()
    m3night = [m for m in _to(env, "psid_10") if "آخر رسالة من طرفنا وعدًا 🤝" in m["text"]]
    check("لا M3 ليلاً عندما تُغلق النافذة بعد 8 صباحاً", len(m3night) == 0)
    env.now = datetime(2026, 8, 2, 8, 5)  # النافذة ما زالت مفتوحة (23.5 ساعة)
    env.run()
    m3mor = [m for m in _to(env, "psid_10") if "آخر رسالة من طرفنا وعدًا 🤝" in m["text"]]
    check("M3 أُرسلت أول دورة بعد 8 صباحاً", len(m3mor) == 1)

    # ---------------------------------------------------------------
    section("11) نافذة 24 ساعة مغلقة → لا إرسال")
    base = datetime(2026, 8, 2, 12, 0, 0)
    env = Env(base)
    c11 = "c11"
    t11 = base - timedelta(hours=25)
    env.add_conv(c11, "psid_11", last_ts=t11.isoformat())
    env.add_msg(c11, "customer", "أنا مهتم بالبرنامج", t11.isoformat())
    env.run()
    check("لا إرسال لمحادثة خارج نافذة الـ 24 ساعة", len(_to(env, "psid_11")) == 0)

    # ---------------------------------------------------------------
    section("12) محادثة من إعلان آخر → لا تُلمس")
    base = datetime(2026, 8, 2, 12, 0, 0)
    env = Env(base)
    c12 = "c12"
    t12 = base - timedelta(hours=3)
    env.add_conv(c12, "psid_12", ad_id="999999999999999999", last_ts=t12.isoformat())
    env.add_msg(c12, "customer", "تفاصيل برنامج تاني", t12.isoformat())
    env.run()
    check("لا أي إرسال لمحادثة من إعلان آخر", len(env.agent.sent_fb) == 0)
    st = env.state()
    check("ولا سجل حالة لمحادثة إعلان آخر", c12 not in st.get("chats", {}))

    # ---------------------------------------------------------------
    section("13) تدخّل موظف بشري (needs_help=1) → تخطي")
    base = datetime(2026, 8, 2, 12, 0, 0)
    env = Env(base)
    c13 = "c13"
    t13 = base - timedelta(hours=3)
    env.add_conv(c13, "psid_13", last_ts=t13.isoformat(), needs_help=1)
    env.add_msg(c13, "customer", "عايز أعرف التفاصيل", t13.isoformat())
    env.run()
    check("لا إرسال لمحادثة متدخل فيها موظف بشري", len(env.agent.sent_fb) == 0)

    # ---------------------------------------------------------------
    section("14) تكرار received/sent → لا رسالة تأكيد إطلاقاً (تحديث المدير)")
    base = datetime(2026, 8, 2, 12, 0, 0)
    env = Env(base)
    c14 = "c14"
    t14 = base - timedelta(minutes=5)
    env.add_conv(c14, "psid_14", last_ts=(t14 + timedelta(seconds=1)).isoformat())
    env.add_msg(c14, "customer", "رقمي 01512345678", t14.isoformat(), status="received")
    env.add_msg(c14, "customer", "رقمي 01512345678", (t14 + timedelta(milliseconds=500)).isoformat(), status="sent")
    env.run()
    env.run()
    conf14 = [m for m in _to(env, "psid_14") if "وصلنا رقم حضرتك ✅" in m["text"]]
    check("لا أي رسالة تأكيد رغم التكرار", len(conf14) == 0, str(len(conf14)))
    row14 = env.conv(c14, "customer_phone")
    check("الرقم سُجّل مرة واحدة", row14 and row14[0] == "01512345678", str(row14))

    # ---------------------------------------------------------------
    section("15) اختبارات الوحدة")
    now15 = datetime(2026, 8, 2, 12, 0, 0)
    # ساعات الهدوء: لا إرسال بين 12 منتصف الليل و 8 صباحاً
    check("نهاراً: الإرسال مسموح", not WF._in_quiet_hours(datetime(2026, 8, 2, 12, 0)))
    check("ليلاً M1: تأجيل", WF._in_quiet_hours(datetime(2026, 8, 2, 2, 0)))
    check("ليلاً M3 والنافذة تغلق 07:30 قبل 8:00: إرسال فوري",
          WF._window_closes_before_8am(datetime(2026, 8, 1, 7, 30), datetime(2026, 8, 2, 5, 30)) is True)
    check("ليلاً M3 والنافذة تغلق 08:30 بعد 8:00: تأجيل",
          WF._window_closes_before_8am(datetime(2026, 8, 1, 8, 30), datetime(2026, 8, 2, 6, 30)) is False)
    # _due_stage(entry, now, last_customer_ts, last_msg_ts) → 0/1/2/3
    e0 = {"highest_stage_sent": 0}
    check("قبل 60 دقيقة لا مرحلة",
          WF._due_stage(e0, now15, now15 - timedelta(minutes=30), now15 - timedelta(minutes=30)) == 0)
    e1s = {"highest_stage_sent": 1}
    check("بعد 7 ساعات من رسالة العميل → M2",
          WF._due_stage(e1s, now15, now15 - timedelta(hours=7, minutes=1), now15 - timedelta(hours=1)) == 2)
    e2s = {"highest_stage_sent": 2}
    check("بعد 22 ساعة → M3",
          WF._due_stage(e2s, now15, now15 - timedelta(hours=22, minutes=1), now15 - timedelta(hours=1)) == 3)
    check("لا تخطي: بدون M1 لا تُرسل M2 حتى لو مرّت 7 ساعات",
          WF._due_stage(e0, now15, now15 - timedelta(hours=7, minutes=1), now15 - timedelta(hours=10)) == 1)
    check("استخراج رقم مصري", WF._extract_phone("كلمني على 01012345678") == "01012345678")
    check("استخراج رقم دولي 20", WF._extract_phone("00201012345678") == "01012345678")
    check("لا رقم", WF._extract_phone("تمام شكراً") is None)
    check("opt-out: متبعتليش", WF._is_optout("متبعتليش حاجة تاني") is True)
    check("opt-out: stop", WF._is_optout("stop please") is True)
    check("ليس opt-out", WF._is_optout("تمام شكراً") is False)
    check("حجز: عايز أحجز", WF._is_booking_intent("عايز أحجز مكان") is True)
    check("حجز: إجراءات الحجز", WF._is_booking_intent("إجراءات الحجز إيه؟") is True)
    check("حجز: خطوات الحجز", WF._is_booking_intent("خطوات الحجز إيه؟") is True)
    check("حجز: حجزت", WF._is_booking_intent("أنا حجزت بالفعل") is True)
    check("ليس حجز: سعر البرنامج؟", WF._is_booking_intent("سعر البرنامج كام؟") is False)

    print()
    print(f"النتيجة النهائية: {PASS} ناجح / {FAIL} فاشل")
    if FAIL:
        sys.exit(1)


if __name__ == "__main__":
    main()
