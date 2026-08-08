"""
Workflow: 15 Days Exact Keyword Auto-Reply - عمرة ١٥ يوم (لحظي)
================================================================
Workflow جديد ومستقل 100% — لا يؤثر على "Religious Keyword Auto-Reply" الموجود.

الرد التلقائي اللحظي على رسائل عملاء القسم الديني (Religious) عندما تحتوي
الرسالة على إحدى الكلمات الثلاث المخصصة لبرنامج "عمرة ١٥ يوم" بالضبط
(Exact Keyword Matching) — كما طلب المدير حرفياً:
  - الكلمة لازم تكون "exact بالظبط" (مطابقة 100% على الكلمة نفسها)
  - حتى لو فيها إيموجي أو نقطة (نحذف الرموز غير الحرفية قبل المقارنة — نفس
    منطق المحرك الرسمي knowledge_base._normalize_rule_text)
  - بدون توحيد الهمزات (إ/أ/آ) أو الأرقام — مطابقة حرفية على الكلمة
  - بدون مطابقة مرنة أو تقريبية

المنطق:
  1) عند وصول أي رسالة جديدة من العميل (trigger: message_received):
     - يتم فحص نص الرسالة فوراً.
  2) القسم المستهدف: Religious فقط (فلترة صارمة - لا يمس أي قسم آخر).
  3) إذا احتوت الرسالة على إحدى الكلمات الثلاث (مطابقة دقيقة) →
     يُرسل الرد الجاهز الخاص بهذه الكلمة فوراً للعميل
     (متجاوزاً وضع الدرافت لأن الرد مُعتمد مسبقاً من الإدارة).
  4) يُسجَّل الرد في سجل المحادثة chat_history.db.
  5) حماية الحالة: حجز ذري (Atomic Claim) في قاعدة SQLite محلية مستقلة
     يمنع تكرار الإرسال حتى لو وصلت نفس رسالة العميل أكثر من مرة من فيسبوك
     (Webhook duplicate deliveries) أو من أكثر من تشغيل متزامن.

ملاحظات هندسية (لماذا هذه الشروط):
  - المطابقة دقيقة وحرفية (EXACT): نطابق على الكلمات الثلاث نفسها حرفياً
    بعد حذف الرموز غير الحرفية فقط (إيموجي، نقاط، علامات ترقيم) — تماماً
    كسلوك المحرك الرسمي "التطابق بالكلمة 100% حتى لو فيها إيموجي أو نقطة".
  - تم تخطي نافذة الـ 24 ساعة تلقائياً لأن هذا رد مباشر (RESPONSE)
    على رسالة العميل الواردة حالاً وليس رسالة برومو مستقلة.
  - احترام auto_reply_hold_until و needs_help: لا نتداخل مع موظف بشري.
  - تجاهل رسائل الميديا غير النصية (صوت/فيديو/ستيكر/مستند).
  - لا نلمس أي قواعد strict_qa_rules ولا knowledge.db إطلاقاً:
    كل الكلمات والردود معرفة هنا محلياً في هذا الملف (قائمة KEYWORDS).
"""

import os
import json
import re
import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta

from fts_paths import get_data_path

