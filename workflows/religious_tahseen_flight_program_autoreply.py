"""
Workflow: برنامج حج طيران تحسين - Religious Auto-Reply - ديني (Exact Match لحظي)
=============================================================================================
طلب المدير (2026-08-27):
  - اعمل workflow باسم "برنامج حج طيران تحسين"
  - أول ما يبقى في رسالة بكلمة "برنامج حج طيران تحسين 👍" بنسبة تطابق 100%
    (Exact Match بالظبط)
  - رد عليها بـ 2 رسالة:
      رسالة ١: خط سير برنامج طيران تحسين (على أساس الموسم اللي فات):
               المدينة المنورة ٢-٥ ذو الحجة / قطار الحرمين / مكة ٦-٨ ذو الحجة /
               المناسك ٩-١٣ ذو الحجة / التحسين على ساحة الحرم ١٤-٢٠ ذو الحجة
      رسالة ٢ (بعدها بثانيتين): السعر ٢٥٠ ألف بدل ٢٧٩ بخصم الحجز المبكر +
               أولوية الخصم لمن يسجل ملفه من دلوقتي + تذكرة الطيران تُضاف وقت
               الحجز + سؤال الإغلاق (لو تحب أكلمك دقيقتين أشرحلك طرق الدفع
               والتقسيط — رقمك عليه واتساب؟)

القرارات الهندسية (مطابقة لنفس سلوك الـ Workflows المعتمدة:
religious_li_ana_autoreply / religious_lwaldy_aw_waldty_autoreply /
religious_with_you_autoreply):
  - "بنسبة تطابق 100%" = المطابقة الدقيقة (EXACT): رسالة العميل يجب أن تساوي
    الكلمة المفتاحية بالكامل (مساواة == بعد إزالة الرموز غير الحرفية فقط — نفس
    منطق المحرك الرسمي knowledge_base._normalize_rule_text).
    ملاحظة: الإيموجي "👍" الموجود في الكلمة المفتاحية هو رمز غير حرفي ويُحذف في
    التطبيع (مثل كل الإيموجي في النظام)، لذا لو كتب العميل الجملة بدون الإيموجي
    أو بإيموجي مختلف تظل تُطابق 100% — لكن أي كلمة إضافية (Contains) تكسر
    المساواة ولا تُطابق.
  - القسم المستهدف: Religious فقط (فلترة صارمة من الجذور - لا يمس أي قسم آخر).
  - trigger_type = "message_received" (رد لحظي مباشر على رسالة العميل الواردة).
  - الرد المباشر يخطي نافذة الـ 24 ساعة تلقائياً لأن هذا رد (RESPONSE) على رسالة
    عميل واردة وليس برومو مستقل (متوافق مع سياسات Meta).
  - إرسال الرد مرة واحدة فقط لكل رسالة (حجز ذري Atomic Claim يمنع تكرار الإرسال
    حتى لو وصلت نفس الرسالة من فيسبوك أكثر من مرة / Webhook duplicate deliveries).
  - الرد عبارة عن رسالتين: الأولى تُرسل فوراً، والثانية بعد ٢ ثانية (time.sleep(2))
    كما طلب المدير حرفياً "رسالة ٢ (بعدها بثانيتين)".
  - احترام auto_reply_hold_until و needs_help (لا نتداخل مع موظف بشري).
  - تجاهل رسائل الميديا غير النصية (صوت/فيديو/ستيكر/مستند).
  - كل تواريخ المقارنة تستخدم توقيت القاهرة chat_db.get_cairo_time() وليس utcnow
    (قاعدة النظام F — نظام FTS يخزن التوقيت كله بتوقيت القاهرة UTC+3).
  - إدارة الحالة عبر ملف JSON محلي + قاعدة بيانات Dedup مستقلة (لا نستخدم
    agent.load_state / save_state — قاعدة النظام G).
  - لا حاجة لإعادة تشغيل السيرفر: محرك الأتمتة يقرأ automation_workflows في كل
    tick (hot-load) — لا نلمس ai_agent.py إطلاقاً.
  - الملف مستقل 100%: لا يعدّل ولا يحذف أي Workflow أو سكربت آخر.
"""

import os
import json
import re
import time
import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta

from fts_paths import get_data_path

