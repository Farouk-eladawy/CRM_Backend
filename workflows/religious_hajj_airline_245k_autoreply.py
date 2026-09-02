# -*- coding: utf-8 -*-
"""
Religious Auto-Reply — حملة "حج طيران — ٢٤٥ ألف" (٢٤٥ ألف بدل ٢٧٠ ألف)
========================================================================
المطلوب (من المدير — 2026-09-02):
  اعمل workflow باسم "حج طيران — ٢٤٥ ألف":
    - أول ما يبقى في رسالة بكلمة "حج طيران — ٢٤٥ ألف" بنسبة تطابق 100%
      (Exact Match كامل — ممنوع Contains / StartsWith / EndsWith)
    - رد عليها بـ 2 رسائل:
        رسالة ١: عرض حج طيران اقتصادي مع FTS 🕋 — ١٧ يوم، ٢٤٥ ألف بدل
                  ٢٧٠ ألف، الخصم لحد الخميس ١٧ سبتمبر ✅ (تذكرة الطيران
                  بتتضاف بسعرها وقت الحجز)، ليه الطيران؟ (من غير طريق ولا
                  عبّارة — طيران مباشر وقطار الحرمين بين المدينة ومكة،
                  وبنفس المخيمات والإشراف والوجبات)، خط السير كاملاً
                  (🕌 المدينة ٢–٥ ذو الحجة فندق بالمنطقة المركزية ٥ دقايق
                  للحرم / 🚄 قطار الحرمين السريع / 🕋 مكة ٦–٨ عمارة فندقية /
                  ⛺ المناسك ٩–١٣ مخيمات ألماني مكيّفة ٣ وجبات + سناكس
                  ومبيت مزدلفة ومنى على السنة / 🕋 العزيزية ١٤–١٧) +
                  ✅ مشرف مرافق من الشركة طول الرحلة + جدية الحجز
                  ٨٠٬١٥٠ جنيه بتتخصم من الإجمالي وتُسترد على بنك مصر لو ما
                  طلعتش في القرعة.
        رسالة ٢: النتيجة يوم ٣٠ سبتمبر + شرح تفاصيل الدفع والتقسيط وتثبيت
                  المكان بسعر الخصم في مكالمة دقيقتين (سؤال إغلاق: أكلم
                  حضرتك على أي رقم؟ 📞)
      (النص منسوخ حرفياً من طلب المدير بدون أي تعديل)

قرار هندسي حول الـ trigger:
  - الطلب "رد عليها" = رد لحظي على رسالة العميل الواردة ⇒
    trigger_type = "message_received" (نفس سلوك Workflows الردود اللحظية
    المعتمدة: Religious "حج بري — ٢٢٠ ألف" و "طيران تحسين — ٢٧٥ ألف"
    بتاريخ 2026-09-02 بنفس القالب الحرفي — أحدثها airline_tahseen_275k).
  - المطابقة بنسبة 100% تعني المساواة الكاملة (==) بعد إزالة الرموز غير
    الحرفية فقط — نفس المعنى المعتمد في workflow "طيران تحسين — ٢٧٥ ألف".

قواعد النظام المطبقة:
  - فلترة صارمة من الجذور: القسم الديني (Religious) فقط — لا نلمس أي قسم
    آخر (Hurghada / Sharm / Sales / Drivers) — قاعدة النظام 15.
  - احترام auto_reply_hold_until و needs_help (لا نتداخل مع موظف بشري).
  - منع التكرار الذري (Atomic Claim) ضد Webhook duplicate deliveries.
  - ملف الحالة المحلي JSON عبر fts_paths.get_data_path (يمنع استخدام
    agent.load_state/save_state — قاعدة النظام G).
  - مقارنة الوقت بتوقيت القاهرة عبر chat_db.get_cairo_time() وليس utcnow
    (قاعدة النظام F) — تستخدم في فحص auto_reply_hold_until.
  - لا حاجة لإعادة تشغيل السيرفر (hot-load عبر محرك الأتمتة) — لا نلمس
    ai_agent.py ولا ننشئ أي ملفات .bat — قاعدة النظام 10/11.
  - الاسم يحتوي "Religious" و "ديني" حتى يظهر في لوحة المدير الديني
    (قاعدة النظام D) ويبدأ بالاسم الذي طلبه المدير حرفياً: "حج طيران — ٢٤٥ ألف".
  - لا نعدّل أو نلغي أي Workflow قديم (مثل حملات حج طيران السابقة بأسعار
    أخرى أو حج بري) — حملة جديدة مستقلة بكلمة مفتاحية مختلفة (٢٤٥ بدل ٢٧٠).
"""
import os
import re
import json
import time
import logging
import hashlib
import sqlite3
from datetime import datetime, timedelta

