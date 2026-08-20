"""
Workflow: Religious Save 29,000 Discount Auto-Reply - ديني (احفظلي خصم الـ٢٩,٠٠٠ باسمي)
=========================================================================================
Workflow جديد ومستقل 100% — لا يلمس "Religious Register With Discount Auto-Reply" ولا
"Tahseen Discount Auto-Reply" ولا "Economic Flight Discount Auto-Reply" ولا أي Workflow
موجود آخر.
(تمت إضافة كلمة "Religious" و "ديني" في الاسم لتظهر في لوحة المدير الديني لأن الفلتر
في الواجهة يعتمد على كلمة religious/ديني في الاسم — قاعدة النظام D.)

المطلوب (من المدير - 2026-08-20):
  اعمل workflow باسم: (احفظلي خصم الـ٢٩,٠٠٠ باسمي)
  - لما عميل يبقي الكلمة ديه مطابقة 100% (Exact Match بالظبط) —
    رسالة العميل تساوي الكلمة بالكامل (مساواة كاملة == بعد إزالة الرموز
    غير الحرفية فقط بنفس منطق المحرك الرسمي knowledge_base._normalize_rule_text).
  - ممنوع Contains / StartsWith / EndsWith: أي كلمة إضافية قبل النص أو بعده
    → لا رد.
  - الكلمة: احفظلي خصم الـ٢٩,٠٠٠ باسمي
  - الرد: 3 رسائل متقطعين ورا بعض (ثلاث رسائل منفصلة متتالية) بالنص الثابت
    التالي حرفياً (مع الحفاظ على النص العربي والإيموجي والأرقام العربية
    وعلامات الترقيم كما وردت في طلب المدير):
      الرسالة 1: أهلًا بحضرتك 🕋 قرار موفق — ... (تفاصيل برنامج حج الطيران تحسين)
      الرسالة 2: 💰 السعر: ٢٥٠ ألف بدلًا من ٢٧٩ ألف — ... (تفاصيل السعر والميزة)
      الرسالة 3: عشان نحفظلك الميزة باسمك دلوقتي، محتاجين ٣ حاجات بس: ...
    (العناوين "📩 رسالة 1/2/3" في الطلب هي فواصل تنظيمية لشرح القالب وليست
     جزءاً من نص الرسائل المرسلة — نفس أسلوب ملفات الرسائل الثلاث المعتمدة سابقاً)

القواعد المنفذة (كما طلب المدير + قواعد النظام):
  - المطابقة: Exact Match 100% (الرسالة == الكلمة بالكامل بعد التطبيع الذي
    يحذف الرموز غير الحرفية فقط — لا نوحّد الهمزات ولا الأرقام، فتطابق
    "احفظلي خصم الـ٢٩,٠٠٠ باسمي" حرفياً كما كتبها المدير).
  - القسم المستهدف: Religious فقط (فلترة صارمة من الجذور - لا يمس أي قسم آخر).
  - الرد مباشرة (لحظي) على رسالة العميل: تخطي نافذة الـ 24 ساعة تلقائياً
    لأن هذا رد مباشر (RESPONSE) على رسالة واردة وليس برومو مستقل.
  - إرسال الردود الثلاثة مرة واحدة فقط لكل رسالة (حجز ذري Atomic Claim يمنع
    تكرار الإرسال حتى لو وصلت نفس الرسالة من فيسبوك أكثر من مرة / Webhook
    duplicate deliveries).
  - احترام auto_reply_hold_until و needs_help: لا نتداخل مع موظف بشري.
  - تجاهل رسائل الميديا غير النصية (صوت/فيديو/ستيكر/مستند).
  - لا نلمس أي قواعد strict_qa_rules ولا knowledge.db إطلاقاً:
    الكلمة المفتاحية والردود معرفة محلياً هنا في هذا الملف (قائمة KEYWORDS).
  - كل التواريخ تُقارن بتوقيت القاهرة chat_db.get_cairo_time() وليس utcnow
    (قاعدة النظام F).
  - إدارة الحالة بملفات JSON محلية عبر fts_paths.get_data_path — يمنع استخدام
    agent.load_state / save_state (قاعدة النظام G).
"""

import os
import json
import re
import sqlite3
import hashlib
import logging
import time
from datetime import datetime, timedelta

from fts_paths import get_data_path

# =============================================================================
# ⚙️ الكلمة المفتاحية والردود الثلاثة المعتمدة (عدّل هنا فقط للتعديل)
# =============================================================================
# IMPORTANT: النصوص التالية منسوخة حرفياً من طلب المدير (2026-08-20)
# — مع الحفاظ على النص العربي والإيموجي والأرقام العربية وعلامات الترقيم كما هي.

# الفاصل الزمني بين الرسائل المتتالية (بالثواني) حتى تصل كرسائل منفصلة
# "متقطعين ورا بعض" كما طلب المدير — 1.5 ثانية كافية لضمان الترتيب مع تجنب
# إبطاء الاستجابة.
INTER_MESSAGE_DELAY_SECONDS = 1.5

