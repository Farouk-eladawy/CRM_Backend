# -*- coding: utf-8 -*-
"""
اختبار معزول (Isolated) لـ workflows/religious_umrah_8day_followup.py
======================================================================
ينشئ قاعدة بيانات مؤقتة + Agent وهمي + ساعة قاهرة قابلة للتحكم، ويوجّه
كلاً من الـ Workflow و chat_db إلى ملفات الاختبار (دون أي أثر على
قاعدة البيانات الحقيقية)، ثم يختبر كل سيناريوهات الـ Workflow.

السيناريوهات المغطاة (حسب برومبت نظام المتابعة التلقائية — عمرة الـ٨ أيام):
  1) شرط التفعيل الحصري: محادثة من إعلان آخر → لا تُلمس نهائياً.
  2) التسلسل الزمني من آخر رسالة عميل: M1 بعد 1-3 ساعات → M2 بعد 6-9 → M3 بعد 21-22.
  3) الوقت يُحسب من آخر رسالة من العميل (وليس منّا) — رد منّا لا يبعد الموعد.
  4) كل رسالة تُرسل مرة واحدة فقط (تشغيلان متتاليان → لا تكرار).
  5) أي رد من العميل → إعادة ضبط العدّاد من الصفر (الرسائل الثلاث تعود متاحة).
  6) بعد 23 ساعة من آخر رسالة عميل → لا إرسال نهائياً (نافذة ميتا).
  7) رقم تليفون → وسم «Lead جاهز للاتصال» + customer_phone + needs_help=1 + إيقاف نهائي.
  8) تأكيد الحجز / تحويل العربون → تحويل لمسار الحجز + needs_help=1 + إيقاف نهائي.
  9) طلب عدم التواصل → إيقاف نهائي + لا يُرسل حتى في محادثة جديدة لنفس الـ sender.
  10) كلمة «موعد» → إرسال مواعيد السفر + إعادة ضبط العدّاد.
  11) تدخّل موظف بشري (needs_help=1) → إيقاف بدون إرسال.
  12) أول رسالة تحتوي رقم → وسم + إيقاف فوري.
  13) رسالة الإحالة [Facebook Ad Referral] لا تُحتسب تفاعلاً.
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

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

FAKE_NOW = datetime(2026, 8, 3, 12, 0, 0)


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


def _add_conv(conn, chat_id, sender, ad_id=None, location="Religious",
              source="Facebook", last_ts=None):
    if ad_id is None:
        ad_id = WF.TARGET_AD_ID
    c = conn.cursor()
    c.execute(
        "INSERT INTO conversations (chat_id, source, sender_identifier, contact_name, last_message_time, location, facebook_ad_id, needs_help) "
        "VALUES (?,?,?,?,?,?,?,0) "
        "ON CONFLICT(chat_id) DO UPDATE SET last_message_time = excluded.last_message_time, facebook_ad_id = excluded.facebook_ad_id",
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


def _set_needs_help(conn, chat_id):
    c = conn.cursor()
    c.execute("UPDATE conversations SET needs_help = 1 WHERE chat_id = ?", (chat_id,))
    conn.commit()


def _run(agent, dry=False, limit=None):
    payload = {"dry_run": dry}
    if limit:
        payload["limit"] = limit
    return WF.run(agent, payload)


def _state():
    with open(WF.STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _conv_row(conn, chat_id):
    return conn.execute("SELECT customer_phone, needs_help FROM conversations WHERE chat_id=?", (chat_id,)).fetchone()


def _tags(conn, chat_id):
    row = conn.execute("SELECT tags FROM sales_customer_state WHERE chat_id=?", (chat_id,)).fetchone()
    if not row or not row[0]:
        return []
    return json.loads(row[0])


PASS = 0
FAIL = 0
BASE_NOW = datetime(2026, 8, 3, 12, 0, 0)


def _reset(conn, agent):
    """عزل تام لكل سيناريو: مسح الجداول + الحالة + سجل الإرسال + إعادة الساعة."""
    global FAKE_NOW
    c = conn.cursor()
    c.execute("DELETE FROM conversations")
    c.execute("DELETE FROM messages")
    c.execute("DELETE FROM sales_customer_state")
    conn.commit()
    agent.sent_fb.clear()
    agent.sent_wa.clear()
    if os.path.exists(WF.STATE_FILE):
        os.remove(WF.STATE_FILE)
    FAKE_NOW = BASE_NOW


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")


def _recent(agent, sender):
    return [m for m in agent.sent_fb if m["to"] == sender]


def scenario_activation_condition(conn, agent):
    print("\n1) شرط التفعيل الحصري: محادثة من إعلان آخر لا تُلمس")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_target", "sender_target", last_ts=t0.isoformat())
    _add_msg(conn, "chat_target", "customer", "السعر كام؟", t0.isoformat())
    _add_conv(conn, "chat_other", "sender_other", ad_id="999999999999999999", last_ts=t0.isoformat())
    _add_msg(conn, "chat_other", "customer", "السعر كام؟", t0.isoformat())
    _run(agent)
    check("محادثة الإعلان المستهدف أُرسلت لها M1", any(m["to"] == "sender_target" for m in agent.sent_fb))
    check("محادثة الإعلان الآخر لم تُرسل لها أي رسالة", not any(m["to"] == "sender_other" for m in agent.sent_fb))


def scenario_timing_from_customer(conn, agent):
    print("\n2) التوقيت من آخر رسالة من العميل: 1-3h → M1، 6-9h → M2، 21-22h → M3")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(minutes=30)  # رسالة العميل قبل 30 دقيقة فقط
    _add_conv(conn, "chat_seq", "sender_seq", last_ts=(t0 + timedelta(minutes=10)).isoformat())
    _add_msg(conn, "chat_seq", "customer", "كام سعر البرنامج؟", t0.isoformat())
    # آخر رسالة = رد منّا (أحدث من رسالة العميل) — لكن التوقيت من رسالة العميل
    agent_reply = t0 + timedelta(minutes=10)
    _add_msg(conn, "chat_seq", "agent", "أهلًا بحضرتك، البرنامج بـ٣٤٬٧٥٠ ج 🕋", agent_reply.isoformat())

    # تشغيل 1: مرّ 30 دقيقة فقط على رسالة العميل → لا إرسال (أقل من 1 ساعة)
    FAKE_NOW = t0 + timedelta(minutes=30)
    _run(agent)
    check("قبل 1 ساعة من رسالة العميل: لا إرسال", len(agent.sent_fb) == 0, f"sent={len(agent.sent_fb)}")

    # تشغيل 2: مرّ 1.5 ساعة على رسالة العميل (1.4 ساعة على ردّنا) → M1
    FAKE_NOW = t0 + timedelta(hours=1, minutes=30)
    _run(agent)
    check("بعد 1-3 ساعات من رسالة العميل: M1 تُرسل", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    check("نص M1 مطابق تماماً", agent.sent_fb and agent.sent_fb[0]["text"] == WF.MSG_STAGE1)
    entry = _state().get("chats", {}).get("chat_seq", {})
    check("M1 مسجّلة كأُرسلت", bool(entry.get("stage1_sent")))

    # تشغيل 3: مرّ 3.5 ساعات → لا M2 (تحتاج 6 ساعات)
    FAKE_NOW = t0 + timedelta(hours=3, minutes=30)
    _run(agent)
    check("قبل 6 ساعات من رسالة العميل: لا M2", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")

    # تشغيل 4: مرّ 6.5 ساعات → M2
    FAKE_NOW = t0 + timedelta(hours=6, minutes=30)
    _run(agent)
    check("بعد 6-9 ساعات من رسالة العميل: M2 تُرسل", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")
    check("نص M2 مطابق تماماً", agent.sent_fb[1]["text"] == WF.MSG_STAGE2)

    # تشغيل 5: مرّ 10 ساعات → لا M3 (تحتاج 21 ساعة)
    FAKE_NOW = t0 + timedelta(hours=10)
    _run(agent)
    check("قبل 21 ساعة من رسالة العميل: لا M3", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")

    # تشغيل 6: مرّ 21.5 ساعة → M3
    FAKE_NOW = t0 + timedelta(hours=21, minutes=30)
    _run(agent)
    check("بعد 21-22 ساعة من رسالة العميل: M3 تُرسل", len(agent.sent_fb) == 3, f"sent={len(agent.sent_fb)}")
    check("نص M3 مطابق تماماً", agent.sent_fb[2]["text"] == WF.MSG_STAGE3)

    # تشغيل 7: مرّ 23.5 ساعة → لا رسالة رابعة أبداً
    FAKE_NOW = t0 + timedelta(hours=23, minutes=30)
    _run(agent)
    check("لا رسالة رابعة بعد 23 ساعة", len(agent.sent_fb) == 3, f"sent={len(agent.sent_fb)}")


def scenario_no_duplicate(conn, agent):
    print("\n3) لا تكرار: تشغيلان متتاليان بعد استحقاق M1 → رسالة واحدة فقط")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_dup", "sender_dup", last_ts=t0.isoformat())
    _add_msg(conn, "chat_dup", "customer", "السلام عليكم", t0.isoformat())
    _run(agent)
    _run(agent)
    check("رسالة واحدة فقط رغم تشغيلين", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")


def scenario_reply_resets(conn, agent):
    print("\n4) أي رد من العميل → إعادة ضبط العدّاد من الصفر (الرسائل الثلاث تعود متاحة)")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_reset", "sender_reset", last_ts=t0.isoformat())
    _add_msg(conn, "chat_reset", "customer", "كام السعر؟", t0.isoformat())
    _run(agent)  # M1 تُرسل (المحادثة عمرها 2 ساعة)
    check("M1 أُرسلت", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")

    # العميل يرد بعد M1 → تُعاد ضبط العدّاد من صفر
    FAKE_NOW = t0 + timedelta(hours=2, minutes=5)
    _add_msg(conn, "chat_reset", "customer", "تمام شكرًا، ممكن تفاصيل أكثر؟", FAKE_NOW.isoformat())
    _add_conv(conn, "chat_reset", "sender_reset", last_ts=FAKE_NOW.isoformat())
    _run(agent)
    entry = _state().get("chats", {}).get("chat_reset", {})
    check("العدّاد أُعيد ضبطه (M1 أصبحت متاحة من جديد)", not entry.get("stage1_sent"))
    check("المرساة أصبحت رد العميل الجديد", entry.get("last_customer_reply") == FAKE_NOW.isoformat())
    check("لا تُرسل رسالة في نفس دورة الرد (أقل من ساعة)", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")

    # بعد 1.5 ساعة من رد العميل → M1 تُرسل من جديد (عدّاد جديد)
    FAKE_NOW = t0 + timedelta(hours=3, minutes=30)
    _run(agent)
    check("M1 تُرسل من جديد بعد 1-3 ساعات من رد العميل", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")


def scenario_window_closed(conn, agent):
    print("\n5) نافذة 24 ساعة مغلقة (أكثر من 23 ساعة) → لا إرسال نهائياً")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=25)
    _add_conv(conn, "chat_old", "sender_old", last_ts=t0.isoformat())
    _add_msg(conn, "chat_old", "customer", "كام السعر؟", t0.isoformat())
    _run(agent)
    check("محادثة قديمة (>23 ساعة) لا تُرسل لها أي شيء", len(agent.sent_fb) == 0)
    check("ولا تدخل التتبع أصلاً", "chat_old" not in _state().get("chats", {}))


def scenario_phone_received(conn, agent):
    print("\n6) رقم تليفون (01 + 11 رقم) → وسم «Lead جاهز للاتصال» + needs_help + إيقاف نهائي")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_ph", "sender_ph", last_ts=t0.isoformat())
    _add_msg(conn, "chat_ph", "customer", "كام السعر؟", t0.isoformat())
    _run(agent)
    # العميل يرسل رقمه
    FAKE_NOW = t0 + timedelta(hours=2, minutes=10)
    _add_msg(conn, "chat_ph", "customer", "رقمي هو 01012345678", FAKE_NOW.isoformat())
    _add_conv(conn, "chat_ph", "sender_ph", last_ts=FAKE_NOW.isoformat())
    _run(agent)
    check("الوسم «Lead جاهز للاتصال» مضاف", "Lead جاهز للاتصال" in _tags(conn, "chat_ph"), str(_tags(conn, "chat_ph")))
    row = _conv_row(conn, "chat_ph")
    check("الرقم محفوظ في customer_phone", row[0] == "01012345678", str(row))
    check("needs_help=1 (إشعار فريق بشري)", row[1] == 1, str(row))
    entry = _state().get("chats", {}).get("chat_ph", {})
    check("السلسلة موقوفة (phone_received)", str(entry.get("stop_reason") or "").startswith("phone_received"))
    # لا مزيد من الإرسالات بعد الرقم
    FAKE_NOW = t0 + timedelta(hours=8)
    _run(agent)
    check("لا مزيد من الإرسالات بعد الرقم", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")


def scenario_booking_intent(conn, agent):
    print("\n7) تأكيد الحجز / تحويل العربون → تحويل لمسار الحجز + إيقاف نهائي")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_bk", "sender_bk", last_ts=t0.isoformat())
    _add_msg(conn, "chat_bk", "customer", "كام السعر؟", t0.isoformat())
    _run(agent)
    FAKE_NOW = t0 + timedelta(hours=2, minutes=5)
    _add_msg(conn, "chat_bk", "customer", "تمام حجزت وحولت العربون", FAKE_NOW.isoformat())
    _add_conv(conn, "chat_bk", "sender_bk", last_ts=FAKE_NOW.isoformat())
    _run(agent)
    row = _conv_row(conn, "chat_bk")
    check("needs_help=1 (تحويل لمسار الحجز)", row[1] == 1, str(row))
    entry = _state().get("chats", {}).get("chat_bk", {})
    check("السلسلة موقوفة (booking_confirmed)", entry.get("stop_reason") == "booking_confirmed")
    # لا مزيد من الإرسالات
    FAKE_NOW = t0 + timedelta(hours=7)
    _run(agent)
    check("لا مزيد من الإرسالات بعد تأكيد الحجز", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")


def scenario_optout_permanent(conn, agent):
    print("\n8) طلب عدم التواصل → إيقاف نهائي + لا يُرسل حتى في محادثة جديدة")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_oo", "sender_oo", last_ts=t0.isoformat())
    _add_msg(conn, "chat_oo", "customer", "كام السعر؟", t0.isoformat())
    _run(agent)
    FAKE_NOW = t0 + timedelta(hours=2, minutes=5)
    _add_msg(conn, "chat_oo", "customer", "متبعتليش كمان، مش مهتم", FAKE_NOW.isoformat())
    _add_conv(conn, "chat_oo", "sender_oo", last_ts=FAKE_NOW.isoformat())
    _run(agent)
    check("السلسلة موقوفة (customer_opt_out)", _state().get("chats", {}).get("chat_oo", {}).get("stop_reason") == "customer_opt_out")
    check("الـ sender مُسجَّل في سجل الإيقاف الدائم", "sender_oo" in _state().get("opted_out_senders", {}))
    # محادثة جديدة لنفس الـ sender من نفس الإعلان
    FAKE_NOW = t0 + timedelta(hours=5)
    _add_conv(conn, "chat_oo2", "sender_oo", last_ts=FAKE_NOW.isoformat())
    _add_msg(conn, "chat_oo2", "customer", "كام السعر؟", FAKE_NOW.isoformat())
    _run(agent)
    check("لا تُرسل أي متابعة في المحادثة الجديدة (إيقاف دائم)", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")


def scenario_dates_keyword(conn, agent):
    print("\n9) كلمة «موعد» → إرسال مواعيد السفر + إعادة ضبط العدّاد")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_dt", "sender_dt", last_ts=t0.isoformat())
    _add_msg(conn, "chat_dt", "customer", "كام السعر؟", t0.isoformat())
    _run(agent)
    # العميل يرسل «موعد»
    FAKE_NOW = t0 + timedelta(hours=2, minutes=5)
    _add_msg(conn, "chat_dt", "customer", "موعد", FAKE_NOW.isoformat())
    _add_conv(conn, "chat_dt", "sender_dt", last_ts=FAKE_NOW.isoformat())
    _run(agent)
    check("أُرسلت رسالة مواعيد السفر", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")
    check("نص رسالة المواعيد مطابق", agent.sent_fb[-1]["text"] == WF.MSG_DATES_REPLY)
    entry = _state().get("chats", {}).get("chat_dt", {})
    check("العدّاد أُعيد ضبطه بعد «موعد»", not entry.get("stage1_sent") and not entry.get("stage2_sent"))
    check("المرساة أصبحت رسالة «موعد»", entry.get("last_customer_reply") == FAKE_NOW.isoformat())


def scenario_human_intervention(conn, agent):
    print("\n10) تدخّل موظف بشري (needs_help=1) → إيقاف بدون إرسال")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_hi", "sender_hi", last_ts=t0.isoformat())
    _add_msg(conn, "chat_hi", "customer", "كام السعر؟", t0.isoformat())
    _run(agent)
    check("M1 أُرسلت", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    _set_needs_help(conn, "chat_hi")
    FAKE_NOW = t0 + timedelta(hours=7)
    _run(agent)
    check("لا إرسال بعد تدخل بشري", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")


def scenario_first_message_phone(conn, agent):
    print("\n11) أول رسالة تحتوي رقم → وسم + إيقاف فوري")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=1)
    _add_conv(conn, "chat_fp", "sender_fp", last_ts=t0.isoformat())
    _add_msg(conn, "chat_fp", "customer", "رقمي 01234567890 ابعتلي التفاصيل", t0.isoformat())
    _run(agent)
    check("الوسم «Lead جاهز للاتصال» مضاف", "Lead جاهز للاتصال" in _tags(conn, "chat_fp"), str(_tags(conn, "chat_fp")))
    row = _conv_row(conn, "chat_fp")
    check("الرقم محفوظ", row[0] == "01234567890", str(row))
    entry = _state().get("chats", {}).get("chat_fp", {})
    check("السلسلة موقوفة فوراً", str(entry.get("stop_reason") or "").startswith("phone_received"))


def scenario_referral_not_counted(conn, agent):
    print("\n12) رسالة الإحالة [Facebook Ad Referral] لا تُحتسب تفاعلاً")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=1)
    _add_conv(conn, "chat_ref", "sender_ref", last_ts=(t0 + timedelta(minutes=5)).isoformat())
    _add_msg(conn, "chat_ref", "customer", "[Facebook Ad Referral] source=ADS type=OPEN_THREAD ad_id=120248067160660757", t0.isoformat())
    _add_msg(conn, "chat_ref", "customer", "كام السعر؟", (t0 + timedelta(minutes=5)).isoformat())
    _run(agent)
    check("لا إرسال قبل 1 ساعة من آخر رسالة حقيقية (الإحالة لا تحتسب)", len(agent.sent_fb) == 0, f"sent={len(agent.sent_fb)}")


def scenario_no_customer_message(conn, agent):
    print("\n13) محادثة بلا أي رسالة حقيقية من العميل → لا إرسال")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_nocust", "sender_nocust", last_ts=t0.isoformat())
    _add_msg(conn, "chat_nocust", "customer", "[Facebook Ad Referral] source=ADS type=OPEN_THREAD ad_id=120248067160660757", t0.isoformat())
    _run(agent)
    check("لا إرسال (لا توجد رسالة عميل حقيقية)", len(agent.sent_fb) == 0, f"sent={len(agent.sent_fb)}")


def scenario_phone_already_recorded(conn, agent):
    print("\n14) customer_phone محفوظ في DB (فُقد ملف الحالة) → حماية ذاتية: لا إرسال")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_phdb", "sender_phdb", last_ts=t0.isoformat())
    _add_msg(conn, "chat_phdb", "customer", "كام السعر؟", t0.isoformat())
    # محاكاة: الرقم محفوظ في قاعدة البيانات لكن ملف الحالة فارغ/مفقود
    c = conn.cursor()
    c.execute("UPDATE conversations SET customer_phone = '01234567890' WHERE chat_id = ?", ("chat_phdb",))
    conn.commit()
    _run(agent)
    check("لا تُرسل أي متابعة لعميل محفوظ له رقم", len(agent.sent_fb) == 0, f"sent={len(agent.sent_fb)}")
    entry = _state().get("chats", {}).get("chat_phdb", {})
    check("السلسلة موقوفة فوراً (phone_already_on_record)",
          str(entry.get("stop_reason") or "").startswith("phone_already_on_record"), str(entry))


def scenario_no_resend_if_sent_in_db(conn, agent):
    print("\n15) رسالة سبق إرسالها (في DB لكن ملف الحالة فُقد) → لا تتكرر أبداً")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_dedup", "sender_dedup", last_ts=t0.isoformat())
    _add_msg(conn, "chat_dedup", "customer", "كام السعر؟", t0.isoformat())
    # محاكاة: M1 أُرسلت فعلاً من نسخة سابقة (مسجّلة في DB) لكن ملف الحالة فارغ
    _add_msg(conn, "chat_dedup", "agent", WF.MSG_STAGE1, (t0 + timedelta(hours=1)).isoformat())
    _run(agent)
    check("لا تُرسل M1 مرة أخرى (موجودة في DB)", len(agent.sent_fb) == 0, f"sent={len(agent.sent_fb)}")
    entry = _state().get("chats", {}).get("chat_dedup", {})
    check("M1 مسجّلة كأُرسلت من قاعدة البيانات", bool(entry.get("stage1_sent")))
    # M2 تبقى متاحة لأنها لم تُرسل بعد
    FAKE_NOW = t0 + timedelta(hours=6, minutes=30)
    _run(agent)
    check("M2 تُرسل (لم تُرسل من قبل)", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    check("نص M2 مطابق", agent.sent_fb[0]["text"] == WF.MSG_STAGE2)


def main():
    global PASS, FAIL, FAKE_NOW, WF
    tmpdir = tempfile.mkdtemp(prefix="umrah_8day_test_")
    db_file = os.path.join(tmpdir, "test_chat.db")
    state_file = os.path.join(tmpdir, "test_state.json")

    spec = importlib.util.spec_from_file_location(
        "religious_umrah_8day_followup_test",
        os.path.join(BASE, "workflows", "religious_umrah_8day_followup.py"),
    )
    WF = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(WF)
    WF.DB_FILE = db_file
    WF.STATE_FILE = state_file
    WF._now = lambda: FAKE_NOW

    chat_db.DB_FILE = db_file

    conn = _make_db(db_file)
    agent = MockAgent()

    print("=== اختبارات Workflow عمرة الـ٨ أيام (Religious Umrah 8-Day) ===")
    scenario_activation_condition(conn, agent)
    scenario_timing_from_customer(conn, agent)
    scenario_no_duplicate(conn, agent)
    scenario_reply_resets(conn, agent)
    scenario_window_closed(conn, agent)
    scenario_phone_received(conn, agent)
    scenario_booking_intent(conn, agent)
    scenario_optout_permanent(conn, agent)
    scenario_dates_keyword(conn, agent)
    scenario_human_intervention(conn, agent)
    scenario_first_message_phone(conn, agent)
    scenario_referral_not_counted(conn, agent)
    scenario_no_customer_message(conn, agent)
    scenario_phone_already_recorded(conn, agent)
    scenario_no_resend_if_sent_in_db(conn, agent)

    conn.close()
    print(f"\n===== النتيجة: {PASS} نجحت / {FAIL} فشلت =====")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
