# -*- coding: utf-8 -*-
"""
اختبار شامل ومعزول (Isolated) — نسخة مستقلة للتحقق من Workflow حج طيران تحسين.
- لا يستخدم FTS_DATA_DIR إطلاقاً (تجنب تلوث get_data_path من ملفات الحالة الحقيقية).
- يعيد توجيه مسارات الوحدة (STATE_FILE / DB_FILE) و chat_db.DB_FILE لقاعدة مؤقتة.
- وقت مُتحكم فيه عبر استبدال wf._now.

الاستخدام: python test_hajj_tahseen_final.py
"""
import sys
import os
import json
import shutil
import sqlite3
import tempfile
import importlib.util
from datetime import datetime, timedelta

BASE = r"C:/Users/Aloosh2020/Downloads/New Project's/AIAgentProject/OpenClaw_Version"
sys.path.insert(0, BASE)

# تحميل الوحدة الحالية (آخر نسخة مستقرة)
SPEC = importlib.util.spec_from_file_location(
    "hajj_tahseen_final_test", os.path.join(BASE, "workflows", "hajj_tahseen_followup.py")
)
WF = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WF)

# ===== توجيه المسارات لقاعدة بيانات مؤقتة (عزل تام عن النظام الحقيقي) =====
TMP_BASE = tempfile.mkdtemp(prefix="hajj_final_test_")
DB_PATH = None
STATE_PATH = None
import chat_db


def fresh_env():
    """مجلد مؤقت جديد لكل سيناريو (تجنب قفل ملفات Windows بين السيناريوهات)."""
    global DB_PATH, STATE_PATH
    d = tempfile.mkdtemp(prefix="hajj_scn_", dir=TMP_BASE)
    DB_PATH = os.path.join(d, "chat_history.db")
    STATE_PATH = os.path.join(d, "state.json")
    WF.DB_FILE = DB_PATH
    WF.STATE_FILE = STATE_PATH
    chat_db.DB_FILE = DB_PATH
    return d

# وقت مُتحكم فيه (بتوقيت القاهرة)
NOW_BOX = {"now": None}
WF._now = lambda: NOW_BOX["now"]


def set_now(dt):
    NOW_BOX["now"] = dt


class MockAgent:
    def __init__(self):
        self.sent = []

    def send_facebook_message(self, recipient_psid, text=None, media_url=None, media_type=None):
        self.sent.append({"channel": "Facebook", "to": recipient_psid, "text": text})
        return True, "ok"

    def send_whatsapp_message(self, recipient_phone, text=None, location="Unknown", media_url=None,
                              media_type=None, template_name=None, template_language="en",
                              booking_data=None, template_variables=None, receiving_phone_id=None,
                              template_header_media_url=None, template_header_media_type=None):
        self.sent.append({"channel": "WhatsApp", "to": recipient_phone, "text": text})
        return True, "ok"


def make_db():
    d = fresh_env()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE conversations (
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
        )
        """
    )
    c.execute(
        """
        CREATE TABLE messages (
            msg_id TEXT PRIMARY KEY, chat_id TEXT, sender_type TEXT, text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT, source TEXT,
            external_message_id TEXT, reaction_to_external_message_id TEXT, reaction_emoji TEXT,
            staff_note TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE sales_customer_state (
            chat_id TEXT PRIMARY KEY, lead_status TEXT, priority TEXT, ai_priority TEXT,
            tags TEXT, ai_tags TEXT, lead_score INTEGER, follow_up_date TEXT, last_contact_date TEXT,
            next_action TEXT, ai_next_action TEXT, sales_notes TEXT, ai_sales_summary TEXT,
            is_starred INTEGER DEFAULT 0, reason_for_marking TEXT, assigned_sales_user TEXT,
            needs_ai_review INTEGER DEFAULT 0, overdue_followup INTEGER DEFAULT 0,
            ready_to_close INTEGER DEFAULT 0, updated_at TEXT, created_at TEXT
        )
        """
    )
    conn.commit()
    return conn


def add_conv(conn, chat_id, sender, ad_id=WF.TARGET_AD_ID, source="Facebook", last_ts=None,
             location="Religious", needs_help=0, is_closed=0):
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO conversations (chat_id, source, sender_identifier, contact_name, location,
                                   receiving_phone_id, last_message_time, facebook_ad_id,
                                   needs_help, is_closed, is_deleted)
        VALUES (?, ?, ?, '', ?, '', ?, ?, ?, ?, 0)
        """,
        (chat_id, source, sender, location, last_ts, ad_id, needs_help, is_closed),
    )
    conn.commit()