# =============================================================================
# ⚙️ الكلمة المفتاحية والردّان الثابتان المعتمدان (تعدّل هنا فقط)
# =============================================================================
# IMPORTANT: النص منسوخ حرفياً من طلب المدير (2026-08-27) — مع الحفاظ على
# النص العربي والإيموجي وعلامات الترقيم والأرقام كما هي تماماً.
KEYWORDS = [
    {
        "keyword": "برنامج حج طيران تحسين 👍",
        # رسالة ١: خط السير الكامل (كما وردت في الطلب حرفياً)
        "reply_1": (
            "أهلًا بحضرتك 🌿 حج مبرور إن شاء الله.\n"
            "ده خط سير برنامج طيران تحسين (على أساس الموسم اللي فات):\n"
            "\n"
            "🕌 المدينة المنورة — من ٢ إلى ٥ ذو الحجة\n"
            "إقامة قريبة من الحرم + إفطار وعشاء\n"
            "\n"
            "🚄 قطار الحرمين من المدينة لمكة\n"
            "\n"
            "🕋 مكة قبل المناسك — من ٦ إلى ٨ ذو الحجة\n"
            "إقامة فندقية + إفطار وعشاء\n"
            "\n"
            "⛺ المناسك — من ٩ إلى ١٣ ذو الحجة\n"
            "عرفات ومزدلفة ومنى، مخيمات مكيفة ووجبات ومشروبات، ومشرف الشركة معاك طول الوقت\n"
            "\n"
            "⭐ التحسين على ساحة الحرم — من ١٤ إلى ٢٠ ذو الحجة\n"
            "ودي أهم ميزة في البرنامج: بعد تعب المناسك، حضرتك بتكون على الحرم مباشرة، تنزل تصلي وترجع ترتاح، من غير باص ولا مشاوير."
        ),
        # رسالة ٢: السعر + أولوية الخصم + الطيران + سؤال الإغلاق (بعد ٢ ثانية)
        "reply_2": (
            "💰 السعر ٢٥٠ ألف بدل ٢٧٩ بخصم الحجز المبكر، على أساس الموسم اللي فات، "
            "والتأكيد بعد ضوابط الوزارة.\n"
            "والخصم ليه أولوية لمن يسجّل ملفه من دلوقتي.\n"
            "تذكرة الطيران بتتضاف بسعرها وقت الحجز.\n"
            "\n"
            "لو تحب أكلمك دقيقتين أشرحلك طرق الدفع والتقسيط — رقمك عليه واتساب؟"
        ),
        "delay_seconds": 2,  # "رسالة ٢ (بعدها بثانيتين)" كما طلب المدير
        "enabled": True,      # مفعّلة
    },
]

# ملف الحالة الاحتياطي (يُستخدم فقط لو تعطلت قاعدة البيانات)
STATE_FILE = get_data_path("religious_tahseen_flight_program_autoreply_state.json")

# قاعدة بيانات الحالة الذرية (Atomic Dedup) - مستقلة تماماً عن أي سكربت آخر
DEDUP_DB = get_data_path("religious_tahseen_flight_program_autoreply_dedup.db")

# أقصى عدد سجلات محفوظة في ملف الحالة الاحتياطي (منع نمو الملف بلا حدود)
MAX_STATE_RECORDS = 2000

# مهلة منع التكرار: إذا أُرسل نفس الرد لنفس المحادثة خلال هذه المدة نتجاهل (بالثواني)
# السبب: فيسبوك يُرسل أحياناً نفس رسالة العميل أكثر من مرة (Webhook duplicate deliveries)
# بنفس النص ومعرفات (mid) مختلفة، فنحتاج حماية ذرية تمنع الإرسال المتكرر.
DEDUP_WINDOW_SECONDS = 600

# مهلة إعادة محاولة إرسال الرسالة الثانية في حال فشلها (مرتان كحد أقصى)
# السبب: لو نجحت الرسالة الأولى وفشلت الثانية لسبب مؤقت (شبكة/توقيت) لا نترك
# العميل بدون رسالة السعر — نعيد المحاولة مرة واحدة بعد ثانيتين إضافيتين.
SEND_RETRY_DELAY_SECONDS = 2