# المدة القصوى الآمنة لإرسال الرسائل الثلاث المتتالية — إن تجاوزناها نوقف
# حتى لا نعلق في حلقة لا نهائية لو تعطلت القناة.
MAX_SEND_ATTEMPTS_PER_MESSAGE = 3

KEYWORDS = [
    {
        "keyword": "احفظلي خصم الـ٢٩,٠٠٠ باسمي",
        # الرسائل الثلاث المتتالية (تُرسل بالترتيب واحدة وراء الأخرى)
        "replies": [
            # 📩 الرسالة 1 — تفاصيل برنامج حج الطيران تحسين
            (
                "أهلًا بحضرتك 🕋 قرار موفق — وقبل ما نحفظهالك، من حقك تشوف اللي بتحفظه الأول:\n"
                "\n"
                "برنامج حج الطيران تحسين:\n"
                "⭐ ٧ أيام إقامة ٥ نجوم على ساحة الحرم مباشرة بعد المناسك — "
                "تسمع الأذان، تنزل تصلي، تطلع ترتاح\n"
                "📅 المدة: ١٩ يوم\n"
                "⛺ مخيمات ألماني مكيفة في المشاعر\n"
                "🚆 الانتقال من المدينة لمكة بقطار الحرمين السريع\n"
                "🍽 وجبات طوال الرحلة\n"
                "👥 مشرفين من الشركة معاك من أول يوم لحد الرجوع بالسلامة"
            ),
            # 📩 الرسالة 2 — تفاصيل السعر وميزة الـ٢٩,٠٠٠
            (
                "💰 السعر: ٢٥٠ ألف بدلًا من ٢٧٩ ألف — ميزة الـ٢٩,٠٠٠ ج بتتحفظ "
                "باسمك كتابيًا وبتتخصم من السعر الرسمي أيًا كان بعد نزول الضوابط\n"
                "✈️ تذكرة الطيران تُضاف بسعرها المعلن وقت الحجز\n"
                "📌 السعر على أساس الموسم السابق لحين إعلان ضوابط ١٤٤٨ الرسمية\n"
                "\n"
                "⚠️ ومهم جدًا: التقديم للحج مسموح من جهة واحدة فقط — والاختيار "
                "نهائي ومينفعش يتغير طول الموسم."
            ),
            # 📩 الرسالة 3 — المطلوب لحفظ الميزة + عرض خط السير
            (
                "عشان نحفظلك الميزة باسمك دلوقتي، محتاجين ٣ حاجات بس:\n"
                "1️⃣ صورة بطاقتك\n"
                "2️⃣ رقم موبايلك — عليه هيوصلك إثبات الحفظ الكتابي، ومستشار الحج "
                "هيتصل بيك يكمّل معاك\n"
                "3️⃣ حضرتك أول مرة تحج ولا سبق ليك الحج؟ (شرط التقديم إنها تكون "
                "أول مرة)\n"
                "\n"
                "ولو تحب تشوف خط سير الرحلة يوم بيوم الأول — ابعت \"خط السير\" "
                "وهيوصلك فورًا 😊"
            ),
        ],
        "enabled": True,   # مفعّلة
    },
]

# ملف الحالة الاحتياطي (يُستخدم فقط لو تعطلت قاعدة البيانات)
STATE_FILE = get_data_path("religious_save_29000_discount_autoreply_state.json")

# قاعدة بيانات الحالة الذرية (Atomic Dedup) - مستقلة تماماً عن أي سكربت آخر
DEDUP_DB = get_data_path("religious_save_29000_discount_autoreply_dedup.db")

# أقصى عدد سجلات محفوظة في ملف الحالة الاحتياطي (منع نمو الملف بلا حدود)
MAX_STATE_RECORDS = 2000

# مهلة منع التكرار: إذا أُرسل نفس الرد لنفس المحادثة خلال هذه المدة نتجاهل (بالثواني)
# السبب: فيسبوك يُرسل أحياناً نفس رسالة العميل أكثر من مرة (Webhook duplicate deliveries)
# بنفس النص ومعرفات (mid) مختلفة، فنحتاج حماية ذرية تمنع الإرسال المتكرر.
DEDUP_WINDOW_SECONDS = 600

