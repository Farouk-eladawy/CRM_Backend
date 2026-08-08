# -*- coding: utf-8 -*-
"""
اختبار معزول (Isolated) لـ workflows/religious_15day_followup.py
=================================================================
ينشئ قاعدة بيانات مؤقتة + Agent وهمي + ساعة قاهرة قابلة للتحكم، ويوجّه
كلاً من الـ Workflow و chat_db إلى ملفات الاختبار (دون أي أثر على قاعدة
البيانات الحقيقية)، ثم يختبر كل سيناريوهات الـ Workflow.

السيناريوهات المغطاة (حسب برومبت نظام الفولو اب — برنامج عمرة الـ١٥ يوم):
  1) شرط التفعيل الحصري: ad_id = 120248067701970757 فقط — محادثة من إعلان
     آخر → لا تُلمس نهائياً.
  2) التسلسل العادي: FU1 بعد 3 ساعات من آخر رسالة (ردّنا) → FU2 بين 20 و23
     ساعة من آخر تفاعل عميل (زرار ١ → نصوص V1).
  3) إزالة تكرار received/sent لزر فيسبوك: آخر رسالة = ردّنا وليس تكرار الزر
     (بدون هذا، FU1 لا تعمل أبداً).
  4) نسخ الأزرار: زرار ٢ → V2، زرار ٣ → V3، بلا زرار → V4 (العامة).
  5) لا تكرار: تشغيلان متتاليان بعد الاستحقاق → رسالة واحدة فقط.
  6) آخر رسالة من العميل (لم نرد بعد) → لا FU1.
  7) نافذة الـ 24 ساعة مغلقة → إيقاف نهائي بدون إرسال.
  8) ساعات الليل [23:00 - 09:00): تأجيل FU1 لما بعد 9 صباحاً.
  9) رد العميل النصي → إلغاء الفولو اب المجدول وإعادة العدّاد من جديد
     (لا FU2 في نفس الدورة — والحد الأقصى التراكمي ٢ يبقى).
  10) رقم تليفون → customer_phone + needs_help=1 + وسم "عميل جاهز للاتصال"
      + إيقاف (بدون رسالة رد للعميل).
  11) العربون/تأكيد الحجز → تحويل لفريق الحجز (needs_help=1) + إيقاف.
  12) طلب عدم التواصل → اعتذار + إيقاف نهائي دائم (لا يُرسل حتى في محادثة
      جديدة لنفس الـ sender).
  13) لايك/إيموجي فقط → رد طبيعي (إن لم يسبق المساعد الأساسي بالرد) +
      إعادة دورة الفولو اب من جديد.
  14) الحد الأقصى: رسالتا فولو اب فقط لكل محادثة مهما كانت الظروف.
  15) تدخّل موظف بشري (needs_help=1) → إيقاف بدون إرسال.
  16) FU2 بعد مرور 23 ساعة → لا تُرسل (حد الـ 23 ساعة).
  17) رسالة الإحالة [Facebook Ad Referral] لا تُحتسب تفاعلاً.
"""
import os
import sys
import json
import uuid
import sqlite3
import tempfile
import importlib.util
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
        timestamp TIMESTAMP, status TEXT, source TEXT, external_message_id TEXT,
        reaction_emoji TEXT)""")
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


def _add_msg(conn, chat_id, sender_type, text, ts, status="received", reaction_emoji=None):
    c = conn.cursor()
    mid = str(uuid.uuid4())
    c.execute(
        "INSERT INTO messages (msg_id, chat_id, sender_type, text, timestamp, status, source, reaction_emoji) VALUES (?,?,?,?,?,?,?,?)",
        (mid, chat_id, sender_type, text, ts, status, "Facebook", reaction_emoji),
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
    try:
        return json.loads(row[0])
    except Exception:
        return []


PASS = 0
FAIL = 0
# الساعة الأساسية 3 مساءً حتى تقع مرحلة FU2 (20-23 ساعة) في النهار
# ولا تتصادم مع ساعات الليل الصامتة [23:00 - 09:00)
BASE_NOW = datetime(2026, 8, 2, 15, 0, 0)


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


def _add_button_chat(conn, chat_id, sender, button_text, agent_reply, t0, version_expected=None):
    """محادثة زر نموذجية: إحالة + زر (received) + تكرار الزر (sent) + ردّنا —
    بنفس ترتيب فيسبوك الحقيقي حتى نختبر إزالة التكرارات."""
    _add_conv(conn, chat_id, sender, last_ts=(t0 + timedelta(minutes=5)).isoformat())
    _add_msg(conn, chat_id, "customer", "[Facebook Ad Referral] source=ADS type=OPEN_THREAD ad_id=120248067701970757", t0.isoformat(), status="received")
    _add_msg(conn, chat_id, "customer", button_text, (t0 + timedelta(minutes=1)).isoformat(), status="received")
    _add_msg(conn, chat_id, "customer", "[Facebook Ad Referral] source=ADS type=OPEN_THREAD ad_id=120248067701970757", (t0 + timedelta(seconds=65)).isoformat(), status="sent")
    _add_msg(conn, chat_id, "agent", agent_reply, (t0 + timedelta(minutes=1, seconds=3)).isoformat(), status="sent")
    # تكرار الزر بعد ردّنا (sent) — نفس ما يحدث في فيسبوك الحقيقي
    _add_msg(conn, chat_id, "customer", button_text, (t0 + timedelta(minutes=1, seconds=9)).isoformat(), status="sent")
    # تحديث آخر رسالة في المحادثة = آخر رسالة (تكرار الزر — في الواقع آخر رسالة)
    _add_conv(conn, chat_id, sender, last_ts=(t0 + timedelta(minutes=1, seconds=9)).isoformat())


def scenario_activation_condition(conn, agent):
    print("\n1) شرط التفعيل الحصري: محادثة من إعلان آخر لا تُلمس")
    _reset(conn, agent)
    # FU1 تستحق بعد ٣ ساعات من آخر رسالة (ردّنا) — نختار t0 قبل ٤ ساعات
    # حتى تكون مستحقة فعلاً في زمن التشغيل (خطأ كان في النسخة الأولى: ٢ ساعة فقط)
    t0 = FAKE_NOW - timedelta(hours=4)
    _add_button_chat(conn, "chat_target", "sender_target", WF.BUTTONS[0]["raw"], "أهلاً بحضرتك 🕋 البرنامج جاهز", t0)
    _add_conv(conn, "chat_other", "sender_other", ad_id="999999999999999999", last_ts=t0.isoformat())
    _add_msg(conn, "chat_other", "customer", "السعر كام؟", t0.isoformat())
    _add_msg(conn, "chat_other", "agent", "أهلاً بحضرتك", (t0 + timedelta(minutes=2)).isoformat())
    _run(agent)
    check("محادثة الإعلان المستهدف أُرسلت لها FU1", any(m["to"] == "sender_target" for m in agent.sent_fb))
    check("محادثة الإعلان الآخر لم تُرسل لها أي رسالة", not any(m["to"] == "sender_other" for m in agent.sent_fb))


def scenario_normal_sequence_v1(conn, agent):
    print("\n2) التسلسل العادي (زرار ١): FU1 بعد 3 ساعات من آخر رسالة → FU2 بين 20 و23 ساعة")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=2)
    _add_button_chat(conn, "chat_seq", "sender_seq", WF.BUTTONS[0]["raw"], "برنامج الـ١٥ يوم مقسّم كده...", t0)

    # تشغيل 1: مرّت ساعة فقط على ردّنا → لا إرسال
    FAKE_NOW = t0 + timedelta(hours=1, minutes=5)
    _run(agent)
    check("قبل 3 ساعات من آخر رسالة: لا FU1", len(agent.sent_fb) == 0, f"sent={len(agent.sent_fb)}")
    entry = _state().get("chats", {}).get("chat_seq", {})
    check("النسخة = 1 (زرار برنامج الـ١٥ يوم)", int(entry.get("button_version") or 4) == 1, str(entry.get("button_version")))

    # تشغيل 2: مرّت 3 ساعات ونصف على آخر رسالة (ردّنا) → FU1 بنسخة V1
    FAKE_NOW = t0 + timedelta(hours=3, minutes=35)
    _run(agent)
    check("بعد 3 ساعات من آخر رسالة: FU1 تُرسل", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    check("نص FU1 مطابق لنسخة الزرار ١", agent.sent_fb and agent.sent_fb[0]["text"] == WF.MSG_V1_FU1)
    entry = _state().get("chats", {}).get("chat_seq", {})
    check("fu1_sent_at مسجّلة", entry.get("fu1_sent_at") is not None)

    # تشغيل 3: مرّت 19 ساعة فقط على آخر تفاعل عميل → لا FU2 بعد
    FAKE_NOW = t0 + timedelta(hours=19, minutes=30)
    _run(agent)
    check("قبل 20 ساعة من آخر تفاعل عميل: لا FU2", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")

    # تشغيل 4: مرّت 20.5 ساعة → FU2 بنسخة V1
    FAKE_NOW = t0 + timedelta(hours=20, minutes=30)
    _run(agent)
    check("بعد 20 ساعة من آخر تفاعل عميل: FU2 تُرسل", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")
    check("نص FU2 مطابق لنسخة الزرار ١", agent.sent_fb[1]["text"] == WF.MSG_V1_FU2)
    entry = _state().get("chats", {}).get("chat_seq", {})
    check("fu2_sent_at مسجّلة", entry.get("fu2_sent_at") is not None)
    check("إجمالي الفولو اب = 2", int(entry.get("total_fu_sent") or 0) == 2)

    # تشغيل 5: لا رسالة ثالثة أبداً
    FAKE_NOW = t0 + timedelta(hours=22, minutes=30)
    _run(agent)
    check("لا رسالة ثالثة أبداً", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")


def scenario_button_versions(conn, agent):
    print("\n3) نسخ الأزرار: زرار ٢ → V2، زرار ٣ → V3، بلا زرار → V4")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=4)
    # زرار ٢
    _add_button_chat(conn, "chat_b2", "sender_b2", WF.BUTTONS[1]["raw"], "عندنا مواعيد ٢ و٢٣ سبتمبر 🗓", t0)
    # زرار ٣
    _add_button_chat(conn, "chat_b3", "sender_b3", WF.BUTTONS[2]["raw"], "السعر شامل كل حاجة 💰", t0 + timedelta(minutes=1))
    # بلا زرار (رسالة نصية عادية)
    _add_conv(conn, "chat_v4", "sender_v4", last_ts=(t0 + timedelta(minutes=2)).isoformat())
    _add_msg(conn, "chat_v4", "customer", "عايز أعرف تفاصيل العمرة", (t0 + timedelta(minutes=2)).isoformat(), status="received")
    _add_msg(conn, "chat_v4", "agent", "أهلاً بحضرتك، تفضل التفاصيل", (t0 + timedelta(minutes=3)).isoformat(), status="sent")

    FAKE_NOW = t0 + timedelta(hours=4, minutes=30)
    _run(agent, limit=10)
    fu_b2 = [m for m in agent.sent_fb if m["to"] == "sender_b2"]
    fu_b3 = [m for m in agent.sent_fb if m["to"] == "sender_b3"]
    fu_v4 = [m for m in agent.sent_fb if m["to"] == "sender_v4"]
    check("FU1 لزرار ٢ بنسخة V2", len(fu_b2) == 1 and fu_b2[0]["text"] == WF.MSG_V2_FU1, str([m["text"][:20] for m in fu_b2]))
    check("FU1 لزرار ٣ بنسخة V3", len(fu_b3) == 1 and fu_b3[0]["text"] == WF.MSG_V3_FU1, str([m["text"][:20] for m in fu_b3]))
    check("FU1 بلا زرار بنسخة V4 (عامة)", len(fu_v4) == 1 and fu_v4[0]["text"] == WF.MSG_V4_FU1, str([m["text"][:20] for m in fu_v4]))


def scenario_no_duplicate(conn, agent):
    print("\n4) لا تكرار: تشغيلان متتاليان بعد الاستحقاق → رسالة واحدة فقط")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=4)
    _add_button_chat(conn, "chat_dup", "sender_dup", WF.BUTTONS[0]["raw"], "برنامج الـ١٥ يوم جاهز", t0)
    _run(agent)
    _run(agent)
    check("رسالة واحدة فقط رغم تشغيلين", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")


def scenario_last_customer_msg_no_fu1(conn, agent):
    print("\n5) آخر رسالة من العميل (لم نرد بعد) → لا FU1")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=4)
    _add_conv(conn, "chat_wait", "sender_wait", last_ts=(t0 + timedelta(minutes=10)).isoformat())
    _add_msg(conn, "chat_wait", "customer", "السعر كام للغرفة الثنائية؟", t0.isoformat(), status="received")
    _add_msg(conn, "chat_wait", "customer", "[Facebook Ad Referral] source=ADS", (t0 + timedelta(minutes=9)).isoformat(), status="sent")
    _add_msg(conn, "chat_wait", "customer", "السعر كام للغرفة الثنائية؟", (t0 + timedelta(minutes=10)).isoformat(), status="sent")
    _run(agent)
    check("لا FU1 بينما آخر رسالة حقيقية من العميل", len(agent.sent_fb) == 0, f"sent={len(agent.sent_fb)}")


def scenario_window_closed(conn, agent):
    print("\n6) نافذة 24 ساعة مغلقة → إيقاف نهائي بدون إرسال")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=25)
    _add_conv(conn, "chat_old", "sender_old", last_ts=(t0 + timedelta(minutes=5)).isoformat())
    _add_msg(conn, "chat_old", "customer", "كام السعر؟", t0.isoformat(), status="received")
    _add_msg(conn, "chat_old", "customer", "كام السعر؟", (t0 + timedelta(minutes=5)).isoformat(), status="sent")
    _run(agent)
    check("محادثة قديمة (>24 ساعة) لا تُرسل لها أي شيء", len(agent.sent_fb) == 0)


def scenario_night_defer(conn, agent):
    print("\n7) ساعات الليل [23:00-09:00): تأجيل FU1 لما بعد 9 صباحاً")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = datetime(2026, 8, 2, 18, 0, 0)  # 6 مساءً
    _add_button_chat(conn, "chat_night", "sender_night", WF.BUTTONS[0]["raw"], "أهلاً بحضرتك", t0)
    # FU1 مستحقة الساعة 9:05 مساءً — ليست في ساعات الليل (تبدأ 11 مساءً)
    FAKE_NOW = t0 + timedelta(hours=3, minutes=5)
    _run(agent)
    check("FU1 أُرسلت 9:05 مساءً (قبل بدء الليل 11 مساءً)", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    _reset(conn, agent)
    # سيناريو آخر: FU1 مستحقة في الليل (23:30) → تؤجَّل
    t0 = datetime(2026, 8, 2, 20, 0, 0)  # 8 مساءً — الزر والرد
    _add_button_chat(conn, "chat_n2", "sender_n2", WF.BUTTONS[0]["raw"], "أهلاً بحضرتك", t0)
    FAKE_NOW = datetime(2026, 8, 2, 23, 30, 0)  # 11:30 مساءً — FU1 مستحقة لكن ليلاً
    _run(agent)
    check("لا إرسال أثناء الليل (FU1 مؤجلة)", len(agent.sent_fb) == 0, f"sent={len(agent.sent_fb)}")
    FAKE_NOW = datetime(2026, 8, 3, 9, 10, 0)  # 9:10 صباحاً اليوم التالي
    _run(agent)
    check("بعد 9 صباحاً: FU1 تُرسل", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")


def scenario_customer_reply_resets(conn, agent):
    print("\n8) رد العميل النصي → إلغاء الفولو اب وإعادة العدّاد من جديد")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=4)
    _add_button_chat(conn, "chat_rep", "sender_rep", WF.BUTTONS[0]["raw"], "برنامج الـ١٥ يوم جاهز", t0)
    _run(agent)  # FU1 تُرسل (مرّت 4 ساعات)
    check("FU1 أُرسلت", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    # العميل يرد نصياً بعد FU1
    FAKE_NOW = t0 + timedelta(hours=4, minutes=30)
    _add_msg(conn, "chat_rep", "customer", "تمام شكراً، هل تشمل التأشيرة؟", FAKE_NOW.isoformat(), status="received")
    _add_conv(conn, "chat_rep", "sender_rep", last_ts=FAKE_NOW.isoformat())
    _run(agent)
    entry = _state().get("chats", {}).get("chat_rep", {})
    check("fu1/fu2 صُفِّرت (إعادة العدّاد)", entry.get("fu1_sent_at") is None and entry.get("fu2_sent_at") is None)
    check("لا FU2 فور رد العميل", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    # بعد 20 ساعة من رد العميل → لا FU2 (لأن fu1 صُفِّرت — الدورة الجديدة)
    FAKE_NOW = t0 + timedelta(hours=20, minutes=30)
    _run(agent)
    check("لا FU2 في نفس الدورة بعد الرد (إعادة العدّاد)", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    # ردّنا على استفساره + مرور 3 ساعات → FU1 تُرسل مرة أخرى (إجمالي 2)
    FAKE_NOW = t0 + timedelta(hours=4, minutes=35)
    _add_msg(conn, "chat_rep", "agent", "أكيد، التأشيرة شاملة بالطيران والإقامة", FAKE_NOW.isoformat(), status="sent")
    _add_conv(conn, "chat_rep", "sender_rep", last_ts=FAKE_NOW.isoformat())
    FAKE_NOW = t0 + timedelta(hours=8)
    _run(agent)
    check("دورة جديدة: FU1 تُرسل بعد 3 ساعات من ردّنا (إجمالي 2)",
          len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")
    # الحد الأقصى: لا يمكن إرسال أكثر من 2 إجمالاً
    FAKE_NOW = t0 + timedelta(hours=30)
    _run(agent)
    check("لا تتجاوز رسالتين إجمالاً مهما كانت الظروف", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")


def scenario_phone_received(conn, agent):
    print("\n9) رقم تليفون → وسم 'عميل جاهز للاتصال' + needs_help + إيقاف")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=4)
    _add_button_chat(conn, "chat_ph", "sender_ph", WF.BUTTONS[0]["raw"], "برنامج الـ١٥ يوم جاهز", t0)
    _run(agent)
    check("FU1 أُرسلت قبل الرقم", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    FAKE_NOW = t0 + timedelta(hours=4, minutes=30)
    _add_msg(conn, "chat_ph", "customer", "رقمي هو 01012345678 كلموني", FAKE_NOW.isoformat(), status="received")
    _add_conv(conn, "chat_ph", "sender_ph", last_ts=FAKE_NOW.isoformat())
    _run(agent)
    row = _conv_row(conn, "chat_ph")
    check("الرقم محفوظ في customer_phone", row[0] == "01012345678", str(row))
    check("needs_help=1 (إشعار فريق خدمة العملاء)", row[1] == 1, str(row))
    check("الوسم 'عميل جاهز للاتصال' مضاف", "عميل جاهز للاتصال" in _tags(conn, "chat_ph"), str(_tags(conn, "chat_ph")))
    check("لا رسالة رد للعميل عند استلام الرقم (بدون تأكيد نصي)",
          len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    FAKE_NOW = t0 + timedelta(hours=10)
    _run(agent)
    check("لا مزيد من الإرسالات بعد الرقم", len(agent.sent_fb) == 1)


def scenario_booking_deposit(conn, agent):
    print("\n10) العربون/تأكيد الحجز → تحويل لفريق الحجز + إيقاف")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=4)
    _add_button_chat(conn, "chat_bk", "sender_bk", WF.BUTTONS[0]["raw"], "برنامج الـ١٥ يوم جاهز", t0)
    _run(agent)
    FAKE_NOW = t0 + timedelta(hours=5)
    _add_msg(conn, "chat_bk", "customer", "تمام، حولت العربون دلوقتي", FAKE_NOW.isoformat(), status="received")
    _add_conv(conn, "chat_bk", "sender_bk", last_ts=FAKE_NOW.isoformat())
    _run(agent)
    row = _conv_row(conn, "chat_bk")
    check("needs_help=1 (تحويل لفريق الحجز)", row[1] == 1, str(row))
    check("السلسلة موقوفة (booking_intent)", _state().get("chats", {}).get("chat_bk", {}).get("stop_reason") == "booking_intent")
    check("لم تُرسل FU2 بعد العربون", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")


def scenario_optout_permanent(conn, agent):
    print("\n11) طلب عدم التواصل → اعتذار + إيقاف نهائي دائم")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=4)
    _add_button_chat(conn, "chat_oo", "sender_oo", WF.BUTTONS[0]["raw"], "برنامج الـ١٥ يوم جاهز", t0)
    _run(agent)
    FAKE_NOW = t0 + timedelta(hours=4, minutes=30)
    _add_msg(conn, "chat_oo", "customer", "متبعتليش تاني، مش مهتم", FAKE_NOW.isoformat(), status="received")
    _add_conv(conn, "chat_oo", "sender_oo", last_ts=FAKE_NOW.isoformat())
    _run(agent)
    check("رُسل اعتذار واحد", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")
    check("نص الاعتذار مطابق", agent.sent_fb[-1]["text"] == WF.MSG_OPTOUT_APOLOGY)
    check("الـ sender مُسجَّل في الإيقاف الدائم", "sender_oo" in _state().get("opted_out_senders", {}))
    # محادثة جديدة لنفس الـ sender من نفس الإعلان
    FAKE_NOW = t0 + timedelta(hours=6)
    _add_conv(conn, "chat_oo2", "sender_oo", last_ts=FAKE_NOW.isoformat())
    _add_msg(conn, "chat_oo2", "customer", "ابعتولي برنامج الـ١٥ يوم بالتفصيل 📋", FAKE_NOW.isoformat(), status="received")
    _add_msg(conn, "chat_oo2", "agent", "أهلاً بحضرتك، تفضل البرنامج", (FAKE_NOW + timedelta(minutes=1)).isoformat(), status="sent")
    _run(agent)
    check("لا تُرسل أي متابعة في المحادثة الجديدة (إيقاف دائم)", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")


def scenario_emoji_new_window(conn, agent):
    print("\n12) لايك/إيموجي فقط → رد طبيعي + إعادة دورة الفولو اب")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=4)
    _add_button_chat(conn, "chat_em", "sender_em", WF.BUTTONS[0]["raw"], "برنامج الـ١٥ يوم جاهز", t0)
    _run(agent)
    check("FU1 أُرسلت قبل الإيموجي", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    # العميل يرد بإيموجي فقط (لا رد من المساعد الأساسي بعده)
    FAKE_NOW = t0 + timedelta(hours=4, minutes=30)
    _add_msg(conn, "chat_em", "customer", "👍", FAKE_NOW.isoformat(), status="received")
    _add_conv(conn, "chat_em", "sender_em", last_ts=FAKE_NOW.isoformat())
    _run(agent)
    check("رُسل رد طبيعي على الإيموجي", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")
    check("نص الرد الطبيعي مطابق", agent.sent_fb[-1]["text"] == WF.MSG_EMOJI_REPLY)
    entry = _state().get("chats", {}).get("chat_em", {})
    check("دورة الفولو اب بدأت من جديد (fu1/fu2 صُفِّرت)",
          entry.get("fu1_sent_at") is None and entry.get("fu2_sent_at") is None)
    # إجمالي الفولو اب = 1 فقط (الرد الطبيعي ليس فولو اب)
    check("الرد الطبيعي لا يُحتسب من إجمالي الفولو اب", int(entry.get("total_fu_sent") or 0) == 1)

    # سيناريو: المساعد الأساسي ردّ فعلاً على الإيموجي → لا رد مزدوج
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=4)
    _add_button_chat(conn, "chat_em2", "sender_em2", WF.BUTTONS[0]["raw"], "برنامج الـ١٥ يوم جاهز", t0)
    _run(agent)
    FAKE_NOW = t0 + timedelta(hours=4, minutes=30)
    _add_msg(conn, "chat_em2", "customer", "❤️", FAKE_NOW.isoformat(), status="received", reaction_emoji="❤️")
    _add_msg(conn, "chat_em2", "agent", "تسلم يا فندم 🧡", (FAKE_NOW + timedelta(seconds=5)).isoformat(), status="sent")
    _add_conv(conn, "chat_em2", "sender_em2", last_ts=(FAKE_NOW + timedelta(seconds=5)).isoformat())
    _run(agent)
    check("لا رد مزدوج (المساعد الأساسي ردّ بالفعل)", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")


def scenario_fu2_after_23h(conn, agent):
    print("\n13) FU2 بعد مرور 23 ساعة → لا تُرسل (حد الـ 23 ساعة)")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=4)
    _add_button_chat(conn, "chat_f23", "sender_f23", WF.BUTTONS[0]["raw"], "برنامج الـ١٥ يوم جاهز", t0)
    _run(agent)  # FU1
    # 23.5 ساعة → نافذة الـ 24 ساعة لم تغلق بعد لكن FU2 لا تُرسل بعد 23 ساعة
    FAKE_NOW = t0 + timedelta(hours=23, minutes=30)
    _run(agent)
    check("لا FU2 بعد مرور 23 ساعة", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    # 24.5 ساعة → النافذة أغلقت نهائياً
    FAKE_NOW = t0 + timedelta(hours=24, minutes=30)
    _run(agent)
    entry = _state().get("chats", {}).get("chat_f23", {})
    check("النافذة أغلقت والسلسلة موقوفة", entry.get("stop_reason") == "window_closed", str(entry.get("stop_reason")))


def scenario_human_intervention(conn, agent):
    print("\n14) تدخّل موظف بشري (needs_help=1) → إيقاف بدون إرسال")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=4)
    _add_button_chat(conn, "chat_hi", "sender_hi", WF.BUTTONS[0]["raw"], "برنامج الـ١٥ يوم جاهز", t0)
    _run(agent)
    check("FU1 أُرسلت", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    _set_needs_help(conn, "chat_hi")
    _run(agent)
    check("لا إرسال بعد تدخّل بشري", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    check("السلسلة موقوفة (human_intervention)",
          _state().get("chats", {}).get("chat_hi", {}).get("stop_reason") == "human_intervention")


def scenario_referral_not_counted(conn, agent):
    print("\n15) رسالة الإحالة [Facebook Ad Referral] لا تُحتسب تفاعلاً")
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=1)
    _add_conv(conn, "chat_ref", "sender_ref", last_ts=(t0 + timedelta(minutes=5)).isoformat())
    _add_msg(conn, "chat_ref", "customer", "[Facebook Ad Referral] source=ADS type=OPEN_THREAD ad_id=120248067701970757", t0.isoformat(), status="received")
    _add_msg(conn, "chat_ref", "customer", "كام السعر؟", (t0 + timedelta(minutes=5)).isoformat(), status="received")
    _add_msg(conn, "chat_ref", "customer", "كام السعر؟", (t0 + timedelta(minutes=6)).isoformat(), status="sent")
    _run(agent)
    check("لا إرسال قبل 3 ساعات (الإحالة لا تحتسب تفاعلاً)", len(agent.sent_fb) == 0, f"sent={len(agent.sent_fb)}")


def scenario_first_message_stop(conn, agent):
    print("\n16) أول رسالة تحتوي رقم/عربون/انسحاب → معالجة فورية")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=1)
    # رقم في أول رسالة
    _add_conv(conn, "chat_fp", "sender_fp", last_ts=t0.isoformat())
    _add_msg(conn, "chat_fp", "customer", "رقمي 01234567890 ابعتلي التفاصيل", t0.isoformat(), status="received")
    _run(agent)
    row = _conv_row(conn, "chat_fp")
    check("الرقم محفوظ من أول رسالة", row[0] == "01234567890", str(row))
    check("needs_help=1", row[1] == 1)
    check("الوسم مضاف", "عميل جاهز للاتصال" in _tags(conn, "chat_fp"))
    # انسحاب في أول رسالة
    _add_conv(conn, "chat_fo", "sender_fo", last_ts=(t0 + timedelta(minutes=1)).isoformat())
    _add_msg(conn, "chat_fo", "customer", "مش مهتم، شيلني", (t0 + timedelta(minutes=1)).isoformat(), status="received")
    _run(agent)
    check("رُسل اعتذار على أول رسالة انسحاب",
          any(m["to"] == "sender_fo" and m["text"] == WF.MSG_OPTOUT_APOLOGY for m in agent.sent_fb))


def scenario_cycle_restart_refire(conn, agent):
    print("\n17) إعادة الدورة بعد الإيموجي: FU1 تُرسل من جديد (بحد أقصى 2 إجمالاً)")
    global FAKE_NOW
    _reset(conn, agent)
    t0 = FAKE_NOW - timedelta(hours=4)
    _add_button_chat(conn, "chat_cr", "sender_cr", WF.BUTTONS[0]["raw"], "برنامج الـ١٥ يوم جاهز", t0)
    _run(agent)
    check("FU1 الأولى أُرسلت", len(agent.sent_fb) == 1, f"sent={len(agent.sent_fb)}")
    # العميل يرد بإيموجي بعد FU1 → نافذة جديدة + رد طبيعي + دورة جديدة
    FAKE_NOW = t0 + timedelta(hours=4, minutes=30)
    _add_msg(conn, "chat_cr", "customer", "👍", FAKE_NOW.isoformat(), status="received")
    _add_conv(conn, "chat_cr", "sender_cr", last_ts=FAKE_NOW.isoformat())
    _run(agent)
    check("رُسل رد طبيعي على الإيموجي", len(agent.sent_fb) == 2, f"sent={len(agent.sent_fb)}")
    entry = _state().get("chats", {}).get("chat_cr", {})
    check("fu1/fu2 صُفِّرت (دورة جديدة)", entry.get("fu1_sent_at") is None and entry.get("fu2_sent_at") is None)
    check("إجمالي الفولو اب ما زال 1", int(entry.get("total_fu_sent") or 0) == 1)
    # بعد 3 ساعات من آخر رسالة (ردّنا الطبيعي) → FU1 تُرسل من جديد (الإجمالي 2)
    FAKE_NOW = t0 + timedelta(hours=7, minutes=45)
    _run(agent)
    check("FU1 تُرسل من جديد في الدورة الجديدة (إجمالي 2)", len(agent.sent_fb) == 3, f"sent={len(agent.sent_fb)}")
    entry = _state().get("chats", {}).get("chat_cr", {})
    check("إجمالي الفولو اب = 2", int(entry.get("total_fu_sent") or 0) == 2)
    # بعد 20 ساعة من الإيموجي → لا FU2 (السقف الكلي 2 مهما كانت الظروف)
    FAKE_NOW = t0 + timedelta(hours=24, minutes=30)
    _run(agent)
    check("لا FU2 بعد تجاوز السقف (2 إجمالاً)", len(agent.sent_fb) == 3, f"sent={len(agent.sent_fb)}")


def main():
    global PASS, FAIL, FAKE_NOW, WF
    tmpdir = tempfile.mkdtemp(prefix="umrah_15day_test_")
    db_file = os.path.join(tmpdir, "test_chat.db")
    state_file = os.path.join(tmpdir, "test_state.json")

    # تحميل الـ Workflow وتوجيهه لقاعدة الاختبار + ساعة وهمية
    spec = importlib.util.spec_from_file_location(
        "religious_15day_followup_test",
        os.path.join(BASE, "workflows", "religious_15day_followup.py"),
    )
    WF = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(WF)
    WF.DB_FILE = db_file
    WF.STATE_FILE = state_file
    WF._now = lambda: FAKE_NOW

    # توجيه chat_db إلى قاعدة الاختبار (حتى تُسجَّل الرسائل والتحديثات هناك)
    # + تثبيت ساعة chat_db على FAKE_NOW حتى تكون الطوابع الزمنية للرسائل
    # المسجّلة متسقة مع ساعة الـ Workflow الوهمية (بدون ذلك تختل مقارنات
    # "هل ردّ المساعد بعد كذا؟" لأن add_message يستخدم التوقيت الحقيقي).
    chat_db.DB_FILE = db_file
    chat_db.get_cairo_time = lambda: FAKE_NOW.isoformat()

    conn = _make_db(db_file)
    agent = MockAgent()

    print("=== اختبارات Workflow عمرة الـ١٥ يوم (الفولو اب) ===")
    scenario_activation_condition(conn, agent)
    scenario_normal_sequence_v1(conn, agent)
    scenario_button_versions(conn, agent)
    scenario_no_duplicate(conn, agent)
    scenario_last_customer_msg_no_fu1(conn, agent)
    scenario_window_closed(conn, agent)
    scenario_night_defer(conn, agent)
    scenario_customer_reply_resets(conn, agent)
    scenario_phone_received(conn, agent)
    scenario_booking_deposit(conn, agent)
    scenario_optout_permanent(conn, agent)
    scenario_emoji_new_window(conn, agent)
    scenario_fu2_after_23h(conn, agent)
    scenario_human_intervention(conn, agent)
    scenario_referral_not_counted(conn, agent)
    scenario_first_message_stop(conn, agent)
    scenario_cycle_restart_refire(conn, agent)

    conn.close()
    print(f"\n===== النتيجة: {PASS} نجحت / {FAIL} فشلت =====")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
