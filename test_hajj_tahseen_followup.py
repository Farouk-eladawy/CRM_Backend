# -*- coding: utf-8 -*-
"""
اختبار معزول (Isolated) لـ workflows/hajj_tahseen_followup.py
=============================================================
ينشئ قاعدة بيانات مؤقتة + Agent وهمي + ساعة قاهرة قابلة للتحكم (عن طريق
استبدال wf._now)، ثم يختبر كل سيناريوهات الـ Workflow دون أي أثر على
قاعدة البيانات الحقيقية:

  1) التسلسل العادي: M1 بعد ساعتين → M2 بعد 8 → M3 بعد 21 + وسم no-response.
  2) الـ Lead الساخن (زرار "إزاي أحجز؟"): M1 بعد 45 دقيقة بمحتوى خطوات الحجز.
     — بما فيها محادثة أول رسالة فيها هي رسالة إحالة [Facebook Ad Referral].
  3) كلمة "ملخص" → إرسال الملخص وإعادة ضبط العداد (stage=0).
  4) كلمة "أحجز" → خطوات الحجز + تحويل لخدمة العملاء (needs_help=1).
  5) رقم موبايل → تسجيل + تحويل فوري كـ Lead ساخن (priority High + tag).
  6) طلب الإيقاف → إيقاف نهائي بلا أي رسائل.
  7) نافذة الـ 24 ساعة مغلقة → لا إرسال + tag لمن بدأ التسلسل.
  8) بداية متأخرة (> 8 ساعات) → لا يُرسل M1 (تُرسل المرحلة المستحقة فقط).
  9) محادثة من إعلان آخر → لا تُلمس نهائياً.
  10) منع الإرسال المزدوج عند تشغيلين متتاليين (ملف الحالة).
  11) الرد بميديا (صوت) → يعيد ضبط العداد ولا يُرسل follow-up قبل أوانه.
"""
import os
import sys
import json
import uuid
import sqlite3
import tempfile
import importlib
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import chat_db  # noqa: E402

# ===== ساعة قاهرة قابلة للتحكم =====
FAKE_NOW = datetime(2026, 8, 2, 12, 0, 0)


class MockAgent:
    """Agent وهمي يسجّل الإرسالات دون إرسال فعلي."""

    def __init__(self):
        self.sent_fb = []
        self.sent_wa = []

    def send_facebook_message(self, recipient_psid, text=None, **kw):
        self.sent_fb.append({"to": recipient_psid, "text": text})
        return True, "ok"

    def send_whatsapp_message(self, recipient_phone, text=None, **kw):
        self.sent_wa.append({"to": recipient_phone, "text": text})
        return True, "ok"


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


def _add_conv(conn, chat_id, sender, ad_id="120246971083710757", location="Religious",
              source="Facebook", last_ts=None):
    c = conn.cursor()
    c.execute(
        "INSERT INTO conversations (chat_id, source, sender_identifier, contact_name, last_message_time, location, facebook_ad_id, needs_help) "
        "VALUES (?,?,?,?,?,?,?,0) "
        "ON CONFLICT(chat_id) DO UPDATE SET last_message_time = excluded.last_message_time",
        (chat_id, source, sender, "", last_ts, location, ad_id),
    )
    conn.commit()


def _add_msg(conn, chat_id, sender_type, text, ts, status="received"):
    c = conn.cursor()
    mid = str(uuid.uuid4())
    c.execute(
        "INSERT INTO messages (msg_id, chat_id, sender_type, text, timestamp, status, source) VALUES (?,?,?,?,?,?,?)",
        (mid, chat_id, sender_type, text, ts, status, "Facebook"),
    )
    conn.commit()


def _run(agent, dry=False, limit=None):
    payload = {"dry_run": dry}
    if limit:
        payload["limit"] = limit
    return WF.run(agent, payload)


