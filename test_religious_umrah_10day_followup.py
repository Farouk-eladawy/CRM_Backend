# -*- coding: utf-8 -*-
"""
اختبار معزول (Isolated) لـ workflows/religious_umrah_10day_followup.py
======================================================================
ينشئ قاعدة بيانات مؤقتة + Agent وهمي + ساعة قاهرة قابلة للتحكم، ويوجّه
كلاً من الـ Workflow و chat_db إلى ملفات الاختبار (دون أي أثر على
قاعدة البيانات الحقيقية)، ثم يختبر كل سيناريوهات الـ Workflow.

السيناريوهات المغطاة (حسب برومبت نظام المتابعة التلقائية — العمرة المريح ١٠ أيام):
  1) شرط التفعيل الحصري: محادثة من إعلان آخر → لا تُلمس نهائياً.
  2) التسلسل العادي: M1 بعد 60 دقيقة → M2 بعد 7 ساعات → M3 بعد 22 ساعة.
  3) M1 تُحسب من آخر رسالة (عميل أو رد منّا) — رد منّا يبعد الموعد.
  4) كل رسالة تُرسل مرة واحدة فقط (تشغيلان متتاليان → لا تكرار).
  5) بعد 24 ساعة من آخر رسالة عميل → إيقاف نهائي بدون إرسال.
  6) ساعات الليل [00:00 - 08:00): تأجيل الإرسال لما بعد 8 صباحاً.
  7) استثناء الليل: نافذة ستُغلق قبل 8 صباحاً → M3 تُرسل فوراً أثناء الليل.
  8) شروط الإيقاف: أي رد من العميل → إيقاف السلسلة.
  9) رقم تليفون → تأكيد الاستلام + تسجيل customer_phone + needs_help=1 + إيقاف.
  10) نية الحجز → تحويل لمسار الحجز + needs_help=1 + إيقاف.
  11) طلب عدم التواصل → اعتذار + إيقاف نهائي + لا يُرسل حتى في محادثة جديدة
      لنفس الـ sender (سجل opt-out دائم).
  12) تدخّل موظف بشري (needs_help=1) → إيقاف بدون إرسال.
  13) رد ميديا (صوت) من العميل → إيقاف السلسلة (تفاعل حقيقي).
  14) رسالة الإحالة [Facebook Ad Referral] لا تُحتسب تفاعلاً.
  15) أول رسالة تحتوي رقم → تأكيد + تسجيل + إيقاف فوري.
  16) M2 أثناء الليل → تُؤجَّل (لا استثناء للمرحلتين 1 و2).
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

# توافق ترميز الـ console مع العربية
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

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


PASS = 0
BASE_NOW = datetime(2026, 8, 2, 12, 0, 0)


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


FAIL = 0


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


def scenario_normal_sequence(conn, agent):
    print("\n2) التسلسل العادي: M1 بعد 60 دقيقة → M2 بعد 7 ساعات → M3 بعد 22 ساعة")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(minutes=30)  # رسالة العميل قبل 30 دقيقة فقط
    _add_conv(conn, "chat_seq", "sender_seq", last_ts=(t0 + timedelta(minutes=10)).isoformat())
    _add_msg(conn, "chat_seq", "customer", "كام سعر البرنامج؟", t0.isoformat())
    # آخر رسالة = رد منّا (أحدث من رسالة العميل) → M1 تُحسب منه
    agent_reply = t0 + timedelta(minutes=10)
    _add_msg(conn, "chat_seq", "agent", "أهلًا بحضرتك، البرنامج بـ٥١,٥٠٠ ج 🕋", agent_reply.isoformat())

    # تشغيل 1: مرّ 20 دقيقة فقط على ردّنا → لا إرسال بعد (تهيئة التتبع فقط)
    FAKE_NOW = agent_reply + timedelta(minutes=20)
    _run(agent)
    check("قبل 60 دقيقة من آخر رسالة: لا إرسال", len(agent.sent_fb) == 0, f"sent={len(agent.sent_fb)}")

    # تشغيل 2: مرّ 65 دقيقة على ردّنا → M1
    FAKE_NOW = agent_reply + timedelta(minutes=65)
    _run(agent)
    check("بعد 60 دقيقة من آخر رسالة: M1 تُرسل", len(agent.sent_fb) == 1)
    check("نص M1 مطابق تماماً", agent.sent_fb and agent.sent_fb[0]["text"] == WF.MSG_STAGE1)
    entry = _state().get("chats", {}).get("chat_seq", {})
    check("أعلى مرحلة مرسلة = 1", int(entry.get("highest_stage_sent") or 0) == 1)

    # تشغيل 3: بعد 5 ساعات من رسالة العميل → لا M2 بعد (تحتاج 7 ساعات)
    FAKE_NOW = t0 + timedelta(hours=5)
    _run(agent)
    check("قبل 7 ساعات من رسالة العميل: لا M2", len(agent.sent_fb) == 1)

    # تشغيل 4: بعد 7 ساعات ونصف → M2
    FAKE_NOW = t0 + timedelta(hours=7, minutes=30)
    _run(agent)
    check("بعد 7 ساعات من رسالة العميل: M2 تُرسل", len(agent.sent_fb) == 2)
    check("نص M2 مطابق تماماً", agent.sent_fb[1]["text"] == WF.MSG_STAGE2)

    # تشغيل 5: بعد 22 ساعة ونصف → M3 (قبل 24)
    FAKE_NOW = t0 + timedelta(hours=22, minutes=30)
    _run(agent)
    check("بعد 22 ساعة من رسالة العميل: M3 تُرسل", len(agent.sent_fb) == 3)
    check("نص M3 مطابق تماماً", agent.sent_fb[2]["text"] == WF.MSG_STAGE3)

    # تشغيل 6: لا تكرار بعد اكتمال التسلسل
    FAKE_NOW = t0 + timedelta(hours=23)
    _run(agent)
    check("لا رسالة رابعة أبداً", len(agent.sent_fb) == 3)


def scenario_no_duplicate(conn, agent):
    print("\n3) لا تكرار: تشغيلان متتاليان بعد استحقاق M1 → رسالة واحدة فقط")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_dup", "sender_dup", last_ts=t0.isoformat())
    _add_msg(conn, "chat_dup", "customer", "السلام عليكم", t0.isoformat())
    _run(agent)
    _run(agent)
    check("رسالة واحدة فقط رغم تشغيلين", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")


def scenario_window_closed(conn, agent):
    print("\n4) نافذة 24 ساعة مغلقة → إيقاف نهائي بدون إرسال")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=25)
    _add_conv(conn, "chat_old", "sender_old", last_ts=t0.isoformat())
    _add_msg(conn, "chat_old", "customer", "كام السعر؟", t0.isoformat())
    _run(agent)
    check("محادثة قديمة (>24 ساعة) لا تُرسل لها أي شيء", len(agent.sent_fb) == 0)
    check("ولا تدخل التتبع أصلاً", "chat_old" not in _state().get("chats", {}))


def scenario_night_defer(conn, agent):
    print("\n5) ساعات الليل [00:00-08:00): تأجيل M1 لما بعد 8 صباحاً")
    global FAKE_NOW
    _reset(conn, agent)
    last_msg = datetime(2026, 8, 2, 0, 0, 0)
    _add_conv(conn, "chat_night", "sender_night", last_ts=last_msg.isoformat())
    _add_msg(conn, "chat_night", "customer", "السعر كام؟", last_msg.isoformat())
    FAKE_NOW = datetime(2026, 8, 2, 1, 30, 0)
    _run(agent)
    check("لا إرسال أثناء الليل (M1 مؤجلة)", len(agent.sent_fb) == 0, f"sent={len(agent.sent_fb)}")
    check("السجل لا يزال متتبعاً (لم يُحذف)", "chat_night" in _state().get("chats", {}))
    FAKE_NOW = datetime(2026, 8, 2, 8, 5, 0)
    _run(agent)
    check("بعد 8 صباحاً: M1 تُرسل", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")


def scenario_night_stage3_exception(conn, agent):
    print("\n6) استثناء الليل: النافذة ستُغلق قبل 8 صباحاً → M3 تُرسل فوراً ليلاً")
    global FAKE_NOW
    _reset(conn, agent)
    # آخر رسالة عميل منذ 23 ساعة → النافذة تغلق خلال ساعة (قبل 8 صباحاً)
    t0 = datetime(2026, 8, 2, 7, 30, 0)  # رسالة العميل (اليوم السابق 7:30 صباحاً)
    _add_conv(conn, "chat_n3", "sender_n3", last_ts=(t0 + timedelta(hours=23)).isoformat())
    _add_msg(conn, "chat_n3", "customer", "السعر كام؟", t0.isoformat())
    _add_msg(conn, "chat_n3", "agent", "أهلًا بحضرتك 🕋", (t0 + timedelta(minutes=5)).isoformat())
    # M1 بعد 70 دقيقة من رسالة العميل (65 دقيقة من ردّنا) = 8:40 صباحاً — نهارية
    FAKE_NOW = t0 + timedelta(hours=1, minutes=10)
    _run(agent)
    check("M1 أُرسلت نهاراً", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    # M2 بعد 8 ساعات (15:30 — نهارية)
    FAKE_NOW = t0 + timedelta(hours=8)
    _run(agent)
    check("M2 أُرسلت", len(agent.sent_fb) == 2)
    # 6:30 صباحاً اليوم التالي — M3 مستحقة والنافذة تغلق 7:30 (قبل 8 صباحاً)
    FAKE_NOW = t0 + timedelta(hours=23)
    _run(agent)
    check("M3 أُرسلت فوراً رغم الليل (النافذة ستُغلق قبل 8 صباحاً)",
          len(agent.sent_fb) == 3, f"sent={len(agent.sent_fb)}")
    check("نص M3 مطابق", agent.sent_fb[-1]["text"] == WF.MSG_STAGE3)


def scenario_customer_reply_stops(conn, agent):
    print("\n7) أي رد من العميل → إيقاف السلسلة (لا مزيد من المتابعات)")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_rep", "sender_rep", last_ts=t0.isoformat())
    _add_msg(conn, "chat_rep", "customer", "كام السعر؟", t0.isoformat())
    _run(agent)  # M1 تُرسل (المحادثة قديمة 2 ساعة)
    check("M1 أُرسلت", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    # العميل يرد بعد M1
    FAKE_NOW = t0 + timedelta(hours=2, minutes=5)
    _add_msg(conn, "chat_rep", "customer", "تمام شكرًا، ممكن تفاصيل أكثر؟", FAKE_NOW.isoformat())
    _add_conv(conn, "chat_rep", "sender_rep", last_ts=FAKE_NOW.isoformat())
    _run(agent)
    check("لا تُرسل M2 بعد رد العميل", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    entry = _state().get("chats", {}).get("chat_rep", {})
    check("السلسلة موقوفة بسبب رد العميل", entry.get("stop_reason") == "customer_replied")
    FAKE_NOW = t0 + timedelta(hours=9)
    _run(agent)
    check("لا إرسال نهائياً بعد إيقاف السلسلة", len(agent.sent_fb) == 1)


def scenario_phone_received(conn, agent):
    print("\n8) رقم تليفون → تأكيد الاستلام + تسجيل + إشعار فريق بشري + إيقاف")
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
    check("رُسل رد تأكيد استلام الرقم", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")
    check("نص التأكيد مطابق", agent.sent_fb[-1]["text"] == WF.MSG_PHONE_CONFIRM)
    row = _conv_row(conn, "chat_ph")
    check("الرقم محفوظ في customer_phone", row[0] == "01012345678", str(row))
    check("needs_help=1 (إشعار فريق بشري)", row[1] == 1, str(row))
    entry = _state().get("chats", {}).get("chat_ph", {})
    check("السلسلة موقوفة (phone_received)", str(entry.get("stop_reason") or "").startswith("phone_received"))
    FAKE_NOW = t0 + timedelta(hours=10)
    _run(agent)
    check("لا مزيد من الإرسالات بعد الرقم", len(agent.sent_fb) == 2)


def scenario_booking_intent(conn, agent):
    print("\n9) نية الحجز → تحويل لمسار الحجز + إيقاف")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_bk", "sender_bk", last_ts=t0.isoformat())
    _add_msg(conn, "chat_bk", "customer", "كام السعر؟", t0.isoformat())
    _run(agent)
    FAKE_NOW = t0 + timedelta(hours=3)
    _add_msg(conn, "chat_bk", "customer", "عايز أحجز، خطوات الحجز إيه؟", FAKE_NOW.isoformat())
    _add_conv(conn, "chat_bk", "sender_bk", last_ts=FAKE_NOW.isoformat())
    _run(agent)
    row = _conv_row(conn, "chat_bk")
    check("needs_help=1 (تحويل لمسار الحجز)", row[1] == 1, str(row))
    check("لم تُرسل M2 بعد نية الحجز", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    entry = _state().get("chats", {}).get("chat_bk", {})
    check("السلسلة موقوفة (booking_intent)", entry.get("stop_reason") == "booking_intent")


def scenario_optout_permanent(conn, agent):
    print("\n10) طلب عدم التواصل → اعتذار + إيقاف نهائي + لا يُرسل حتى في محادثة جديدة")
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
    check("رُسل اعتذار واحد", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")
    check("نص الاعتذار قصير ولطيف", agent.sent_fb[-1]["text"] == WF.MSG_OPTOUT_APOLOGY)
    check("السلسلة موقوفة (customer_opt_out)", _state().get("chats", {}).get("chat_oo", {}).get("stop_reason") == "customer_opt_out")
    check("الـ sender مُسجَّل في سجل الإيقاف الدائم", "sender_oo" in _state().get("opted_out_senders", {}))
    # محادثة جديدة لنفس الـ sender من نفس الإعلان
    FAKE_NOW = t0 + timedelta(hours=5)
    _add_conv(conn, "chat_oo2", "sender_oo", last_ts=FAKE_NOW.isoformat())
    _add_msg(conn, "chat_oo2", "customer", "كام السعر؟", FAKE_NOW.isoformat())
    _run(agent)
    check("لا تُرسل أي متابعة في المحادثة الجديدة (إيقاف دائم)", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")


def scenario_human_intervention(conn, agent):
    print("\n11) تدخّل موظف بشري (needs_help=1) → إيقاف بدون إرسال")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_hi", "sender_hi", last_ts=t0.isoformat())
    _add_msg(conn, "chat_hi", "customer", "كام السعر؟", t0.isoformat())
    _run(agent)
    check("M1 أُرسلت", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    _set_needs_help(conn, "chat_hi")
    _run(agent)
    check("لا إرسال بعد تدخل بشري", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")


def scenario_media_reply(conn, agent):
    print("\n12) رد ميديا (صوت) من العميل → إيقاف السلسلة (تفاعل حقيقي)")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_conv(conn, "chat_md", "sender_md", last_ts=t0.isoformat())
    _add_msg(conn, "chat_md", "customer", "كام السعر؟", t0.isoformat())
    _run(agent)
    FAKE_NOW = t0 + timedelta(hours=2, minutes=5)
    _add_msg(conn, "chat_md", "customer", "[customer sent an audio message]", FAKE_NOW.isoformat())
    _add_conv(conn, "chat_md", "sender_md", last_ts=FAKE_NOW.isoformat())
    _run(agent)
    check("الميديا تُوقف السلسلة ولا تُرسل M2", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    check("سبب الإيقاف: customer_replied", _state().get("chats", {}).get("chat_md", {}).get("stop_reason") == "customer_replied")


def scenario_referral_not_counted(conn, agent):
    print("\n13) رسالة الإحالة [Facebook Ad Referral] لا تُحتسب تفاعلاً")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=1)
    _add_conv(conn, "chat_ref", "sender_ref", last_ts=(t0 + timedelta(minutes=5)).isoformat())
    _add_msg(conn, "chat_ref", "customer", "[Facebook Ad Referral] source=ADS type=OPEN_THREAD ad_id=120248068201650757", t0.isoformat())
    _add_msg(conn, "chat_ref", "customer", "كام السعر؟", (t0 + timedelta(minutes=5)).isoformat())
    _run(agent)
    check("لا إرسال قبل 60 دقيقة من آخر رسالة حقيقية (الإحالة لا تحتسب)", len(agent.sent_fb) == 0, f"sent={len(agent.sent_fb)}")


def scenario_first_message_phone(conn, agent):
    print("\n14) أول رسالة تحتوي رقم → تأكيد + تسجيل + إيقاف فوري")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=1)
    _add_conv(conn, "chat_fp", "sender_fp", last_ts=t0.isoformat())
    _add_msg(conn, "chat_fp", "customer", "رقمي 01234567890 ابعتلي التفاصيل", t0.isoformat())
    _run(agent)
    check("رُسل تأكيد الاستلام", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    check("نص التأكيد مطابق", agent.sent_fb[0]["text"] == WF.MSG_PHONE_CONFIRM)
    row = _conv_row(conn, "chat_fp")
    check("الرقم محفوظ", row[0] == "01234567890", str(row))
    entry = _state().get("chats", {}).get("chat_fp", {})
    check("السلسلة موقوفة فوراً", str(entry.get("stop_reason") or "").startswith("phone_received"))


def scenario_stage2_night_defer(conn, agent):
    print("\n15) M2 أثناء الليل → تُؤجَّل (لا استثناء للمرحلتين 1 و2)")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = datetime(2026, 8, 1, 18, 0, 0)  # رسالة العميل 6 مساءً
    _add_conv(conn, "chat_n2", "sender_n2", last_ts=t0.isoformat())
    _add_msg(conn, "chat_n2", "customer", "كام السعر؟", t0.isoformat())
    # M1 بعد 60 دقيقة (7 مساءً) — نهارية
    FAKE_NOW = t0 + timedelta(hours=1)
    _run(agent)
    check("M1 أُرسلت نهاراً", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    # M2 مستحقة بعد 7 ساعات = 1 صباحاً → ليلاً → تُؤجَّل
    FAKE_NOW = t0 + timedelta(hours=7, minutes=10)
    _run(agent)
    check("M2 لا تُرسل أثناء الليل (تأجيل)", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    # 8:30 صباحاً → تُرسل
    FAKE_NOW = t0 + timedelta(hours=14, minutes=30)
    _run(agent)
    check("M2 تُرسل بعد 8 صباحاً", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")


def main():
    global PASS, FAIL, FAKE_NOW, WF
    tmpdir = tempfile.mkdtemp(prefix="umrah_10day_test_")
    db_file = os.path.join(tmpdir, "test_chat.db")
    state_file = os.path.join(tmpdir, "test_state.json")

    # تحميل الـ Workflow وتوجيهه لقاعدة الاختبار + ساعة وهمية
    spec = importlib.util.spec_from_file_location(
        "religious_umrah_10day_followup_test",
        os.path.join(BASE, "workflows", "religious_umrah_10day_followup.py"),
    )
    WF = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(WF)
    WF.DB_FILE = db_file
    WF.STATE_FILE = state_file
    WF._now = lambda: FAKE_NOW

    # توجيه chat_db إلى قاعدة الاختبار (حتى تُسجَّل الرسائل والتحديثات هناك)
    chat_db.DB_FILE = db_file

    conn = _make_db(db_file)
    agent = MockAgent()

    print("=== اختبارات Workflow العمرة المريح ١٠ أيام ===")
    scenario_activation_condition(conn, agent)
    scenario_normal_sequence(conn, agent)
    scenario_no_duplicate(conn, agent)
    scenario_window_closed(conn, agent)
    scenario_night_defer(conn, agent)
    scenario_night_stage3_exception(conn, agent)
    scenario_customer_reply_stops(conn, agent)
    scenario_phone_received(conn, agent)
    scenario_booking_intent(conn, agent)
    scenario_optout_permanent(conn, agent)
    scenario_human_intervention(conn, agent)
    scenario_media_reply(conn, agent)
    scenario_referral_not_counted(conn, agent)
    scenario_first_message_phone(conn, agent)
    scenario_stage2_night_defer(conn, agent)

    conn.close()
    print(f"\n===== النتيجة: {PASS} نجحت / {FAIL} فشلت =====")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