log = logging.getLogger("ReligiousTahseenFlightProgramAutoReply")


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
    (حذف [^\w\s]) بحيث تُعتبر "برنامج حج طيران تحسين 👍" و
    "برنامج حج طيران تحسين" رسالة واحدة لنفس المحادثة خلال نافذة منع التكرار.
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
                CREATE TABLE IF NOT EXISTS religious_tahseen_flight_program_reply_dedup (
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
                cur.execute("DELETE FROM religious_tahseen_flight_program_reply_dedup WHERE replied_at < ?", (cutoff,))
            except Exception:
                pass
            # INSERT OR IGNORE: إذا كان المفتاح موجوداً بالفعل فلن يُدرج => منع التكرار
            cur.execute(
                "INSERT OR IGNORE INTO religious_tahseen_flight_program_reply_dedup (dedup_key, chat_id, replied_at, keyword) VALUES (?, ?, ?, ?)",
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
    توحيد النص للمطابقة الدقيقة — نفس سلوك knowledge_base._normalize_rule_text:
      - تحويل لحروف صغيرة
      - حذف التشكيل والتطويل (الـ → ال)
      - حذف الرموز غير الحرفية (إيموجي 👍، نقاط، علامات استفهام/تعجب، الشرطات)
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
    إزالة الرموز غير الحرفية فقط — نفس منطق المحرك الرسمي).
    - ممنوع Contains: أي كلمة إضافية قبل النص أو بعده تكسر المساواة → لا رد.
    - ممنوع StartsWith / EndsWith.
    ملاحظة: الإيموجي "👍" في الكلمة المفتاحية رمز غير حرفي يُحذف في التطبيع،
    لذا "برنامج حج طيران تحسين 👍" و"برنامج حج طيران تحسين" يطابقان معاً.
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


def _send_text(agent, source: str, sender_identifier: str, text: str,
               location: str, receiving_phone_id: str):
    """
    إرسال نص عبر القناة الصحيحة (واتساب/فيسبوك) مع تمييز القناة الفعلية.
    تعيد (ok, channel, error).
    """
    channel = source if source else "Facebook"
    try:
        if str(source).lower() == "whatsapp" or str(sender_identifier).startswith("20"):
            channel = "WhatsApp"
            ok, err = agent.send_whatsapp_message(
                sender_identifier,
                text=text,
                location=location,
                receiving_phone_id=receiving_phone_id,
            )
        else:
            channel = "Facebook"
            ok, err = agent.send_facebook_message(sender_identifier, text=text)
        return bool(ok), channel, str(err or "")
    except Exception as e:
        log.error(f"Send error: {e}")
        return False, channel, str(e)


def _log_reply(chat_id: str, text: str, channel: str):
    """تسجيل رسالة الرد في سجل المحادثة (بعد نجاح الإرسال الفعلي)."""
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
        log.warning(f"Failed to log reply message: {e}")


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

    reply_1 = str(matched.get("reply_1") or "").strip()
    reply_2 = str(matched.get("reply_2") or "").strip()
    if not reply_1 or not reply_2:
        return {"ok": True, "skipped": "empty_reply", "chat_id": chat_id}

    try:
        delay_seconds = max(0, int(matched.get("delay_seconds") or 2))
    except Exception:
        delay_seconds = 2

    # ===== منع التكرار (الحجز الذري) - بعد تحديد الكلمة وقبل الإرسال =====
    claimed = _claim_reply(chat_id, incoming_external_message_id, message_body, matched.get("keyword"))
    if not claimed:
        return {"ok": True, "skipped": "already_processed", "chat_id": chat_id}

    # ===== إرسال الرسالة الأولى (خط السير) فوراً =====
    ok1, channel1, err1 = _send_text(
        agent, source, sender_identifier, reply_1, location, receiving_phone_id
    )
    if not ok1:
        log.warning(f"Reply 1 send failed for chat {chat_id}: {err1}")
        return {
            "ok": False,
            "skipped": "send_failed",
            "chat_id": chat_id,
            "keyword": matched.get("keyword"),
            "error": f"reply_1: {str(err1)[:400]}",
        }
    _log_reply(chat_id, reply_1, channel1)

    # ===== انتظار ثانيتين ثم إرسال الرسالة الثانية (السعر) =====
    # تم إضافة هذا التأخير لتنفيذ طلب المدير حرفياً: "رسالة ٢ (بعدها بثانيتين)"
    time.sleep(delay_seconds)
    ok2, channel2, err2 = _send_text(
        agent, source, sender_identifier, reply_2, location, receiving_phone_id
    )
    if not ok2:
        # إعادة محاولة واحدة بعد ثانيتين إضافيتين حتى لا يترك العميل بدون رسالة السعر
        # (السبب: فشل مؤقت في الشبكة/التوقيت — والـ dedup يمنع إعادة إرسال الرسالة الأولى)
        log.warning(f"Reply 2 first attempt failed for chat {chat_id}: {err2} — retrying once")
        time.sleep(SEND_RETRY_DELAY_SECONDS)
        ok2, channel2, err2 = _send_text(
            agent, source, sender_identifier, reply_2, location, receiving_phone_id
        )
    if not ok2:
        log.warning(f"Reply 2 send failed for chat {chat_id}: {err2}")
        return {
            "ok": False,
            "sent": True,
            "partial": True,  # الرسالة الأولى أُرسلت والثانية فشلت
            "chat_id": chat_id,
            "keyword": matched.get("keyword"),
            "error": f"reply_2: {str(err2)[:400]}",
        }
    _log_reply(chat_id, reply_2, channel2)

    # ===== تنظيف حالة المحادثة بعد نجاح الرد الكامل =====
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
                    reason="religious_tahseen_flight_program_autoreply",
                )
        except Exception:
            pass
    except Exception as e:
        log.warning(f"Failed to cleanup chat state: {e}")

    return {
        "ok": True,
        "sent": True,
        "chat_id": chat_id,
        "keyword": matched.get("keyword"),
        "channel": channel1,
        "messages_sent": 2,
        "reply_1_preview": reply_1[:80],
        "reply_2_preview": reply_2[:80],
    }