def _state():
    with open(WF.STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _sales(conn, chat_id):
    return conn.execute("SELECT tags, priority, lead_status FROM sales_customer_state WHERE chat_id=?", (chat_id,)).fetchone()


def _needs_help(conn, chat_id):
    return conn.execute("SELECT needs_help FROM conversations WHERE chat_id=?", (chat_id,)).fetchone()


PASS = 0
FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {extra}")


def main():
    global FAKE_NOW, PASS, FAIL, WF
    tmpdir = tempfile.mkdtemp(prefix="hajj_tahseen_test_")
    db_file = os.path.join(tmpdir, "test_chat.db")
    state_file = os.path.join(tmpdir, "test_state.json")

    # تحميل الوحدة النمطية وتوجيهها لقاعدة الاختبار + ساعة وهمية
    spec = importlib.util.spec_from_file_location(
        "hajj_tahseen_followup_test", os.path.join(BASE, "workflows", "hajj_tahseen_followup.py")
    )
    WF = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(WF)
    WF.DB_FILE = db_file
    WF.STATE_FILE = state_file
    WF._now = lambda: FAKE_NOW

    chat_db.DB_FILE = db_file  # تسجيل الرسائل في قاعدة الاختبار

    conn = _make_db(db_file)
    agent = MockAgent()
    now = FAKE_NOW

    # ---------------------------------------------------------------
    print("== 1) التسلسل العادي M1 → M2 → M3 + وسم no-response ==")
    agent.sent_fb.clear()
    c1 = "chat-normal-1"
    t0 = now - timedelta(hours=2, minutes=30)
    _add_conv(conn, c1, "psid_1", last_ts=t0.isoformat())
    _add_msg(conn, c1, "customer", "تفاصيل البرنامج", t0.isoformat())
    _run(agent)                       # تشغيل 1: تهيئة فقط
    _run(agent)                       # تشغيل 2: M1
    m1 = [m for m in agent.sent_fb if m["to"] == "psid_1" and "حضرتك لسه معانا؟ 🕋" in m["text"]]
    check("M1 أُرسلت بعد ساعتين", len(m1) == 1, str(len(m1)))
    check("نص M1 مطابق للتعليمات حرفياً", m1 and m1[0]["text"] == WF.MSG_STAGE1_NORMAL)

    FAKE_NOW = now + timedelta(hours=6)     # إجمالي 8.5 ساعة
    _run(agent)
    m2 = [m for m in agent.sent_fb if m["to"] == "psid_1" and "عارفين إن قرار الحج مش سهل" in m["text"]]
    check("M2 أُرسلت بعد 8 ساعات", len(m2) == 1)

    FAKE_NOW = now + timedelta(hours=19, minutes=5)  # إجمالي 21.5 ساعة
    _run(agent)
    m3 = [m for m in agent.sent_fb if m["to"] == "psid_1" and "قبل ما اليوم يخلص حابين نفكر حضرتك 📌" in m["text"]]
    check("M3 أُرسلت بعد 21 ساعة", len(m3) == 1)

    FAKE_NOW = now + timedelta(hours=24, minutes=10)  # إغلاق نافذة 24 ساعة
    _run(agent)
    st = _state()
    e1 = st["chats"].get(c1, {})
    check("الوسم no-response-hajj-tahseen طُبّق", e1.get("tagged") is True and e1.get("sequence_done") is True, str(e1))
    s1 = _sales(conn, c1)
    check("الوسم ظهر في sales_customer_state.tags", s1 and "no-response-hajj-tahseen" in (s1[0] or ""))

    n_before = len(agent.sent_fb)
    _run(agent)
    check("لا تكرار بعد الاكتمال", len(agent.sent_fb) == n_before)

    # ---------------------------------------------------------------
    print("== 2) الـ Lead الساخن (زرار إزاي أحجز؟) — مع رسالة إحالة أولاً ==")
    agent.sent_fb.clear()
    c2 = "chat-hot-1"
    base = FAKE_NOW
    t1 = base - timedelta(minutes=50)
    _add_conv(conn, c2, "psid_2", last_ts=t1.isoformat())
    _add_msg(conn, c2, "customer", "[Facebook Ad Referral] source=ADS type=OPEN_THREAD ad_id=120246971083710757", (t1 - timedelta(minutes=1)).isoformat())
    _add_msg(conn, c2, "customer", "إزاي أحجز؟", t1.isoformat())
    _run(agent)
    _run(agent)
    hot = [m for m in agent.sent_fb if m["to"] == "psid_2" and "خطوات الحجز" in m["text"]]
    check("الـ hot أُرسلت له M1 بعد 45 دقيقة بمحتوى الحجز", len(hot) == 1, str(len(hot)))
    st = _state()
    check("تم تصنيفه كـ hot_lead رغم رسالة الإحالة الأولى", st["chats"][c2].get("hot_lead") is True)

    c2b = "chat-hot-2"
    t1b = base - timedelta(minutes=20)
    _add_conv(conn, c2b, "psid_2b", last_ts=t1b.isoformat())
    _add_msg(conn, c2b, "customer", "إزاي أحجز؟", t1b.isoformat())
    _run(agent)
    _run(agent)
    check("قبل 45 دقيقة لا تُرسل M1 للساخن", not any(m["to"] == "psid_2b" for m in agent.sent_fb))

    # ---------------------------------------------------------------
    print("== 3) كلمة ملخص ==")
    agent.sent_fb.clear()
    c3 = "chat-summary-1"
    base = FAKE_NOW
    t2 = base - timedelta(hours=3)
    _add_conv(conn, c3, "psid_3", last_ts=t2.isoformat())
    _add_msg(conn, c3, "customer", "عايز أعرف تفاصيل البرنامج", t2.isoformat())
    _run(agent)
    _run(agent)  # M1
    t2b = FAKE_NOW + timedelta(minutes=10)
    _add_conv(conn, c3, "psid_3", last_ts=t2b.isoformat())
    _add_msg(conn, c3, "customer", "ملخص", t2b.isoformat())
    FAKE_NOW = t2b + timedelta(minutes=1)
    _run(agent)
    sm = [m for m in agent.sent_fb if m["to"] == "psid_3" and "ملخص برنامج طيران تحسين الكامل" in m["text"]]
    check("كلمة ملخص → أُرسل الملخص الكامل", len(sm) == 1)
    check("الملخص يحوي السعر ٢٥٠ ألف بدلًا من ٢٧٩ ألف", sm and "٢٥٠ ألف" in sm[0]["text"])
    st = _state()
    check("أُعيد ضبط العداد بعد الملخص (highest_stage_sent=0)", st["chats"][c3].get("highest_stage_sent") == 0)

    # ---------------------------------------------------------------
    print("== 4) كلمة أحجز ==")
    agent.sent_fb.clear()
    c4 = "chat-booking-1"
    base = FAKE_NOW
    t3 = base - timedelta(hours=2, minutes=30)
    _add_conv(conn, c4, "psid_4", last_ts=t3.isoformat())
    _add_msg(conn, c4, "customer", "مميزات طيران تحسين", t3.isoformat())
    _run(agent)
    _run(agent)  # M1
    t3b = FAKE_NOW + timedelta(minutes=5)
    _add_conv(conn, c4, "psid_4", last_ts=t3b.isoformat())
    _add_msg(conn, c4, "customer", "أحجز", t3b.isoformat())
    FAKE_NOW = t3b + timedelta(minutes=1)
    _run(agent)
    bk = [m for m in agent.sent_fb if m["to"] == "psid_4" and "خطوات الحجز في برنامج طيران تحسين" in m["text"]]
    check("كلمة أحجز → أُرسلت خطوات الحجز", len(bk) == 1)
    r4 = _needs_help(conn, c4)
    check("تحويل لموظف خدمة العملاء (needs_help=1)", r4 and r4[0] == 1)

    # ---------------------------------------------------------------
    print("== 5) رقم موبايل → Lead ساخن ==")
    agent.sent_fb.clear()
    c5 = "chat-phone-1"
    base = FAKE_NOW
    t4 = base - timedelta(hours=2, minutes=30)
    _add_conv(conn, c5, "psid_5", last_ts=t4.isoformat())
    _add_msg(conn, c5, "customer", "تفاصيل", t4.isoformat())
    _run(agent)
    _run(agent)  # M1
    t4b = FAKE_NOW + timedelta(minutes=5)
    _add_conv(conn, c5, "psid_5", last_ts=t4b.isoformat())
    _add_msg(conn, c5, "customer", "رقمي 01012345678 اتصلوا بيا", t4b.isoformat())
    FAKE_NOW = t4b + timedelta(minutes=1)
    _run(agent)
    ph = [m for m in agent.sent_fb if m["to"] == "psid_5" and "تم استلام رقم حضرتك" in m["text"]]
    check("رقم الموبايل → رسالة تأكيد التسجيل", len(ph) == 1)
    r5 = _needs_help(conn, c5)
    s5 = _sales(conn, c5)
    check("تحويل فوري لخدمة العملاء (needs_help=1)", r5 and r5[0] == 1)
    check("lead ساخن: priority + tag في sales_customer_state", s5 and (s5[1] == "High" or "hajj-tahseen-hot-lead" in (s5[0] or "")), str(s5))
    ph5 = conn.execute("SELECT customer_phone FROM conversations WHERE chat_id=?", (c5,)).fetchone()
    check("تم تسجيل رقم العميل في customer_phone", ph5 and ph5[0] == "01012345678")

    # ---------------------------------------------------------------
    print("== 6) طلب الإيقاف ==")
    agent.sent_fb.clear()
    c6 = "chat-stop-1"
    base = FAKE_NOW
    t5 = base - timedelta(hours=3)
    _add_conv(conn, c6, "psid_6", last_ts=t5.isoformat())
    _add_msg(conn, c6, "customer", "تفاصيل البرنامج", t5.isoformat())
    _run(agent)
    _run(agent)  # M1
    t5b = FAKE_NOW + timedelta(minutes=5)
    _add_conv(conn, c6, "psid_6", last_ts=t5b.isoformat())
    _add_msg(conn, c6, "customer", "ممنوع ترسل لي حاجة تاني", t5b.isoformat())
    FAKE_NOW = t5b + timedelta(minutes=1)
    n_before = len(agent.sent_fb)
    _run(agent)
    st = _state()
    e6 = st["chats"].get(c6, {})
    check("طلب الإيقاف → opted_out=True", e6.get("opted_out") is True)
    check("لا رسائل بعد طلب الإيقاف", not any(m["to"] == "psid_6" for m in agent.sent_fb[n_before:]))

    # ---------------------------------------------------------------
    print("== 7) نافذة 24 ساعة مغلقة (بداية قبل التشغيل بأكثر من 24 ساعة) ==")
    agent.sent_fb.clear()
    c7 = "chat-late-1"
    base = FAKE_NOW
    t6 = base - timedelta(hours=25)
    _add_conv(conn, c7, "psid_7", last_ts=t6.isoformat())
    _add_msg(conn, c7, "customer", "تفاصيل البرنامج", t6.isoformat())
    n_before = len(agent.sent_fb)
    _run(agent)
    check("لا إرسال لمحادثة تجاوزت 24 ساعة", not any(m["to"] == "psid_7" for m in agent.sent_fb))

    # ---------------------------------------------------------------
    print("== 8) بداية متأخرة (10 ساعات) → تُرسل المرحلة المستحقة فقط (M2) ==")
    agent.sent_fb.clear()
    c8 = "chat-late-start"
    base = FAKE_NOW
    t7 = base - timedelta(hours=10)
    _add_conv(conn, c8, "psid_8", last_ts=t7.isoformat())
    _add_msg(conn, c8, "customer", "مميزات طيران تحسين", t7.isoformat())
    _run(agent)  # تهيئة
    _run(agent)  # مرحلة مستحقة
    m8 = [m for m in agent.sent_fb if m["to"] == "psid_8"]
    check("أُرسلت رسالة واحدة فقط (المرحلة المستحقة)", len(m8) == 1, str(len(m8)))
    check("المرحلة المستحقة بعد 10 ساعات هي M2", m8 and "عارفين إن قرار الحج مش سهل" in m8[0]["text"])

    # ---------------------------------------------------------------
    print("== 9) محادثة من إعلان آخر → لا تُلمس ==")
    agent.sent_fb.clear()
    c9 = "chat-other-ad"
    base = FAKE_NOW
    _add_conv(conn, c9, "psid_9", ad_id="999999999999999999")
    _add_msg(conn, c9, "customer", "تفاصيل", (base - timedelta(hours=3)).isoformat())
    n_before = len(agent.sent_fb)
    _run(agent)
    check("إعلان آخر → لا إرسال", not any(m["to"] == "psid_9" for m in agent.sent_fb))
    st = _state()
    check("إعلان آخر → غير موجود في ملف الحالة", c9 not in st.get("chats", {}))

    # ---------------------------------------------------------------
    print("== 10) منع الإرسال المزدوج (تشغيلان متتاليان) ==")
    agent.sent_fb.clear()
    c10 = "chat-dedup-1"
    base = FAKE_NOW
    t8 = base - timedelta(hours=2, minutes=30)
    _add_conv(conn, c10, "psid_10", last_ts=t8.isoformat())
    _add_msg(conn, c10, "customer", "تفاصيل البرنامج", t8.isoformat())
    _run(agent)
    _run(agent)
    _run(agent)  # تشغيل ثالث — يجب ألا يكرر M1
    sent_10 = [m for m in agent.sent_fb if m["to"] == "psid_10" and "حضرتك لسه معانا؟ 🕋" in m["text"]]
    check("M1 أُرسلت مرة واحدة فقط", len(sent_10) == 1, f"count={len(sent_10)}")

    # ---------------------------------------------------------------
    print("== 11) الرد بميديا (صوت) يعيد ضبط العداد ==")
    agent.sent_fb.clear()
    c11 = "chat-media-1"
    base = FAKE_NOW
    t9 = base - timedelta(hours=3)
    _add_conv(conn, c11, "psid_11", last_ts=t9.isoformat())
    _add_msg(conn, c11, "customer", "تفاصيل", t9.isoformat())
    _run(agent)
    _run(agent)  # M1 أُرسلت
    t9b = FAKE_NOW + timedelta(minutes=30)
    _add_conv(conn, c11, "psid_11", last_ts=t9b.isoformat())
    _add_msg(conn, c11, "customer", "[customer sent an audio message.]", t9b.isoformat())
    FAKE_NOW = t9b + timedelta(minutes=30)  # بعد نصف ساعة من الصوت
    n_before = len(agent.sent_fb)
    _run(agent)
    check("الرد الصوتي لم يُنتج رسالة follow-up فورية", len(agent.sent_fb) == n_before)
    st = _state()
    e11 = st["chats"].get(c11, {})
    check("العداد أُعيد ضبطه من الرد الصوتي (highest=0)", e11.get("highest_stage_sent") == 0, str(e11))

    conn.close()
    print(f"\n=== النتيجة: {PASS} نجح / {FAIL} فشل ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