# =============================================================================
# ⚙️ الكلمات الثلاث والردود المعتمدة (تعدّل هنا فقط لإضافة/تعديل الكلمات)
# =============================================================================
# IMPORTANT: المدير طلب 3 كلمات. الكلمة 1 مؤكدة من الجلسات السابقة مع ردها
# المعتمد (الموجود فعلاً في chat_history.db وأُرسل للعملاء).
# الكلمتان 2 و3 لم تصلا في الرسائل السابقة (كانت تُقتطع) — أُضيفتا هنا
# كقوالب جاهزة (معطلة) حتى يعتمدها المدير، وعند اعتمادهما يكفي تفعيلهما.
KEYWORDS = [
    {
        "keyword": "ابعتولي برنامج الـ١٥ يوم بالتفصيل 📋",
        # الرد المعتمد الحرفي (مأخوذ من chat_history.db — رسالة agent حالة sent)
        "reply": (
            "أهلًا بحضرتك 🕋 اتفضل تفاصيل البرنامج:\n\n"
            "*عمرة ١٥ يوم بسعر ٤٠٬٩٥٠ جنيه شامل الطيران والتأشيرة والإقامة في مكة والمدينة والانتقالات* ✅\n\n"
            "✨ ١٥ يوم معناها إن حضرتك بتأدي العمرة براحتك ومن غير استعجال — وقت كافي للعبادة والطواف والصلاة من غير ضغط.\n\n"
            "🕌 *المدينة المنورة — إقامة فعلية ٣ ليالي مش مجرد زيارة:*\n"
            "فندق طيبة هيلز — أقل من ٥ دقايق مشي من الحرم النبوي\n"
            "يعني رايح جاي للروضة والصلوات على رجليك في أي وقت\n\n"
            "🕋 *مكة المكرمة — ١١ ليلة:*\n"
            "فندق منازل العين في امتداد شارع أجياد — باصات متوفرة طوال اليوم توصّلك الحرم في حوالي ٥ دقايق (المسافة ١٢٠٠ متر) — مرونة كاملة تروح وتيجي زي ما يناسبك\n\n"
            "✈️ *الطيران مباشر* على الخطوط السعودية أو مصر للطيران\n"
            "القاهرة ← المدينة المنورة، والعودة من جدة ← القاهرة\n"
            "يعني بتوصل المدينة على طول من غير مشقة طريق إضافي\n\n"
            "📅 مواعيد الرحلات:\n"
            "• ٢ سبتمبر (آخر معاد للحجز ٢٠ أغسطس)\n"
            "• ٢٣ سبتمبر\n"
            "• ١٤ أكتوبر\n\n"
            "أنسب لحضرتك رحلة ٢ سبتمبر، ولا ٢٣ سبتمبر، ولا ١٤ أكتوبر؟ 😊\n"
            "اختار الموعد المناسب، وأبعت لحضرتك خطوات الحجز وتفاصيل البرنامج كاملة."
        ),
        "enabled": True,   # مفعّلة
    },
    {
        "keyword": "إيه أقرب مواعيد السفر المتاحة؟ 🗓",
        # القاعدة 2 أُرسلت من جديد من المدير (2026-08-01) بالشكل الصحيح:
        #   الكلمة = إيه أقرب مواعيد السفر المتاحة؟ 🗓
        #   الرد   = عندنا ٢ مواعيد لبرنامج الـ١٥ يوم
        "reply": (
            "عندنا ٢ مواعيد لبرنامج الـ١٥ يوم"
        ),
        "enabled": True,   # مفعّلة
    },
    # ملاحظة: القاعدتان 2 و3 حُذفتا بناءً على طلب المدير (2026-08-01):
    # "احذف القاعده ال 2 و ال 3 علشان هبعتهملك من الاول" — المدير سيرسل
    # الكلمات والردود من جديد بالشكل الصحيح.
    # القاعدة 1 (ابعتولي برنامج الـ١٥ يوم بالتفصيل) ما زالت مفعّلة.
    # يمكن الاستعادة من النسخ الاحتياطية religious_15day_autoreply.py.bak-*
    # {
    #     "keyword": "الكلمة 3 هنا",
    #     "reply": "الرد 3 هنا",
    #     "enabled": False,
    # },
]

# ملف الحالة الاحتياطي (يُستخدم فقط لو تعطلت قاعدة البيانات)
STATE_FILE = get_data_path("religious_15day_autoreply_state.json")

# قاعدة بيانات الحالة الذرية (Atomic Dedup) - مستقلة عن سكربت الكلمات المفتاحية العام
DEDUP_DB = get_data_path("religious_15day_autoreply_dedup.db")

# أقصى عدد سجلات محفوظة في ملف الحالة الاحتياطي (منع نمو الملف بلا حدود)
MAX_STATE_RECORDS = 2000

# مهلة منع التكرار: إذا أُرسل نفس الرد لنفس المحادثة خلال هذه المدة نتجاهل (بالثواني)
# السبب: فيسبوك يُرسل أحياناً نفس رسالة العميل أكثر من مرة (Webhook duplicate deliveries)
# بنفس النص ومعرفات (mid) مختلفة، فنحتاج حماية ذرية تمنع الإرسال المتكرر.
DEDUP_WINDOW_SECONDS = 600

log = logging.getLogger("Religious15DayAutoReply")


# =============================================================================
# أدوات الحالة المحلية (State Management - يمنع استخدام agent.load_state)
# =============================================================================
def _load_state() -> dict:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception as e:
        log.error(f"Failed to load state: {e}")
    return {}


