"""
Workflow: 15 Days Exact Keyword Auto-Reply - Religious - عمرة ١٥ يوم (لحظي)
================================================================================
Workflow جديد ومستقل 100% — لا يعدّل ولا يحدّث أي Workflow موجود:
  - لا يلمس "Religious Keyword Auto-Reply - ديني (لحظي)" إطلاقاً.
  - لا يلمس religious_keyword_autoreply.py ولا religious_15day_autoreply.py.
  - هذا ملف مستقل جديد خاص بالردود الثلاثة التالية فقط (برنامج عمرة ١٥ يوم).

الرد التلقائي اللحظي على رسائل عملاء القسم الديني (Religious) فقط عندما تكون
رسالة العميل مطابقة حرفياً (Exact Match) لإحدى الكلمات الثلاث التالية:

  1) "ابعتولي برنامج الـ١٥ يوم بالتفصيل 📋"
  2) "إيه أقرب مواعيد السفر المتاحة؟ 🗓"
  3) "السعر ٤٠٬٩٥٠ شامل إيه بالظبط؟ 💰"

المطابقة (Exact Match — كما طلب المدير حرفياً):
  - يتم إرسال الرد فقط عندما تكون رسالة العميل مطابقة للكلمة المحددة بالكامل.
  - ممنوع Contains / StartsWith / EndsWith: نستخدم مساواة كاملة (==) وليس احتواء.
  - عدم تشغيل الرد عند وجود أي كلمة إضافية قبل النص أو بعده.
  - الحفاظ على النص العربي والإيموجي والأرقام وعلامات الترقيم كما هي.
  - إعطاء قواعد الـ Exact Match أولوية على أي ردود تلقائية عامة.
  - إرسال الرد المرتبط بالكلمة مرة واحدة فقط (حجز ذري Atomic Claim).
  - عدم تشغيل أكثر من رد على الرسالة نفسها.

ملاحظات هندسية (لماذا هذه الشروط):
  - التوحيد في _normalize_for_match يحذف فقط الرموز غير الحرفية (إيموجي،
    نقاط، علامات استفهام/تعجب) — نفس سلوك المحرك الرسمي knowledge_base.
    ثم نقارن بالمساواة الكاملة == (وليس in) لكي لا تنجح أي رسالة فيها كلمة
    إضافية قبل النص أو بعده. لا نوحّد الهمزات (إ/أ/آ) ولا الأرقام — حرفية 100%.
  - تم تخطي نافذة الـ 24 ساعة تلقائياً لأن هذا رد مباشر (RESPONSE) على رسالة
    العميل الواردة حالاً وليس رسالة برومو مستقلة.
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
KEYWORDS = [
    {
        "keyword": "ابعتولي برنامج الـ١٥ يوم بالتفصيل 📋",
        # الرد المعتمد الحرفي من المدير (2026-08-02)
        "reply": (
            "برنامج الـ١٥ يوم مقسّم كده:\n\n"
            "🕋 مكة المكرمة: ١١ ليلة في فندق منازل العين (امتداد أجياد) — والباصات شغالة طول اليوم لحد الحرم رايح جاي.\n\n"
            "🕌 المدينة المنورة: ٣ ليالي في فندق طيبة هيلز — أقل من ٥ دقايق مشي وحضرتك واقف قدام الحرم النبوي، يعني تصلي كل الفروض في الحرم من غير أي مشوار.\n\n"
            "✈️ الطيران: السعودية أو مصر للطيران — القاهرة / المدينة / جدة / القاهرة، يعني بتوصل المدينة على طول من غير أي طريق برّي.\n\n"
            "📄 والتأشيرة والإجراءات كلها علينا — حضرتك بس تجهزلنا صورة الباسبور (ساري ٦ شهور من تاريخ السفر) وصورة شخصية بخلفية بيضا.\n\n"
            "💰 والسعر يبدأ من ٤٠٬٩٥٠ ج شامل الطيران والتأشيرة والإقامة والانتقالات والزيارات والإشراف الكامل من فريق الشركة.\n\n"
            "والأماكن على رحلات سبتمبر بتتحجز بسرعة، فعشان نضمنلك مكانك من دلوقتي — حضرتك ناوي تسافر لوحدك ولا معاك حد؟ 😊"
        ),
        "enabled": True,
    },
    {
        "keyword": "إيه أقرب مواعيد السفر المتاحة؟ 🗓",
        # الرد المعتمد الحرفي من المدير (2026-08-02)
        "reply": (
            "عندنا ٢ مواعيد لبرنامج الـ١٥ يوم:\n\n"
            "🗓 ٢ سبتمبر\n"
            "🗓 ٢٣ سبتمبر\n\n"
            "والمواعيد كلها بنفس المميزات: إقامة في المدينة ٥ دقايق مشي بس من الحرم النبوي، وطيران مباشر للمدينة من غير أي طريق برّي.\n\n"
            "وبصراحة، رحلات الـ١٥ يوم بالذات بتتقفل بدري — فندق المدينة الطلب عليه عالي جدًا عشان قربه من الحرم، واللي بيحدد موعده بدري بيضمن مكانه وبيختار التسكين اللي يريحه قبل ما الغرف تتحجز.\n\n"
            "أنسب لحضرتك موعد ٢ سبتمبر ولا ٢٣ سبتمبر؟ 😊"
        ),
        "enabled": True,
    },
    {
        "keyword": "السعر ٤٠٬٩٥٠ شامل إيه بالظبط؟ 💰",
        # الرد المعتمد الحرفي من المدير (2026-08-02)
        "reply": (
            "سؤال ممتاز 🧡 السعر شامل كل حاجة من باب بيتك للحرم:\n\n"
            "✅ تذاكر الطيران ذهاب وعودة\n"
            "✅ التأشيرة والباركود وكل الإجراءات\n"
            "✅ الإقامة كاملة (١١ ليلة مكة + ٣ ليالي المدينة ٥ دقايق من الحرم)\n"
            "✅ كل الانتقالات الداخلية بباصات مكيفة\n"
            "✅ الزيارات والمزارات\n"
            "✅ إشراف كامل من فريق الشركة طول الرحلة\n\n"
            "يعني مفيش أي مصاريف مفاجئة — حضرتك بتدفع مرة واحدة وبتتفرغ للعبادة بس.\n\n"
            "والسعر بيختلف حسب التسكين:\n\n"
            "🔸 رباعي: ٤٠٬٩٥٠ ج للفرد\n"
            "🔸 ثلاثي: ٤٣٬١٠٠ ج للفرد\n"
            "🔸 ثنائي: ٤٧٬٤٠٠ ج للفرد\n\n"
            "والحجز أسهل ما يكون: ٥٠٪ عربون بس والباقي قبل السفر بأسبوعين — كاش في المقر أو تحويل بنكي أو إنستاباي 💳\n\n"
            "التسكين المناسب لحضرتك ثنائي ولا ثلاثي ولا رباعي؟ 😊"
        ),
        "enabled": True,
    },
]

# ملف الحالة الاحتياطي (يُستخدم فقط لو تعطلت قاعدة البيانات)
STATE_FILE = get_data_path("religious_15day_exact_autoreply_state.json")

# قاعدة بيانات الحالة الذرية (Atomic Dedup) - مستقلة تماماً عن باقي السكربتات
DEDUP_DB = get_data_path("religious_15day_exact_autoreply_dedup.db")

# أقصى عدد سجلات محفوظة في ملف الحالة الاحتياطي (منع نمو الملف بلا حدود)
MAX_STATE_RECORDS = 2000

# مهلة منع التكرار: إذا أُرسل نفس الرد لنفس المحادثة خلال هذه المدة نتجاهل (بالثواني)
# السبب: فيسبوك يُرسل أحياناً نفس رسالة العميل أكثر من مرة (Webhook duplicate deliveries)
# بنفس النص ومعرفات (mid) مختلفة، فنحتاج حماية ذرية تمنع الإرسال المتكرر.
DEDUP_WINDOW_SECONDS = 600

log = logging.getLogger("Religious15DayExactAutoReply")


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
                CREATE TABLE IF NOT EXISTS religious_15day_exact_reply_dedup (
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
                cur.execute("DELETE FROM religious_15day_exact_reply_dedup WHERE replied_at < ?", (cutoff,))
            except Exception:
                pass
            # INSERT OR IGNORE: إذا كان المفتاح موجوداً بالفعل فلن يُدرج => منع التكرار
            cur.execute(
                "INSERT OR IGNORE INTO religious_15day_exact_reply_dedup (dedup_key, chat_id, replied_at, keyword) VALUES (?, ?, ?, ?)",
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
# المطابقة الدقيقة (Exact Match) - مساواة كاملة وليست احتواء
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
    مطابقة دقيقة (Exact Match): تعيد الكلمة المفتاحية فقط إذا كانت رسالة
    العميل مطابقة للكلمة بالكامل (==) بعد حذف الرموز غير الحرفية فقط.

    الفرق عن النسخة السابقة: هنا نستخدم المساواة الكاملة == بدلاً من
    الاحتواء (in)، لذلك أي كلمة إضافية قبل النص أو بعده تمنع التطابق —
    وهذا هو المطلوب حرفياً من المدير ("ممنوع Contains / StartsWith / EndsWith").
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
        # Exact Match: مساواة كاملة وليست احتواء
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

    # ===== البحث عن الكلمة المفتاحية الدقيقة (Exact Match) =====
    matched = _match_keyword(message_body)
    if not matched:
        # لا توجد كلمة مطابقة بالكامل → يترك النظام الأساسي (AI) يتعامل مع الرسالة
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
                    reason="religious_15day_exact_autoreply",
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