from fts_paths import get_data_path

# =============================================================================
# ⚙️ الكلمة المفتاحية والردود الثابتة المعتمدة (تعدّل هنا فقط لإضافة/تعديل)
# =============================================================================
# IMPORTANT: النص منسوخ حرفياً من طلب المدير (2026-09-02) — مع الحفاظ على
# النص العربي والإيموجي وعلامات الترقيم والأرقام (العربية/اللاتينية) كما هي.

# رسالة ١: عرض حج طيران اقتصادي — ٢٤٥ ألف (الخصم لحد الخميس ١٧ سبتمبر)
MSG_HAJJ_AIRLINE_245K_OFFER = (
    "حج طيران اقتصادي مع FTS 🕋 — ١٧ يوم\n"
    "٢٤٥ ألف بدل ٢٧٠ ألف — الخصم لحد الخميس ١٧ سبتمبر ✅\n"
    "(تذكرة الطيران بتتضاف بسعرها وقت الحجز)\n"
    "\n"
    "ليه الطيران؟ من غير طريق ولا عبّارة — طيران مباشر وقطار الحرمين بين "
    "المدينة ومكة، وبنفس المخيمات والإشراف والوجبات.\n"
    "\n"
    "🕌 المدينة ٢–٥ ذو الحجة: فندق بالمنطقة المركزية، ٥ دقايق للحرم، إفطار وعشاء\n"
    "🚄 قطار الحرمين السريع من المدينة لمكة\n"
    "🕋 مكة ٦–٨: عمارة فندقية، إفطار وعشاء\n"
    "⛺ المناسك ٩–١٣: مخيمات ألماني مكيّفة، ٣ وجبات + سناكس، ومبيت مزدلفة ومنى على السنة\n"
    "🕋 العزيزية ١٤–١٧: إفطار وعشاء\n"
    "✅ مشرف مرافق من الشركة طول الرحلة\n"
    "\n"
    "جدية الحجز ٨٠٬١٥٠ جنيه بتتخصم من الإجمالي — وبتتسترد علي بنك مصر لو ما طلعتش في القرعة."
)

# رسالة ٢: النتيجة يوم ٣٠ سبتمبر + سؤال الإغلاق (مكالمة دقيقتين)
MSG_HAJJ_AIRLINE_245K_CLOSING = (
    "النتيجة يوم ٣٠ سبتمبر — يعني خلال أسابيع قليلة هتعرف إن شاء الله.\n"
    "\n"
    "خليني أشرحلك تفاصيل الدفع والتقسيط وأثبّتلك مكانك بسعر الخصم في مكالمة دقيقتين — أكلم حضرتك على أي رقم؟ 📞"
)

KEYWORDS = [
    {
        "keyword": "حج طيران — ٢٤٥ ألف",
        "replies": [MSG_HAJJ_AIRLINE_245K_OFFER, MSG_HAJJ_AIRLINE_245K_CLOSING],
        "enabled": True,   # مفعّلة
    },
]

# ملف الحالة الاحتياطي (يُستخدم فقط لو تعطلت قاعدة البيانات)
STATE_FILE = get_data_path("religious_hajj_airline_245k_autoreply_state.json")

# قاعدة بيانات الحالة الذرية (Atomic Dedup) - مستقلة تماماً عن أي سكربت آخر
# (ملف منفصل حتى لا نلمس dedup الخاص بأي workflow آخر — قاعدة النظام 8/12)
DEDUP_DB = get_data_path("religious_hajj_airline_245k_autoreply_dedup.db")

# أقصى عدد سجلات محفوظة في ملف الحالة الاحتياطي (منع نمو الملف بلا حدود)
MAX_STATE_RECORDS = 2000