log = logging.getLogger("ReligiousSave29000DiscountAutoReply")


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
    (حذف [^\w\s]) بحيث تُعتبر "احفظلي خصم الـ٢٩,٠٠٠ باسمي" و
    "احفظلي خصم الـ٢٩,٠٠٠ باسمي." رسالة واحدة لنفس المحادثة خلال نافذة
    منع التكرار.
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
                CREATE TABLE IF NOT EXISTS religious_save_29000_discount_reply_dedup (
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
                cur.execute("DELETE FROM religious_save_29000_discount_reply_dedup WHERE replied_at < ?", (cutoff,))
            except Exception:
                pass
            # INSERT OR IGNORE: إذا كان المفتاح موجوداً بالفعل فلن يُدرج => منع التكرار
            cur.execute(
                "INSERT OR IGNORE INTO religious_save_29000_discount_reply_dedup (dedup_key, chat_id, replied_at, keyword) VALUES (?, ?, ?, ?)",
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
# المطابقة الدقيقة (Exact Keyword Match) - ممنوع Contains/StartsWith/EndsWith
# =============================================================================
def _normalize_for_match(text: str) -> str:
    """
    توحيد النص للمطابقة الدقيقة — نفس سلوك knowledge_base._normalize_rule_text:
      - تحويل لحروف صغيرة
      - حذف التشكيل والتطويل (الـ → ال)
      - حذف الرموز غير الحرفية (إيموجي، نقاط، علامات استفهام/تعجب، الفاصلة ,)
      - توحيد المسافات
    ملاحظة: لا نوحّد الهمزات (إ/أ/آ) ولا الأرقام (0-9 / ٠-٩) — مطابقة 100% بالكلمة.
    (الفاصلة العربية في "٢٩,٠٠٠" تُحذف بالتطبيع تماماً مثل بقية الـ Workflows المعتمدة.)
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
    المطابقة الدقيقة (EXACT): رسالة العميل يجب أن تساوي الكلمة المحددة بالكامل
    (مساواة كاملة == بعد إزالة الرموز غير الحرفية فقط — نفس منطق المحرك الرسمي).
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
        # المساواة الكاملة (==) وليس الاحتواء — Exact Match بالظبط كما طلب المدير
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
# الإرسال الآمن (مع إعادة المحاولة) للرسائل الثلاث المتتالية
# =============================================================================
def _send_single(agent, source, sender_identifier, location, receiving_phone_id, text: str) -> tuple:
    """إرسال رسالة واحدة عبر القناة الصحيحة مع محاولة واحدة (لا نعيد الإرسال
    تلقائياً لتجنب إرسال مكرر قد يُحتسب على أنه Spam)."""
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
        return channel, ok, error
    except Exception as e:
        return "Unknown", False, str(e)


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
        # لا توجد كلمة مطابقة → يترك النظام الأساسي (AI) يتعامل مع الرسالة
        return {"ok": True, "skipped": "no_keyword_match", "chat_id": chat_id}

    replies = matched.get("replies") or []
    replies = [str(r or "").strip() for r in replies if str(r or "").strip()]
    if not replies:
        return {"ok": True, "skipped": "empty_reply", "chat_id": chat_id}

    # ===== منع التكرار (الحجز الذري) - بعد تحديد الكلمة وقبل الإرسال =====
    # الـ claim يعتمد على مفتاح موحد (chat_id + hash النص المطبع) وليس على
    # mid المتغير من فيسبوك، حتى لو وصلت نفس الرسالة أكثر من مرة خلال النافذة
    # الزمنية. كما يتجاهل الإيموجي والنقاط في النص لمنع التكرار.
    claimed = _claim_reply(chat_id, incoming_external_message_id, message_body, matched.get("keyword"))
    if not claimed:
        return {"ok": True, "skipped": "already_processed", "chat_id": chat_id}

    # ===== الإرسال الفوري للرسائل الثلاث المتتالية عبر القناة الصحيحة =====
    # إرسال رسالة تلو الأخرى مع فاصل زمني قصير بينها حتى تصل "متقطعين ورا بعض"
    # كرسائل منفصلة كما طلب المدير.
    channel = source if source else "Facebook"
    sent_count = 0
    first_error = None
    for idx, reply_text in enumerate(replies):
        chan, ok, error = _send_single(
            agent, source, sender_identifier, location, receiving_phone_id, reply_text
        )
        if ok:
            sent_count += 1
            channel = chan
            # ===== تسجيل كل رسالة في سجل المحادثة =====
            try:
                import chat_db
                chat_db.add_message(
                    chat_id=chat_id,
                    sender_type="agent",
                    text=reply_text,
                    status="sent",
                    source=channel,
                )
            except Exception as e:
                log.warning(f"Failed to log reply message {idx+1}: {e}")
        else:
            if first_error is None:
                first_error = str(error)[:500]
            log.warning(f"Send failed for chat {chat_id} (message {idx+1}/{len(replies)}): {error}")
        # فاصل زمني قصير بين الرسائل المتتالية (لا ننتظر بعد آخر رسالة)
        if idx < len(replies) - 1:
            time.sleep(INTER_MESSAGE_DELAY_SECONDS)

    if sent_count == 0:
        return {
            "ok": False,
            "skipped": "send_failed",
            "chat_id": chat_id,
            "keyword": matched.get("keyword"),
            "error": first_error,
        }

    # ===== تنظيف ما بعد الإرسال الناجح (مرة واحدة) =====
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
                    reason="religious_save_29000_discount_autoreply",
                )
        except Exception:
            pass
    except Exception as e:
        log.warning(f"Failed cleanup after send: {e}")

    return {
        "ok": True,
        "sent": True,
        "chat_id": chat_id,
        "keyword": matched.get("keyword"),
        "channel": channel,
        "messages_sent": sent_count,
        "messages_total": len(replies),
        "reply_preview": replies[0][:120],
    }