def add_msg(conn, chat_id, sender_type, text, ts, status="received", source="Facebook"):
    import uuid
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (msg_id, chat_id, sender_type, text, timestamp, status, source) VALUES (?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), chat_id, sender_type, text, ts, status, source),
    )
    c.execute("UPDATE conversations SET last_message_time = ? WHERE chat_id = ?", (ts, chat_id))
    conn.commit()


PASSED = 0
FAILED = 0
FAILURES = []


def check(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  PASS | {name}")
    else:
        FAILED += 1
        FAILURES.append(name)
        print(f"  FAIL | {name} | {detail}")


def run_wf(agent, **kw):
    return WF.run(agent, kw)


BASE_T = datetime(2026, 8, 2, 12, 0, 0)


def scenario_1_normal_sequence():
    print("\n== 1: التسلسل العادي (تهيئة أولاً ثم مراحل) ==")
    conn = make_db()
    agent = MockAgent()
    set_now(BASE_T)
    add_conv(conn, "cA", "1001")
    add_msg(conn, "cA", "customer", "[Facebook Ad Referral] source=ADS type=OPEN_THREAD ad_id=120246971083710757", (BASE_T - timedelta(hours=2.7)).isoformat())
    add_msg(conn, "cA", "customer", "تفاصيل البرنامج", (BASE_T - timedelta(hours=2.7)).isoformat())

    r1 = run_wf(agent)
    check("التشغيل الأول: تهيئة فقط بلا إرسال", r1.get("sent_count") == 0 and len(agent.sent) == 0, r1)

    r2 = run_wf(agent)
    check("المرحلة 1 بعد ساعتين (نص حرفي)", len(agent.sent) == 1 and agent.sent[0]["text"] == WF.MSG_STAGE1_NORMAL,
          [s["text"][:50] for s in agent.sent])

    r3 = run_wf(agent)
    check("لا تكرار لنفس المرحلة", len(agent.sent) == 1, agent.sent)

    # محاكاة مرور الوقت: المرحلة 2 بعد 8 ساعات من آخر رد
    set_now(BASE_T + timedelta(hours=8, minutes=10))
    r4 = run_wf(agent)
    check("المرحلة 2 بعد 8 ساعات", len(agent.sent) == 2 and agent.sent[1]["text"] == WF.MSG_STAGE2,
          [s["text"][:50] for s in agent.sent])

    # المرحلة 3 نافذتها [21,22) من آخر رد للعميل (آخر رد كان قبل 2.7 ساعة من BASE_T)
    # → النافذة عند now = BASE_T + 18.4h تقريباً (elapsed 21.1h)
    set_now(BASE_T + timedelta(hours=18, minutes=25))
    r5 = run_wf(agent)
    check("المرحلة 3 عند 21 ساعة (داخل نافذة 21-22)", len(agent.sent) == 3 and agent.sent[2]["text"] == WF.MSG_STAGE3,
          [s["text"][:50] for s in agent.sent])
    conn.close()


def scenario_2_hot_lead():
    print("\n== 2: الـ Lead الساخن (زرار إزاي أحجز؟) ==")
    conn = make_db()
    agent = MockAgent()
    set_now(BASE_T)
    add_conv(conn, "cB", "2002")
    add_msg(conn, "cB", "customer", "[Facebook Ad Referral] source=ADS type=OPEN_THREAD ad_id=120246971083710757", (BASE_T - timedelta(minutes=50)).isoformat())
    add_msg(conn, "cB", "customer", "إزاي أحجز؟", (BASE_T - timedelta(minutes=50)).isoformat())

    run_wf(agent)  # تهيئة
    r2 = run_wf(agent)
    check("المرحلة 1 للـ Hot بعد 45 دقيقة (محتوى الحجز)", len(agent.sent) == 1 and agent.sent[0]["text"] == WF.MSG_STAGE1_HOT,
          [s["text"][:60] for s in agent.sent])
    conn.close()


def scenario_3_other_ad():
    print("\n== 3: محادثة من إعلان آخر لا تُلمس ==")
    conn = make_db()
    agent = MockAgent()
    set_now(BASE_T)
    add_conv(conn, "cOther", "3003", ad_id="999999999999")
    add_msg(conn, "cOther", "customer", "تفاصيل", (BASE_T - timedelta(hours=3)).isoformat())
    run_wf(agent)
    run_wf(agent)
    check("لا إرسال لمحادثة من إعلان آخر", len(agent.sent) == 0, agent.sent)
    conn.close()


def scenario_4_meta_window():
    print("\n== 4: نافذة الـ 24 ساعة مغلقة (لم يبدأ التسلسل) ==")
    conn = make_db()
    agent = MockAgent()
    set_now(BASE_T)
    add_conv(conn, "cOld", "4004")
    add_msg(conn, "cOld", "customer", "تفاصيل البرنامج", (BASE_T - timedelta(hours=24, minutes=20)).isoformat())
    run_wf(agent)
    run_wf(agent)
    check("لا إرسال بعد 24 ساعة", len(agent.sent) == 0, agent.sent)
    # محادثة لم يبدأ تسلسلها تُحذف من الحالة (لا وسم)
    st = json.load(open(STATE_PATH, encoding="utf-8"))
    check("المحادثة المتأخرة تُحذف من الحالة", "cOld" not in st.get("chats", {}), st.get("chats", {}).keys())
    conn.close()


def scenario_5_no_response_tag():
    print("\n== 5: اكتمال التسلسل بدون رد → وسم no-response ==")
    conn = make_db()
    agent = MockAgent()
    set_now(BASE_T)
    add_conv(conn, "cTag", "5005")
    add_msg(conn, "cTag", "customer", "تفاصيل", (BASE_T - timedelta(hours=2.5)).isoformat())
    run_wf(agent)          # تهيئة
    run_wf(agent)          # المرحلة 1
    set_now(BASE_T + timedelta(hours=8))
    run_wf(agent)          # المرحلة 2 (elapsed 10.5h)
    set_now(BASE_T + timedelta(hours=19))
    run_wf(agent)          # المرحلة 3 (elapsed 21.5h داخل النافذة)
    # مرور الوقت حتى ما بعد 24 ساعة → الوسم
    set_now(BASE_T + timedelta(hours=23))
    run_wf(agent)
    st = json.load(open(STATE_PATH, encoding="utf-8"))
    entry = st["chats"]["cTag"]
    check("sequence_done=True بعد نافذة 24 ساعة", entry.get("sequence_done") is True, entry)
    check("tagged=True", entry.get("tagged") is True, entry)
    conn2 = sqlite3.connect(DB_PATH)
    row = conn2.execute("SELECT tags FROM sales_customer_state WHERE chat_id='cTag'").fetchone()
    check("الوسم no-response-hajj-tahseen في sales_customer_state", row and WF.TAG_NO_RESPONSE in (row[0] or ""), row)
    conn2.close()
    conn.close()


def scenario_6_keywords():
    print("\n== 6: الكلمات المفتاحية (ملخص / أحجز / رقم / إيقاف) ==")
    conn = make_db()
    agent = MockAgent()
    set_now(BASE_T)

    # F: ملخص
    add_conv(conn, "cSum", "6006")
    add_msg(conn, "cSum", "customer", "تفاصيل", (BASE_T - timedelta(hours=1)).isoformat())
    # G: أحجز
    add_conv(conn, "cBook", "6007")
    add_msg(conn, "cBook", "customer", "تفاصيل", (BASE_T - timedelta(hours=1)).isoformat())
    # H: رقم موبايل
    add_conv(conn, "cPhone", "6008")
    add_msg(conn, "cPhone", "customer", "تفاصيل", (BASE_T - timedelta(hours=1)).isoformat())
    # I: إيقاف
    add_conv(conn, "cStop", "6009")
    add_msg(conn, "cStop", "customer", "تفاصيل", (BASE_T - timedelta(hours=1)).isoformat())

    run_wf(agent)  # تهيئة الجميع

    set_now(BASE_T + timedelta(hours=1))
    add_msg(conn, "cSum", "customer", "ملخص", (BASE_T + timedelta(hours=1)).isoformat())
    add_msg(conn, "cBook", "customer", "أحجز", (BASE_T + timedelta(hours=1)).isoformat())
    add_msg(conn, "cPhone", "customer", "رقمي ٠١٠١٢٣٤٥٦٧٨", (BASE_T + timedelta(hours=1)).isoformat())
    add_msg(conn, "cStop", "customer", "متبعتليش تاني", (BASE_T + timedelta(hours=1)).isoformat())

    r = run_wf(agent)
    texts = [s["text"] for s in agent.sent]
    check("ملخص → يُرسل الملخص الكامل", any(t == WF.MSG_SUMMARY for t in texts), texts[:1])
    check("أحجز → تُرسل خطوات الحجز", any(t == WF.MSG_BOOKING_STEPS for t in texts), texts[:1])
    check("رقم → رسالة تسجيل وشكر", any(t == WF.MSG_PHONE_THANKS for t in texts), texts[:1])
    check("إيقاف → لا تُرسل رسالة", all(s["to"] != "6009" for s in agent.sent), agent.sent)

    conn2 = sqlite3.connect(DB_PATH)
    row = conn2.execute("SELECT needs_help FROM conversations WHERE chat_id='cBook'").fetchone()
    check("أحجز → تحويل لخدمة العملاء (needs_help=1)", row and row[0] == 1, row)
    row = conn2.execute("SELECT needs_help FROM conversations WHERE chat_id='cPhone'").fetchone()
    check("رقم → تحويل فوري (needs_help=1)", row and row[0] == 1, row)
    srow = conn2.execute("SELECT tags, customer_phone FROM conversations, sales_customer_state WHERE conversations.chat_id='cPhone' AND sales_customer_state.chat_id='cPhone'").fetchone()
    conn2.close()

    st = json.load(open(STATE_PATH, encoding="utf-8"))
    check("ملخص → إعادة ضبط العداد (highest=0)", st["chats"]["cSum"].get("highest_stage_sent") == 0, st["chats"]["cSum"])
    check("أحجز → handled=True", st["chats"]["cBook"].get("handled") is True, st["chats"]["cBook"])
    check("رقم → handled=True", st["chats"]["cPhone"].get("handled") is True, st["chats"]["cPhone"])
    check("إيقاف → opted_out=True", st["chats"]["cStop"].get("opted_out") is True, st["chats"]["cStop"])
    conn.close()


def scenario_7_reply_resets():
    print("\n== 7: رد العميل يعيد ضبط العداد ==")
    conn = make_db()
    agent = MockAgent()
    set_now(BASE_T)
    add_conv(conn, "cR", "7007")
    add_msg(conn, "cR", "customer", "تفاصيل", (BASE_T - timedelta(hours=2.5)).isoformat())
    run_wf(agent)  # تهيئة
    run_wf(agent)  # المرحلة 1
    check("المرحلة 1 أُرسلت", len(agent.sent) == 1, agent.sent)

    # العميل يرد بعد ساعة
    set_now(BASE_T + timedelta(hours=1))
    add_msg(conn, "cR", "customer", "عايز أعرف الأسعار", (BASE_T + timedelta(hours=1)).isoformat())
    run_wf(agent)
    st = json.load(open(STATE_PATH, encoding="utf-8"))
    check("الرد العادي يعيد ضبط العداد", st["chats"]["cR"].get("highest_stage_sent") == 0, st["chats"]["cR"])

    # بعد ساعتين من الرد الجديد → المرحلة 1 تُرسل من جديد (عداد جديد)
    set_now(BASE_T + timedelta(hours=3, minutes=10))
    run_wf(agent)
    check("المرحلة 1 تُحسب من الرد الجديد", len(agent.sent) == 2 and agent.sent[1]["text"] == WF.MSG_STAGE1_NORMAL,
          [s["text"][:40] for s in agent.sent])
    conn.close()


def scenario_8_verbatim():
    print("\n== 8: النصوص حرفية 100% من ملف التعليمات ==")
    exp1 = (
        "حضرتك لسه معانا؟ 🕋\n"
        "لو في أي سؤال محيّرك في برنامج طيران تحسين — عن الإقامة، أو المشاعر، أو طريقة الدفع — اكتبهولي وأنا أجاوبك فورًا.\n"
        "ولو حابب أبعتلك ملخص البرنامج كامل في رسالة واحدة، ابعت كلمة \"ملخص\" ✅"
    )
    exp2 = (
        "عارفين إن قرار الحج مش سهل، وإن حضرتك بتدور على شركة تطمنلها 🧡\n"
        "علشان كده حابين نقولك:\n"
        "✅ شركة FTS للسياحة مرخصة من وزارة السياحة فئة (أ) ترخيص رقم ٢٠٨٩\n"
        "✅ برنامج طيران تحسين كان من أكتر البرامج اللي حجاجنا شكرونا عليها الموسم اللي فات\n"
        "✅ معاك مشرفين من أول يوم لحد الرجوع بالسلامة\n"
        "لو حابب تعرف خطوات الحجز، ابعت كلمة \"أحجز\" وهنمشي معاك خطوة بخطوة."
    )
    exp3 = (
        "قبل ما اليوم يخلص حابين نفكر حضرتك 📌\n"
        "خصم الحجز المبكر (٢٩ ألف جنيه) مستمر لفترة محدودة، وأماكن برنامج طيران تحسين بتتحجز بسرعة لأن التأشيرات بعدد محدد.\n"
        "الحجز بيتم بـ ٥٠٪ مقدم بس، والباقي قبل السفر — وممكن تدفع كاش في مقر الشركة أو إيداع بنكي أو إنستاباي.\n"
        "لو حابب نحجزلك مكان أو نجاوبك على أي سؤال أخير، رد علينا دلوقتي وإحنا معاك ☎️\n"
        "ولو تحب نكلم حضرتك، ابعتلنا رقم الواتساب بتاعك وواحد من فريقنا هيتواصل معاك."
    )
    check("الرسالة 1 حرفية", WF.MSG_STAGE1_NORMAL == exp1, repr(WF.MSG_STAGE1_NORMAL))
    check("الرسالة 2 حرفية", WF.MSG_STAGE2 == exp2, repr(WF.MSG_STAGE2))
    check("الرسالة 3 حرفية", WF.MSG_STAGE3 == exp3, repr(WF.MSG_STAGE3))
    # الملخص يحتوي التفاصيل المعتمدة من التعليمات
    check("الملخص يشمل السعر ٢٥٠ ألف بدلًا من ٢٧٩", "٢٥٠" in WF.MSG_SUMMARY and "٢٧٩" in WF.MSG_SUMMARY, WF.MSG_SUMMARY[:150])
    check("الملخص يشمل ضوابط وزارة السياحة", "وزارة السياحة" in WF.MSG_SUMMARY, WF.MSG_SUMMARY[:150])
    check("خطوات الحجز تشمل المستندات", "جواز سفر" in WF.MSG_BOOKING_STEPS, WF.MSG_BOOKING_STEPS[:150])
    check("خطوات الحجز تشمل طرق الدفع", "إنستاباي" in WF.MSG_BOOKING_STEPS, WF.MSG_BOOKING_STEPS[:150])


def scenario_9_whatsapp():
    print("\n== 9: قناة واتساب ==")
    conn = make_db()
    agent = MockAgent()
    set_now(BASE_T)
    add_conv(conn, "cWA", "201001234567", source="WhatsApp")
    add_msg(conn, "cWA", "customer", "تفاصيل", (BASE_T - timedelta(hours=2.5)).isoformat(), source="WhatsApp")
    run_wf(agent)
    run_wf(agent)
    check("رسالة واتساب عبر send_whatsapp_message", len(agent.sent) == 1 and agent.sent[0]["channel"] == "WhatsApp", agent.sent)
    conn.close()


def scenario_10_needs_help_skip():
    print("\n== 10: محادثة needs_help=1 لا تُلمس ==")
    conn = make_db()
    agent = MockAgent()
    set_now(BASE_T)
    add_conv(conn, "cNH", "1010", needs_help=1)
    add_msg(conn, "cNH", "customer", "تفاصيل", (BASE_T - timedelta(hours=2.5)).isoformat())
    run_wf(agent)
    run_wf(agent)
    check("محادثة تحت إشراف بشري لا تُرسل لها رسائل", len(agent.sent) == 0, agent.sent)
    conn.close()


if __name__ == "__main__":
    try:
        scenario_8_verbatim()
        scenario_1_normal_sequence()
        scenario_2_hot_lead()
        scenario_3_other_ad()
        scenario_4_meta_window()
        scenario_5_no_response_tag()
        scenario_6_keywords()
        scenario_7_reply_resets()
        scenario_9_whatsapp()
        scenario_10_needs_help_skip()
    finally:
        shutil.rmtree(TMP_BASE, ignore_errors=True)

    print("\n========================================")
    print(f"PASSED: {PASSED} | FAILED: {FAILED}")
    if FAILURES:
        print("FAILED:", FAILURES)
        sys.exit(1)
    print("ALL TESTS PASSED ✅")
    sys.exit(0)