def _save_state(state: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
    except Exception as e:
        log.error(f"Failed to save state: {e}")


def _dedup_key(chat_id: str, external_id: str, message_body: str) -> str:
    """مفتاح تفرد احتياطي: معرف الرسالة الخارجي إن وُجد، وإلا chat_id + نص مختصر."""
    if external_id:
        return f"ext:{external_id}"
    return f"{chat_id}:{str(message_body or '')[:60]}"


def _normalize_body_for_dedup(message_body: str) -> str:
    r"""
    توحيد نص الرسالة لمنع التكرار فقط (وليس للمطابقة):
    يزيل الإيموجي وعلامات الترقيم والنقاط بنفس طريقة المحرك الرسمي
    (حذف [^\w\s]) بحيث تُعتبر "أقرب رحلة متاحة 🚀" و "أقرب رحلة متاحة."
    رسالة واحدة لنفس المحادثة خلال نافذة منع التكرار.
    ملاحظة: لا نوحّد الهمزات هنا أيضاً (مطابقة دقيقة حتى في منع التكرار).
    """
    try:
        s = str(message_body or "").strip().lower()
        # إزالة علامات التشكيل العربية والتطويل
        s = re.sub(r"[\u0610-\u061A\u0640\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)
        # إزالة كل ما ليس حرفاً أو رقماً (يمحو الإيموجي والترقيم)
        s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
        s = re.sub(r"\s+", " ", s, flags=re.UNICODE)
        return s.strip()
    except Exception:
        return str(message_body or "").strip()


# =============================================================================
# منع التكرار الذري (Atomic Claim) - يحل مشكلة السباق بين التشغيلات المتزامنة
# =============================================================================
def _ensure_dedup_table():
    """إنشاء جدول منع التكرار الذري إن لم يكن موجوداً."""
    try:
        with sqlite3.connect(DEDUP_DB, timeout=30.0) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS religious_15day_reply_dedup (
                    dedup_key TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    replied_at TEXT NOT NULL,
                    keyword TEXT
                )
                """
            )
            conn.commit()
    except Exception as e:
        log.error(f"Failed to init dedup table: {e}")


def _claim_reply(chat_id: str, external_id: str, message_body: str, keyword: str = None) -> bool:
    """
    محاولة حجز (Claim) حق الرد على هذه الرسالة بشكل ذري.
    تعيد True إذا كان هذا التشغيل هو الأول (يُسمح بالإرسال)،
    و False إذا كانت الرسالة مُعالجة بالفعل (يُمنع الإرسال المكرر).
    المفتاح الموحد يعتمد على المحادثة + النص المطبع (بدون إيموجي/ترقيم)
    وليس على mid المتغير من فيسبوك.
    """
    _ensure_dedup_table()
    # مفتاح موحد: chat_id + hash للنص المطبع (يتجاهل الإيموجي والنقاط)
    try:
        normalized = _normalize_body_for_dedup(message_body)
        body_hash = hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()[:24]
    except Exception:
        body_hash = "0" * 24
    unified_key = f"{chat_id}:{body_hash}"
    now = datetime.utcnow().isoformat()
    try:
        with sqlite3.connect(DEDUP_DB, timeout=30.0) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            cur = conn.cursor()
            # حذف السجلات القديمة (أقدم من النافذة) للحفاظ على صغر الجدول
            try:
                cutoff = (datetime.utcnow() - timedelta(seconds=DEDUP_WINDOW_SECONDS)).isoformat()
                cur.execute("DELETE FROM religious_15day_reply_dedup WHERE replied_at < ?", (cutoff,))
            except Exception:
                pass
            # INSERT OR IGNORE: إذا كان المفتاح موجوداً بالفعل فلن يُدرج => منع التكرار
            cur.execute(
                "INSERT OR IGNORE INTO religious_15day_reply_dedup (dedup_key, chat_id, replied_at, keyword) VALUES (?, ?, ?, ?)",
                (unified_key, str(chat_id or ""), now, str(keyword or "")),
            )
            conn.commit()
            claimed = cur.rowcount > 0
        return claimed
    except Exception as e:
        log.error(f"Failed to claim dedup: {e}")
        # في حال فشل قاعدة البيانات، نعود للملف الاحتياطي
        return _legacy_claim(chat_id, external_id, message_body)


def _legacy_claim(chat_id: str, external_id: str, message_body: str) -> bool:
    """حجز احتياطي عبر ملف JSON (لحالات تعطل قاعدة البيانات)."""
    state = _load_state()
    processed = state.get("processed", [])
    key = _dedup_key(chat_id, external_id, message_body)
    if key in processed:
        return False
    processed.append(key)
    if len(processed) > MAX_STATE_RECORDS:
        processed = processed[-MAX_STATE_RECORDS:]
    state["processed"] = processed
    _save_state(state)
    return True


# =============================================================================
# المطابقة الدقيقة (Exact Keyword) - نفس منطق المحرك الرسمي
# =============================================================================
def _normalize_for_match(text: str) -> str:
    """
    توحيد النص للمطابقة الدقيقة — نفس سلوك knowledge_base._normalize_rule_text:
      - تحويل لحروف صغيرة
      - حذف التشكيل والتطويل (الـ → ال)
      - حذف الرموز غير الحرفية (إيموجي، نقاط، علامات استفهام/تعجب)
      - توحيد المسافات
    ملاحظة: لا نوحّد الهمزات (إ/أ/آ) ولا الأرقام (0-9 / ٠-٩) — مطابقة 100% بالكلمة.
    """
    try:
        s = str(text or "").strip().lower()
        s = re.sub(r"[\u0610-\u061A\u0640\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)
        s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
        s = re.sub(r"\s+", " ", s, flags=re.UNICODE)
        return s.strip()
    except Exception:
        return str(text or "").strip().lower()


def _match_keyword(message_body: str):
    """
    يبحث عن أول كلمة مفتاحية (من قائمة KEYWORDS المفعلة) تظهر في نص الرسالة
    بشكل دقيق وحرفي بعد حذف الرموز غير الحرفية فقط.

    السبب (طلب المدير حرفياً): "الكلمة تكون exact بالظبط حتى لو فيها إيموجي
    أو نقطة" — أي أن المطابقة على الكلمة نفسها 100%، وليس تطابقاً مرناً.
    """
    normalized_message = _normalize_for_match(message_body)
    if not normalized_message:
        return None
    for entry in KEYWORDS:
        if not entry.get("enabled"):
            continue
        keyword = str(entry.get("keyword") or "").strip()
        if not keyword:
            continue
        normalized_keyword = _normalize_for_match(keyword)
        if not normalized_keyword:
            continue
        # مطابقة دقيقة: الكلمة المفتاحية حاضرة في الرسالة كاملة النص (بعد التنظيف)
        if normalized_keyword in normalized_message:
            return entry
    return None


# =============================================================================
# دوال مساعدة
# =============================================================================
def _is_non_text_media(message_body: str) -> bool:
    """هل الرسالة وسائط غير نصية (لا تحمل نصاً للمطابقة)؟"""
    lb = str(message_body or "").lower().strip()
    prefixes = (
        "[customer sent an audio message.",
        "[customer sent a video.",
        "[customer sent a sticker.",
        "[customer sent a document.",
        "[customer sent a message of type:",
        "[customer shared a location]",
        "[customer shared contacts.",
    )
    return any(lb.startswith(p) for p in prefixes)


def _is_human_active(chat_id: str) -> bool:
    """
    هل يوجد مساعد بشري نشط في المحادثة (needs_help=1)؟
    تمت إضافة هذا الشرط حتى لا يتعارض الرد الآلي مع تدخل الموظف البشري
    (نفس سلوك المسار الرئيسي: needs_help=1 يوقف الرد الآلي).
    """
    try:
        import chat_db
        conv = chat_db.get_conversation(chat_id) or {}
        try:
            return int(conv.get("needs_help") or 0) == 1
        except Exception:
            return False
    except Exception:
        return False


def _is_chat_on_hold(chat_id: str) -> bool:
    """هل أوقف إداري الرد الآلي لهذه المحادثة (auto_reply_hold_until)؟"""
    try:
        import chat_db
        conv = chat_db.get_conversation(chat_id) or {}
        hold_raw = str(conv.get("auto_reply_hold_until") or "").strip()
        if not hold_raw:
            return False
        try:
            # استخدام توقيت القاهرة (UTC+3) كما يخزنه النظام كله — لا نستخدم utcnow أبداً
            now = datetime.fromisoformat(chat_db.get_cairo_time())
            if now.tzinfo is not None:
                now = now.replace(tzinfo=None)
            hold_dt = datetime.fromisoformat(hold_raw)
            if hold_dt.tzinfo is not None:
                hold_dt = hold_dt.replace(tzinfo=None)
            # إذا كانت فترة الإيقاف ما زالت سارية → لا نرسل
            if hold_dt > now:
                return True
            # انتهت الفترة → نلغي الإيقاف ونسمح بالإرسال
            try:
                chat_db.update_auto_reply_hold_until(chat_id, None)
            except Exception:
                pass
        except Exception:
            return False
    except Exception:
        pass
    return False


# =============================================================================
# نقطة الدخول الرئيسية (يستدعيها محرك الأتمتة)
# =============================================================================
def run(agent, payload: dict = None) -> dict:
    """
    المعاملات (payload) قادمة من حدث message_received:
      chat_id, message_body, sender_identifier, source, location,
      receiving_phone_id, incoming_external_message_id
    """
    payload = payload or {}
    chat_id = str(payload.get("chat_id") or "").strip()
    message_body = str(payload.get("message_body") or "").strip()
    source = str(payload.get("source") or "").strip()
    sender_identifier = str(payload.get("sender_identifier") or "").strip()
    location = str(payload.get("location") or "").strip()
    receiving_phone_id = str(payload.get("receiving_phone_id") or "").strip() or None
    incoming_external_message_id = str(payload.get("incoming_external_message_id") or "").strip()

    # ===== فلترة صارمة: القسم الديني فقط (لا نلمس أي قسم آخر) =====
    if location.lower() != "religious":
        return {"ok": True, "skipped": "not_religious", "chat_id": chat_id}

    if not chat_id or not message_body or not sender_identifier:
        return {"ok": True, "skipped": "missing_data", "chat_id": chat_id}

    # ===== تجاهل رسائل الميديا غير النصية =====
    if _is_non_text_media(message_body):
        return {"ok": True, "skipped": "non_text_media", "chat_id": chat_id}

    # ===== احترام إيقاف الإداري للرد الآلي على هذه المحادثة =====
    if _is_chat_on_hold(chat_id):
        return {"ok": True, "skipped": "human_hold", "chat_id": chat_id}

    # ===== لا نتداخل مع مساعد بشري نشط (needs_help=1) =====
    if _is_human_active(chat_id):
        return {"ok": True, "skipped": "human_active", "chat_id": chat_id}

    # ===== البحث عن الكلمة المفتاحية الدقيقة =====
    matched = _match_keyword(message_body)
    if not matched:
        # لا توجد كلمة مطابقة → يترك النظام الأساسي (AI) يتعامل مع الرسالة
        return {"ok": True, "skipped": "no_keyword_match", "chat_id": chat_id}

    answer = str(matched.get("reply") or "").strip()
    if not answer:
        return {"ok": True, "skipped": "empty_reply", "chat_id": chat_id}

    # ===== منع التكرار (الحجز الذري) - بعد تحديد الكلمة وقبل الإرسال =====
    # الـ claim يعتمد على مفتاح موحد (chat_id + hash النص المطبع) وليس على
    # mid المتغير من فيسبوك، حتى لو وصلت نفس الرسالة أكثر من مرة خلال النافذة
    # الزمنية. كما يتجاهل الإيموجي والنقاط في النص لمنع التكرار.
    claimed = _claim_reply(chat_id, incoming_external_message_id, message_body, matched.get("keyword"))
    if not claimed:
        return {"ok": True, "skipped": "already_processed", "chat_id": chat_id}

    # ===== الإرسال الفوري عبر القناة الصحيحة =====
    channel = source if source else "Facebook"
    ok = False
    error = None
    try:
        if str(source).lower() == "whatsapp" or str(sender_identifier).startswith("20"):
            channel = "WhatsApp"
            ok, error = agent.send_whatsapp_message(
                sender_identifier,
                text=answer,
                location=location,
                receiving_phone_id=receiving_phone_id,
            )
        else:
            channel = "Facebook"
            ok, error = agent.send_facebook_message(sender_identifier, text=answer)
    except Exception as e:
        ok = False
        error = str(e)
        log.error(f"Send error: {e}")

    if not ok:
        log.warning(f"Send failed for chat {chat_id}: {error}")
        return {
            "ok": False,
            "skipped": "send_failed",
            "chat_id": chat_id,
            "keyword": matched.get("keyword"),
            "error": str(error)[:500],
        }

    # ===== تسجيل الرد في سجل المحادثة =====
    try:
        import chat_db
        chat_db.add_message(
            chat_id=chat_id,
            sender_type="agent",
            text=answer,
            status="sent",
            source=channel,
        )
        try:
            chat_db.mark_conversation_read(chat_id)
        except Exception:
            pass
        # منع سباق مسار الـ Debounce/AI: احذف أي مسودة وألغِ مؤقت الـ 10 ثوانٍ
        try:
            chat_db.delete_proposed_drafts(chat_id)
        except Exception:
            pass
        try:
            if agent and hasattr(agent, "cancel_whatsapp_ai_processing"):
                agent.cancel_whatsapp_ai_processing(
                    chat_id=chat_id,
                    reason="religious_15day_autoreply",
                )
        except Exception:
            pass
    except Exception as e:
        log.warning(f"Failed to log reply message: {e}")

    return {
        "ok": True,
        "sent": True,
        "chat_id": chat_id,
        "keyword": matched.get("keyword"),
        "channel": channel,
        "reply_preview": answer[:120],
    }