# مهلة منع التكرار: إذا أُرسل نفس الرد لنفس المحادثة خلال هذه المدة نتجاهل (بالثواني)
# السبب: فيسبوك يُرسل أحياناً نفس رسالة العميل أكثر من مرة (Webhook duplicate deliveries)
# بنفس النص ومعرفات (mid) مختلفة، فنحتاج حماية ذرية تمنع الإرسال المتكرر.
DEDUP_WINDOW_SECONDS = 600

log = logging.getLogger("ReligiousHajjAirline245kAutoReply")


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
    (حذف [^\w\s]) بحيث تُعتبر "حج طيران — ٢٤٥ ألف" و
    "حج طيران — ٢٤٥ ألف." رسالة واحدة لنفس المحادثة خلال نافذة منع التكرار.
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
                CREATE TABLE IF NOT EXISTS religious_hajj_airline_245k_reply_dedup (
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
                cur.execute("DELETE FROM religious_hajj_airline_245k_reply_dedup WHERE replied_at < ?", (cutoff,))
            except Exception:
                pass
            # INSERT OR IGNORE: إذا كان المفتاح موجوداً بالفعل فلن يُدرج => منع التكرار
            cur.execute(
                "INSERT OR IGNORE INTO religious_hajj_airline_245k_reply_dedup (dedup_key, chat_id, replied_at, keyword) VALUES (?, ?, ?, ?)",
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
# المطابقة الدقيقة (Exact Keyword Match) - بنسبة تطابق 100% كما طلب المدير
# =============================================================================
def _normalize_for_match(text: str) -> str:
    """
    توحيد النص للمطابقة الدقيقة — نفس سلوك _normalize_for_match المعتمد في
    workflow "طيران تحسين — ٢٧٥ ألف" و "حج بري — ٢٢٠ ألف"
    (الموافق عليهما من المدير — 2026-09-02):
      - تحويل لحروف صغيرة
      - حذف التشكيل والتطويل (الـ → ال)
      - حذف الرموز غير الحرفية (إيموجي، نقاط، علامات استفهام/تعجب، الشرطات)
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
    المطابقة الدقيقة (EXACT — نسبة تطابق 100%):
    رسالة العميل يجب أن تساوي الكلمة المفتاحية بالكامل (مساواة كاملة == بعد
    إزالة الرموز غير الحرفية فقط — نفس منطق المحرك الرسمي المعتمد).
    - ممنوع Contains: أي كلمة إضافية قبل النص أو بعده تكسر المساواة → لا رد.
    - ممنوع StartsWith / EndsWith.
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
        # المساواة الكاملة (==) وليس الاحتواء — Exact Match بنسبة 100% بالظبط
        if normalized_message == normalized_keyword:
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
            # (قاعدة النظام F: مقارنة الوقت في الأتمتة يجب أن تكون بتوقيت القاهرة)
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


def _send_one(agent, text: str, source: str, sender_identifier: str, location: str,
              receiving_phone_id: str, chat_id: str) -> tuple:
    """
    إرسال رسالة واحدة عبر القناة الصحيحة (WhatsApp أو Facebook).
    تُرجع (channel, ok, error).
    """
    try:
        if str(source).lower() == "whatsapp" or str(sender_identifier).startswith("20"):
            channel = "WhatsApp"
            ok, error = agent.send_whatsapp_message(
                sender_identifier,
                text=text,
                location=location,
                receiving_phone_id=receiving_phone_id,
            )
        else:
            channel = "Facebook"
            ok, error = agent.send_facebook_message(sender_identifier, text=text)
    except Exception as e:
        ok = False
        error = str(e)
        log.error(f"Send error for chat {chat_id}: {e}")
    return channel, ok, error


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

    # ===== فلترة صارمة من الجذور: القسم الديني فقط (لا نلمس أي قسم آخر) =====
    # قاعدة النظام 15: عند تحديد نطاق العمل (Religious) يُمنع تماماً لمس أي
    # قسم آخر (Hurghada / Sharm / Sales / Drivers ...) — الفلتر هنا في أول السكربت.
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

    # ===== البحث عن الكلمة المفتاحية الدقيقة (Exact Match 100%) =====
    matched = _match_keyword(message_body)
    if not matched:
        # لا توجد كلمة مطابقة → يترك النظام الأساسي (AI) يتعامل مع الرسالة
        return {"ok": True, "skipped": "no_keyword_match", "chat_id": chat_id}

    replies = matched.get("replies") or []
    replies = [str(r).strip() for r in replies if str(r or "").strip()]
    if not replies:
        return {"ok": True, "skipped": "empty_reply", "chat_id": chat_id}

    # ===== منع التكرار (الحجز الذري) - بعد تحديد الكلمة وقبل الإرسال =====
    claimed = _claim_reply(chat_id, incoming_external_message_id, message_body, matched.get("keyword"))
    if not claimed:
        return {"ok": True, "skipped": "already_processed", "chat_id": chat_id}

    # ===== إرسال الرسائل بالتتابع (الرسالة ١ ثم الرسالة ٢) =====
    sent_count = 0
    errors = []
    last_channel = None
    for idx, text in enumerate(replies, start=1):
        channel, ok, error = _send_one(
            agent, text, source, sender_identifier, location,
            receiving_phone_id, chat_id,
        )
        last_channel = channel
        if ok:
            sent_count += 1
            # ===== تسجيل كل رسالة في سجل المحادثة =====
            try:
                import chat_db
                chat_db.add_message(
                    chat_id=chat_id,
                    sender_type="agent",
                    text=text,
                    status="sent",
                    source=channel,
                )
            except Exception as e:
                log.warning(f"Failed to log reply #{idx}: {e}")
        else:
            log.warning(f"Reply #{idx} failed for chat {chat_id}: {error}")
            errors.append({"index": idx, "error": str(error)[:300]})

    if sent_count == 0:
        return {
            "ok": False,
            "skipped": "send_failed",
            "chat_id": chat_id,
            "keyword": matched.get("keyword"),
            "errors": errors[:5],
        }

    # ===== عمليات ما بعد الإرسال الناجح (مرة واحدة) =====
    try:
        import chat_db
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
                    reason="religious_hajj_airline_245k_autoreply",
                )
        except Exception:
            pass
    except Exception as e:
        log.warning(f"Post-send cleanup failed: {e}")

    return {
        "ok": True,
        "sent": True,
        "sent_count": sent_count,
        "total_messages": len(replies),
        "chat_id": chat_id,
        "keyword": matched.get("keyword"),
        "channel": last_channel,
        "reply_preview": replies[0][:120],
        "errors": errors[:5],
    }


# =============================================================================
# اختبار ذاتي سريع (يُستخدم عند التطوير فقط — لا يُستدعى من المحرك)
# =============================================================================
if __name__ == "__main__":
    print("=== Self-test: religious_hajj_airline_245k_autoreply ===")
    tests = [
        ("حج طيران — ٢٤٥ ألف", True),
        ("حج طيران — ٢٤٥ ألف؟", True),
        ("حج طيران — ٢٤٥ ألف.", True),
        ("حج طيران - ٢٤٥ الف", False),   # ألف بدون همزة => لا تطابق (مطابقة 100% حرفية)
        ("حج طيران", False),              # بدون السعر => لا تطابق
        ("عايز تفاصيل حج طيران", False),  # أي كلمة إضافية تكسر المساواة
        ("طيران تحسين — ٢٧٥ ألف", False), # حملة أخرى => لا تتداخل
        ("حج بري — ٢٢٠ ألف", False),      # حملة أخرى => لا تتداخل
        ("السلام عليكم", False),
        ("", False),
    ]
    ok_all = True
    for msg, expected in tests:
        got = _match_keyword(msg) is not None
        flag = "✅" if got == expected else "❌"
        if got != expected:
            ok_all = False
        print(f"{flag} {msg!r:50} -> matched={got} expected={expected}")

    # فحص نص الرسالتين (العدد والتسلسل)
    kw = KEYWORDS[0]
    print("\n=== Keyword ===")
    print(repr(kw["keyword"]))
    print("=== Reply count:", len(kw["replies"]))
    for i, r in enumerate(kw["replies"], 1):
        print(f"\n----- MSG {i} (len={len(r)}) -----")
        print(r)
    print("\nALL OK" if ok_all else "SOME TESTS FAILED")
