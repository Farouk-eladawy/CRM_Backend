# -*- coding: utf-8 -*-
"""
Workflow: Religious Umrah 10-Day Follow-Up - ديني - برنامج العمرة المريح ١٠ أيام
===============================================================================
نظام المتابعة التلقائية (Follow-Up) لبرنامج "العمرة المريح ١٠ أيام" على
فيسبوك ماسنجر — إعادة تنشيط العملاء الصامتين داخل نافذة الـ 24 ساعة وتحويلهم
لحجز أو الحصول على رقم تليفون/واتساب قبل انتهاء النافذة.

شرط التفعيل (فلترة صارمة من الجذور في SQL - لا نلمس أي إعلان أو قسم آخر):
    WHERE facebook_ad_id = '120248068201650757'
    AND (is_deleted IS NULL OR is_deleted = 0)

نظام الجدولة — دورة فحص كل ٦٠ دقيقة (مُسجَّلة في automation_workflows):
    - متابعة ١: مرّ ٦٠ دقيقة أو أكثر على آخر رسالة (عميل أو رد منّا)،
      ولم تُرسل متابعة ١ بعد.
    - متابعة ٢: مرّ ٧ ساعات أو أكثر على آخر رسالة من العميل، وأُرسلت
      متابعة ١، ولم تُرسل متابعة ٢ بعد.
    - متابعة ٣: مرّ ٢٢ ساعة أو أكثر على آخر رسالة من العميل (قبل إغلاق
      نافذة الـ ٢٤ ساعة)، وأُرسلت متابعة ٢، ولم تُرسل متابعة ٣ بعد.
    - كل رسالة تُرسل مرة واحدة فقط بالترتيب ١ ← ٢ ← ٣ (لا تكرار ولا تخطي).
    - بعد مرور ٢٤ ساعة من آخر رسالة من العميل → إيقاف الإرسال نهائياً.

قاعدة ساعات الليل (١٢ منتصف الليل - ٨ صباحاً بتوقيت القاهرة):
    - إذا وقع موعد الإرسال بين ١٢ منتصف الليل و٨ صباحاً → يُؤجَّل الإرسال
      لأول دورة فحص بعد الساعة ٨ صباحاً، بشرط ألا تتجاوز نافذة الـ ٢٤ ساعة.
    - استثناء وحيد: إذا كانت النافذة ستُغلق قبل ٨ صباحاً → تُرسل رسالة
      المتابعة ٣ فوراً بغضّ النظر عن الوقت (لأنها آخر فرصة قبل إغلاق النافذة).

شروط الإيقاف الفوري (Stop Conditions):
    1) العميل ردّ بأي رسالة → إيقاف السلسلة (المساعد الأساسي يتعامل مع رسالته).
    2) العميل أرسل رقم تليفون/واتساب → تسجيل الرقم في customer_phone + إشعار
       فوري للفريق البشري (needs_help=1 + رسالة System Log) + إيقاف السلسلة.
       (تحديث المدير 2026-08-02: لا تُرسل رسالة رد للعميل عند استلام الرقم —
       لا نص "وصلنا رقم حضرتك" خالصاً؛ المساعد الأساسي/الفريق البشري يرد عليه.)
    3) العميل أكّد الحجز أو طلب إجراءات الحجز → تحويله لمسار الحجز
       (needs_help=1 + رسالة System Log) + إيقاف السلسلة.
    4) العميل طلب عدم التواصل أو أظهر انزعاجاً → اعتذار لطيف برسالة واحدة
       قصيرة + إيقاف نهائي، ولا نرسل له أي شيء آخر حتى لو بدأ محادثة جديدة
       من نفس الإعلان (سجل opt-out بالـ sender_identifier).
    5) تدخّل موظف بشري (needs_help=1 أو is_closed=1) → إيقاف السلسلة.

ملاحظات هندسية (لماذا هذه الشروط):
    - التوقيت: نستخدم chat_db.get_cairo_time() (توقيت القاهرة UTC+3) كما يفعل
      النظام بالكامل، ولا نستخدم datetime.now(timezone.utc) إطلاقاً لمنع
      انحراف 3 ساعات في منطق المراحل (قاعدة النظام F).
    - الحالة: يُمنع استخدام agent.load_state/save_state (غير موجودة على الـ
      agent في run_script)، لذا نستخدم ملف JSON محلي عبر fts_paths.get_data_path
      (قاعدة النظام G) لمنع التكرار اللانهائي وإعادة الإرسال.
    - نصوص الرسائل الثلاث تُرسل كما هي بالحرف (لا نعيد صياغتها).
    - رسالة "وصلنا رقم حضرتك" أُلغي إرسالها تماماً حسب تحديث المدير
      2026-08-02 — عند استلام رقم العميل نكتفي بالتسجيل والإشعار والإيقاف.
    - حد أقصى للإرسال في كل تشغيل (MAX_SENDS_PER_RUN) حتى لا تتجاوز مدة
      التشغيل timeout الـ http_request (60 ثانية) — التشغيل التالي يكمل الباقي
      لأن الحالة محفوظة فور كل إرسال.
    - تحسين الأداء: نفلتر المحادثات من الجذور في SQL (facebook_ad_id + نافذة
      زمنية 25 ساعة على last_message_time) بدلاً من جلب كل محادثات الإعلان
      وفلترتها برمجياً (قاعدة النظام 10-7).
"""

import os
import json
import re
import sqlite3
import logging
from datetime import datetime, timedelta

from fts_paths import get_data_path

# =============================================================================
# ثوابت السير العمل
# =============================================================================
# الإعلان المستهدف فقط (شرط التفعيل الحصري — Ad ID من طلب المدير)
TARGET_AD_ID = "120248068201650757"

# قاعدة بيانات المحادثات (نفس مسار chat_db)
DB_FILE = get_data_path("chat_history.db")

# ملف الحالة المحلي (قاعدة النظام G: يُمنع agent.load_state)
STATE_FILE = get_data_path("religious_umrah_10day_followup_state.json")

# عتبات التوقيت (حسب جدول المدير حرفياً)
STAGE1_MINUTES = 60.0            # المتابعة 1 بعد 60 دقيقة من آخر رسالة
STAGE2_HOURS = 7.0               # المتابعة 2 بعد 7 ساعات من آخر رسالة عميل
STAGE3_HOURS = 22.0              # المتابعة 3 بعد 22 ساعة (قبل إغلاق النافذة)
WINDOW_HOURS = 24.0              # نافذة Meta الكاملة من آخر رسالة عميل

# ساعات الليل الصامتة (بتوقيت القاهرة): من 12 منتصف الليل حتى 8 صباحاً
QUIET_START_HOUR = 0
QUIET_END_HOUR = 8

# حد أقصى للإرسال في كل تشغيل (حتى لا يتجاوز timeout الـ http_request)
MAX_SENDS_PER_RUN = 20

log = logging.getLogger("ReligiousUmrah10DayFollowup")

# =============================================================================
# نصوص الرسائل (كما هي بالحرف من برومبت المدير — لا تغيير ولا إعادة صياغة)
# =============================================================================
# 🟢 رسالة المتابعة ١ — بعد ٦٠ دقيقة
MSG_STAGE1 = (
    "حضرتك لسه معانا؟ 🕋\n"
    "عشان نوفر وقت حضرتك، ابعتلنا بس عدد المسافرين ونبعت لحضرتك أقرب موعد متاح ونحجزلك مكانك مبدئيًا من غير أي التزام.\n"
    "ولو عندك أي سؤال — حتى لو صغير — اسأل براحتك، إحنا هنا 🧡"
)

# 🟡 رسالة المتابعة ٢ — بعد ٧ ساعات
MSG_STAGE2 = (
    "غالبًا حضرتك بتفكر أو بتستشير حد من العيلة — ودي أصلًا الطريقة الصح لقرار زي ده 🙏\n"
    "عشان نسهّل عليك: أكتر حاجتين بيسأل عنهم عملاؤنا قبل الحجز:\n"
    "١- الفنادق: الماسة جراند خلف برج الساعة (٥ دقايق مشي للحرم) وأوديست بالمدينة (أقل من ٥ دقايق للحرم النبوي) — ودوّر عليهم بنفسك على جوجل.\n"
    "٢- السعر ٥١,٥٠٠ ج شامل الطيران والتأشيرة والإقامة وقطار الحرمين — مفيش أي رسوم بتظهر بعدين.\n"
    "لو فيه سؤال تالت واقف معاك، قولّي عليه وأنا أجاوبك حالًا ✅"
)

# 🔴 رسالة المتابعة ٣ — بعد ٢٢ ساعة (قبل إغلاق النافذة)
MSG_STAGE3 = (
    "آخر رسالة من طرفنا وعدًا 🤝\n"
    "الأماكن على أقرب رحلة بتتحجز بترتيب تأكيد الحجز، والحجز بيتم بـ٥٠٪ فقط والباقي قبل السفر بأسبوعين.\n"
    "عشان نوفر على حضرتك — ابعتلنا رقم تليفونك أو الواتساب بتاعك، وواحد من فريقنا هيكلمك بنفسه يجاوبك على أي سؤال ويقولك أقرب المواعيد المتاحة، من غير أي التزام عليك.\n"
    "ولو الوقت مش مناسب دلوقتي، إحنا موجودين دايمًا — وربنا يكتبلك زيارة بيته قريب 🕋🧡"
)

# نص "وصلنا رقم حضرتك" — محفوظ للتوثيق فقط (أُلغي إرساله نهائياً حسب
# تحديث المدير 2026-08-02: لا نرسل أي رد للعميل عند استلام رقمه)
MSG_PHONE_CONFIRM = (
    "وصلنا رقم حضرتك ✅ هيتواصل معاك أحد فريقنا خلال دقايق بإذن الله. لو تحب المكالمة في وقت معين، قولنا الوقت المناسب ليك 🧡"
)

# اعتذار لطيف عند طلب العميل عدم التواصل (شرط الإيقاف 4 — رسالة واحدة قصيرة فقط)
MSG_OPTOUT_APOLOGY = (
    "آسفين لو أزعجناك يا فندم 🙏 مش هنتواصل معاك تاني. لو احتجت أي حاجة في أي وقت، إحنا موجودين 🧡"
)

# =============================================================================
# أدوات التوقيت (توقيت القاهرة فقط — قاعدة النظام F)
# =============================================================================
def _now():
    """الوقت الحالي بتوقيت القاهرة (UTC+3) بدون tzinfo لسهولة الطرح."""
    try:
        import chat_db
        now = datetime.fromisoformat(chat_db.get_cairo_time())
    except Exception:
        now = datetime.utcnow() + timedelta(hours=3)
    if now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    return now


def _parse_dt(value):
    """تحويل أي صيغة تاريخ في قاعدة البيانات إلى datetime (بدون tzinfo)."""
    if not value:
        return None
    try:
        s = str(value)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        d = datetime.fromisoformat(s)
    except Exception:
        try:
            d = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None
    if d.tzinfo is not None:
        d = d.replace(tzinfo=None)
    return d


def _in_quiet_hours(now: datetime) -> bool:
    """هل الوقت الحالي ضمن ساعات الليل الصامتة [00:00, 08:00) بتوقيت القاهرة؟"""
    h = now.hour
    return QUIET_START_HOUR <= h < QUIET_END_HOUR


def _next_8am(now: datetime) -> datetime:
    """أول ساعة 8:00 صباحاً القادمة (اليوم إن كنا قبلها، وإلا غداً)."""
    candidate = now.replace(hour=QUIET_END_HOUR, minute=0, second=0, microsecond=0)
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate


# =============================================================================
# أدوات الحالة المحلية (قاعدة النظام G - ملف JSON عبر fts_paths)
# =============================================================================
def _load_state() -> dict:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            if isinstance(data, dict):
                data.setdefault("chats", {})
                data.setdefault("opted_out_senders", {})
                return data
            return {"chats": {}, "opted_out_senders": {}}
    except Exception as e:
        log.error(f"Failed to load state: {e}")
    return {"chats": {}, "opted_out_senders": {}}


def _save_state(state: dict):
    """حفظ فوري بعد كل حدث مهم حتى لا نكرر الإرسال لو توقف التشغيل فجأة."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
    except Exception as e:
        log.error(f"Failed to save state: {e}")


# =============================================================================
# أدوات النصوص والتطبيع
# =============================================================================
_AR_TRANS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي"})
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def _normalize_keyword(text: str) -> str:
    """تطبيع النص للمطابقة فقط (وليس للتغيير في الرسائل):
    توحيد الهمزات، إزالة التشكيل والتطويل، تحويل الأرقام العربية إلى لاتينية،
    وإزالة الإيموجي وعلامات الترقيم — حتى نلتقط كتابة العميل بأي صيغة.
    """
    s = str(text or "").strip().lower()
    s = re.sub(r"[\u064B-\u065F\u0640]", "", s)
    s = s.translate(_AR_TRANS).translate(_AR_DIGITS).translate(_FA_DIGITS)
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# رسائل النظام/الإحالة التي ليست تفاعلاً حقيقياً (تُستبعد من حساب الوقت)
_SYSTEM_PREFIXES = (
    "[facebook ad referral]",
    "[facebook referral]",
    "[system log]",
    "[system]",
    "[proposed_draft]",
    "[auto",
)


def _is_system_noise(text: str, sender_type: str = "") -> bool:
    """رسائل النظام والإحالة والمقترحات غير الجاهزة — ليست تفاعلاً حقيقياً
    ولا تُحتسب في توقيت المتابعات (لا من العميل ولا منّا).
    """
    t = str(text or "").strip()
    if not t:
        return True
    low = t.lower()
    for p in _SYSTEM_PREFIXES:
        if low.startswith(p):
            return True
    return False


# رسائل الميديا غير النصية (صوت/فيديو/ستيكر/صورة...) — تفاعل حقيقي من العميل
# يُحتسب في التوقيت لكن لا يُفحص للكلمات المفتاحية (لا يحتوي كلاماً مكتوباً)
_MEDIA_PREFIXES = (
    "[customer sent an audio",
    "[customer sent a video",
    "[customer sent a sticker",
    "[customer sent a document",
    "[customer sent a message of type",
    "[customer shared a location",
    "[customer shared contacts",
    "[customer sent a photo",
    "[customer sent an image",
    "[customer sent a picture",
    "[customer sent a voice",
    "[customer sent media",
)


def _is_media_placeholder(text: str) -> bool:
    low = str(text or "").strip().lower()
    return any(low.startswith(p) for p in _MEDIA_PREFIXES)


def _is_real_customer_message(text: str, sender_type: str) -> bool:
    """رسالة عميل حقيقية (نصية أو ميديا) تُبقي السلسلة/النافذة حية."""
    if str(sender_type or "").strip().lower() != "customer":
        return False
    return not _is_system_noise(text, sender_type)


_OPTOUT_PATTERNS = (
    r"متبعتليش", r"متبعتلوش", r"متكلمنيش", r"متكلمناش", r"متزعجنيش",
    r"بلاش تبعت", r"بلاش رسا[يئ]ل", r"مش عايز رسا[يئ]ل", r"مش عايز اتصالات",
    r"مش مهتم", r"اوقفوا", r"اوقفو", r"وقفو", r"لا ترسل", r"لا تبعث",
    r"شيلني", r"انزعني", r"ممنوع ترسل", r"مش هحجز", r"مش ححجز",
    r"\bstop\b", r"\bunsubscribe\b", r"don'?t contact", r"no more messages",
    r"leave me alone", r"مكفيني", r"انتو ضايقيني", r"ضايقني",
)


def _is_optout(text: str) -> bool:
    """كشف طلب العميل إيقاف التواصل نهائياً (لا نرسل له مجدداً أبداً)."""
    norm = _normalize_keyword(text)
    for p in _OPTOUT_PATTERNS:
        if re.search(p, norm):
            return True
    return False


def _extract_phone(text: str):
    """استخراج رقم موبايل مصري (بأي صيغة: 010.. / 20 10.. / 002 10.. / +20 10..)."""
    s = _normalize_keyword(text)
    s = re.sub(r"[\s\-\.\(\)]", "", s)
    # البادئات الاختيارية: 002 / 20 — ثم 0?1[0125] متبوعاً بـ 8 أرقام
    m = re.search(r"(?<!\d)(?:002|20)?0?1[0125][0-9]{8}(?!\d)", s)
    if not m:
        return None
    digits = m.group(0)
    if digits.startswith("002"):
        digits = digits[3:]
    elif digits.startswith("20") and len(digits) >= 12:
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("1"):
        digits = "0" + digits
    return digits if len(digits) >= 11 else None


# أنماط نية الحجز (العميل أكّد الحجز أو طلب إجراءات الحجز)
_BOOKING_PATTERNS = (
    r"احجز",                 # أحجز / احجز (بعد التطبيع: توحيد الهمزات)
    r"عايز ابدا الحجز", r"نفسي ابدا الحجز", r"ابدا الحجز", r"ابداء الحجز",
    r"نبدا الحجز", r"نبداء الحجز", r"نبتدي الحجز", r"نبدأ الحجز",
    r"خطوات الحجز", r"طريقة الحجز", r"طريقه الحجز", r"ازاي احجز", r"ازاى احجز",
    r"اجراءات الحجز",  # إجراءات الحجز (بعد التطبيع: إ→ا) — شرط الإيقاف ٣ في برومبت المدير: "طلب إجراءات الحجز"
    r"تاكيد الحجز", r"تأكيد الحجز", r"اكد الحجز", r"احجزلي", r"احجز ليا",
    r"حجز مكان", r"عايز احجز", r"نفسي احجز", r"حجزت",
    r"اجراءات الحجز", r"اجراءات الحجز", r"اكمل الحجز", r"كمل الحجز",
    r"\bbook\b", r"\breserve\b", r"\bbooking\b",
)


def _is_booking_intent(text: str) -> bool:
    """كشف نية العميل في الحجز أو طلب إجراءات الحجز (شرط الإيقاف 3)."""
    norm = _normalize_keyword(text)
    for p in _BOOKING_PATTERNS:
        if re.search(p, norm):
            return True
    return False


# =============================================================================
# استعلامات قاعدة البيانات (فلترة صارمة من الجذور — قاعدة النظام 10-7)
# =============================================================================
def _get_ad_conversations(cursor, now: datetime):
    """المحادثات الواردة من الإعلان المستهدف فقط.
    الفلترة تتم في SQL من الجذور:
      - facebook_ad_id = TARGET_AD_ID (شرط التفعيل الحصري)
      - last_message_time حديثة (خلال 25 ساعة) — أي محادثة أقدم من ذلك تكون
        نافذة الـ 24 ساعة مغلقة ولا يمكن مراسلتها أصلاً، فلا داعي لجلبها
        (تحسين الأداء بدلاً من جلب كل المحادثات وفلترتها برمجياً).
      - نرتب الأقدم أولاً (ASC) بحيث تُعالج المحادثات الأقرب لإغلاق نافذة
        مراحلها قبل الأحدث فلا تُحرم رسالة M3 بسبب MAX_SENDS_PER_RUN.
    """
    cutoff = (now - timedelta(hours=WINDOW_HOURS + 1)).isoformat()
    cursor.execute(
        """
        SELECT chat_id, sender_identifier, contact_name, source, location,
               receiving_phone_id, last_message_time, needs_help, is_closed,
               auto_reply_hold_until, customer_phone
        FROM conversations
        WHERE facebook_ad_id = ?
          AND (is_deleted IS NULL OR is_deleted = 0)
          AND last_message_time IS NOT NULL
          AND last_message_time >= ?
        ORDER BY last_message_time ASC
        """,
        (TARGET_AD_ID, cutoff),
    )
    rows = cursor.fetchall()
    return [dict(r) for r in rows] if rows else []


def _last_real_message(cursor, chat_id):
    """آخر رسالة حقيقية في المحادثة (عميل أو رد منّا) — مرساة المتابعة 1.
    نستبعد رسائل النظام/الإحالة ([Facebook Ad Referral]، [System Log]،
    [PROPOSED_DRAFT]...) لأنها ليست تفاعلاً حقيقياً. أما رسائل الميديا من
    العميل (صوت/فيديو/ستيكر) فهي تفاعل حقيقي يُحتسب في التوقيت.
    يعيد (sender_type, text, timestamp) أو (None, None, None).
    """
    cursor.execute(
        """
        SELECT sender_type, text, timestamp
        FROM messages
        WHERE chat_id = ?
        ORDER BY timestamp DESC
        LIMIT 40
        """,
        (chat_id,),
    )
    for row in cursor.fetchall():
        sender_type = str(row[0] or "").strip().lower()
        text = str(row[1] or "")
        if _is_system_noise(text, sender_type):
            continue
        if sender_type in ("customer", "agent", "ai"):
            return sender_type, text, row[2]
    return None, None, None


def _last_customer_message(cursor, chat_id):
    """آخر رسالة حقيقية من العميل — مرساة نافذة الـ 24 ساعة ومرحلتي 2 و3.
    (رسائل الميديا تُحتسب تفاعلاً حقيقياً لكن لا يُفحص نصها للكلمات المفتاحية.)
    يعيد (text, timestamp) أو (None, None).
    """
    cursor.execute(
        """
        SELECT text, timestamp
        FROM messages
        WHERE chat_id = ? AND sender_type = 'customer'
        ORDER BY timestamp DESC
        LIMIT 20
        """,
        (chat_id,),
    )
    for row in cursor.fetchall():
        text = str(row[0] or "")
        if _is_system_noise(text, "customer"):
            continue
        return text, row[1]
    return None, None


def _hold_active(hold_until, now: datetime) -> bool:
    """هل فترة إيقاف الرد الآلي (auto_reply_hold_until) ما زالت سارية؟
    (تأجيل مؤقت فقط — لا يُعد تدخلاً بشرياً دائماً).
    """
    if not hold_until:
        return False
    d = _parse_dt(hold_until)
    return bool(d and d > now)


# =============================================================================
# الإرسال والتحويل والإشعارات
# =============================================================================
def _send_message(agent, conv: dict, text: str, dry_run: bool = False):
    """إرسال الرسالة عبر القناة الصحيحة (Facebook / WhatsApp) وتسجيلها في سجل المحادثة."""
    if dry_run:
        return True, None
    source = str(conv.get("source") or "").strip().lower()
    sender_id = str(conv.get("sender_identifier") or "").strip()
    chat_id = str(conv.get("chat_id") or "").strip()
    if not sender_id or not chat_id:
        return False, "missing_sender_or_chat"
    try:
        # القناة تُحدَّد من عمود source أساساً (أدق وأأمن من تخمين المعرفات)
        is_wa = source == "whatsapp" or (not source and sender_id.startswith("20") and len(sender_id) > 10)
        if is_wa:
            channel = "WhatsApp"
            ok, resp = agent.send_whatsapp_message(
                sender_id,
                text=text,
                location=str(conv.get("location") or "Unknown"),
                receiving_phone_id=str(conv.get("receiving_phone_id") or "").strip() or None,
            )
        else:
            channel = "Facebook"
            ok, resp = agent.send_facebook_message(sender_id, text=text)
        if not ok:
            return False, str(resp or "")[:300]
        try:
            import chat_db
            chat_db.add_message(chat_id=chat_id, sender_type="agent", text=text, status="sent", source=channel)
            try:
                chat_db.mark_conversation_read(chat_id)
            except Exception:
                pass
        except Exception as e:
            log.warning(f"Failed to log sent message for {chat_id}: {e}")
        return True, None
    except Exception as e:
        return False, str(e)[:300]


def _save_phone_and_notify(chat_id: str, phone: str, dry_run: bool = False):
    """تسجيل الرقم في بيانات العميل (customer_phone) + إشعار فوري للفريق البشري:
    needs_help=1 (يُظهر المحادثة للموظف البشري في لوحة التحكم) + رسالة System Log.
    """
    if dry_run:
        return
    try:
        import chat_db
        try:
            chat_db.update_conversation_info(chat_id, customer_phone=phone)
        except Exception as e:
            log.warning(f"Failed to save customer_phone for {chat_id}: {e}")
        try:
            chat_db.update_conversation_info(chat_id, needs_help=True)
        except Exception as e:
            log.warning(f"Failed to set needs_help for {chat_id}: {e}")
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] Umrah 10-day follow-up: customer phone received ({phone}) - notify human team",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to save/notify phone for {chat_id}: {e}")


def _transfer_to_booking(chat_id: str, reason: str, dry_run: bool = False):
    """تحويل المحادثة لمسار الحجز (إشعار للفريق البشري) + إيقاف السلسلة."""
    if dry_run:
        return
    try:
        import chat_db
        try:
            chat_db.update_conversation_info(chat_id, needs_help=True)
        except Exception as e:
            log.warning(f"Failed to set needs_help for {chat_id}: {e}")
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] Umrah 10-day follow-up: transferred to booking path ({reason})",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to transfer {chat_id}: {e}")


def _log_stop_reason(chat_id: str, reason: str, dry_run: bool = False):
    """تسجيل سبب إيقاف السلسلة في سجل المحادثة (أثر توثيقي فقط — لا رسالة للعميل)."""
    if dry_run:
        return
    try:
        import chat_db
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] Umrah 10-day follow-up: chain stopped ({reason})",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to log stop reason for {chat_id}: {e}")


# =============================================================================
# منطق الحالة ومعالجة الردود
# =============================================================================
def _init_entry(conv: dict, last_customer_ts: datetime, last_customer_text: str,
                last_msg_ts: datetime, now_iso: str) -> dict:
    """تهيئة سجل الحالة لمحادثة جديدة."""
    return {
        "last_customer_reply": last_customer_ts.isoformat(),
        "last_message_time": last_msg_ts.isoformat(),
        "highest_stage_sent": 0,
        "stages": {},
        "stopped": False,
        "stop_reason": "",
        "opted_out": False,
        "sender_identifier": str(conv.get("sender_identifier") or "").strip(),
        "last_customer_text": str(last_customer_text or "")[:200],
        "updated_at": now_iso,
    }


def _classify_customer_message(text: str):
    """تصنيف رسالة العميل الواردة:
    يعيد (category, phone) حيث category ∈ {opt_out, phone, booking, reply}.
    - opt_out: طلب إيقاف التواصل نهائياً.
    - phone:   تحتوي رقم تليفون/واتساب.
    - booking: نية حجز أو طلب إجراءات الحجز.
    - reply:   أي رد آخر (المساعد الأساسي يتعامل معه).
    """
    if _is_optout(text):
        return "opt_out", None
    phone = _extract_phone(text)
    if phone:
        return "phone", phone
    if _is_booking_intent(text):
        return "booking", None
    return "reply", None


def _handle_new_reply(agent, conv, entry, text, now, dry_run):
    """معالجة رد جديد من العميل أثناء السلسلة (أو أول رسالة لمحادثة جديدة):
    - opt_out → اعتذار + إيقاف نهائي (يُسجَّل على الـ sender ليشمل المحادثات الجديدة).
    - phone   → تسجيل الرقم + إشعار فريق بشري + إيقاف (بدون أي رسالة رد
                للعميل — تحديث المدير 2026-08-02: لا نرسل نص "وصلنا رقم حضرتك").
    - booking → تحويل لمسار الحجز + إيقاف.
    - reply   → إيقاف السلسلة فقط (المساعد الأساسي يرد على العميل).
    يعيد (category, sent) حيث sent=هل أُرسلت رسالة.
    """
    category, phone = _classify_customer_message(text)
    chat_id = str(conv.get("chat_id") or "").strip()

    if category == "opt_out":
        _send_message(agent, conv, MSG_OPTOUT_APOLOGY, dry_run)
        _log_stop_reason(chat_id, "customer_opt_out", dry_run)
        entry["opted_out"] = True
        entry["stopped"] = True
        entry["stop_reason"] = "customer_opt_out"
        return "opt_out", True

    if category == "phone":
        # تحديث المدير 2026-08-02: لا نرسل أي رسالة رد للعميل عند استلام الرقم
        # (نص "وصلنا رقم حضرتك" أُلغي نهائياً) — نكتفي بتسجيل الرقم في حقل
        # customer_phone + إشعار فوري للفريق البشري + إيقاف السلسلة.
        # المساعد الأساسي/الفريق البشري هو من يرد على العميل مباشرة.
        _save_phone_and_notify(chat_id, phone, dry_run)
        entry["stopped"] = True
        entry["stop_reason"] = f"phone_received:{phone}"
        return "phone", False

    if category == "booking":
        _transfer_to_booking(chat_id, "booking_intent", dry_run)
        entry["stopped"] = True
        entry["stop_reason"] = "booking_intent"
        return "booking", False

    # أي رد آخر → إيقاف السلسلة (المساعد الأساسي يرد على الاستفسار)
    _log_stop_reason(chat_id, "customer_replied", dry_run)
    entry["stopped"] = True
    entry["stop_reason"] = "customer_replied"
    return "reply", False


# =============================================================================
# منطق المراحل والجدولة
# =============================================================================
def _due_stage(entry: dict, now: datetime, last_customer_ts: datetime,
               last_msg_ts: datetime) -> int:
    """تحديد المرحلة المستحقة (واحدة فقط لكل محادثة في كل تشغيل — ترتيب إجباري):
    - المرحلة 1: لم تُرسل بعد + مرّ 60 دقيقة على آخر رسالة.
    - المرحلة 2: أُرسلت 1 + لم تُرسل 2 + مرّ 7 ساعات على آخر رسالة عميل.
    - المرحلة 3: أُرسلت 2 + لم تُرسل 3 + مرّ 22 ساعة على آخر رسالة عميل
                 (وقبل إغلاق نافذة الـ 24 ساعة).
    يعيد 0 إذا لم تكن أي مرحلة مستحقة.
    """
    highest = int(entry.get("highest_stage_sent") or 0)
    elapsed_msg = (now - last_msg_ts).total_seconds() / 3600.0
    elapsed_cust = (now - last_customer_ts).total_seconds() / 3600.0

    if highest < 1 and elapsed_msg >= (STAGE1_MINUTES / 60.0):
        return 1
    if highest < 2 and highest >= 1 and elapsed_cust >= STAGE2_HOURS:
        return 2
    if highest < 3 and highest >= 2 and elapsed_cust >= STAGE3_HOURS:
        return 3
    return 0


def _window_closes_before_8am(last_customer_ts: datetime, now: datetime) -> bool:
    """هل نافذة الـ 24 ساعة ستُغلق قبل الساعة 8 صباحاً القادمة؟
    (الاستثناء الوحيد الذي يسمح بإرسال المتابعة 3 أثناء ساعات الليل).
    """
    window_close = last_customer_ts + timedelta(hours=WINDOW_HOURS)
    return window_close < _next_8am(now)


# =============================================================================
# نقطة الدخول الرئيسية (يستدعيها محرك الأتمتة عبر run_script)
# =============================================================================
def run(agent, payload: dict = None) -> dict:
    """
    المعاملات (payload):
        dry_run:  (اختياري) إن كان True لا يُرسل ولا يحفظ الحالة (للاختبار فقط).
        limit:    (اختياري) عدد أقصى للمحادثات المعالجة في هذا التشغيل (للاختبار).
    """
    payload = payload or {}
    dry_run = bool(payload.get("dry_run"))
    limit = None
    try:
        limit = int(payload.get("limit") or 0) or None
    except Exception:
        limit = None

    now = _now()
    now_iso = now.isoformat()
    sent_count = 0
    errors = []
    processed_chats = 0
    actions = {"stage1": 0, "stage2": 0, "stage3": 0, "opt_out": 0, "phone": 0,
               "booking": 0, "reply_stop": 0, "window_closed": 0, "deferred_night": 0}

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        msg = f"Failed to connect to DB: {e}"
        log.error(f"[Umrah10Day] {msg}")
        return {"ok": False, "sent_count": 0, "errors": [msg], "message": msg}

    state = _load_state()
    chats = state.setdefault("chats", {})
    opted_out_senders = state.setdefault("opted_out_senders", {})

    try:
        conversations = _get_ad_conversations(cursor, now)
        log.info(f"[Umrah10Day] Found {len(conversations)} recent conversations for ad {TARGET_AD_ID}")

        for conv in conversations:
            chat_id = str(conv.get("chat_id") or "").strip()
            if not chat_id:
                continue
            if limit and processed_chats >= limit:
                break

            # ===== 5) تدخّل موظف بشري → إيقاف السلسلة نهائياً =====
            human_active = False
            try:
                if int(conv.get("needs_help") or 0) == 1:
                    human_active = True
            except Exception:
                pass
            try:
                if int(conv.get("is_closed") or 0) == 1:
                    human_active = True
            except Exception:
                pass
            if human_active:
                entry = chats.get(chat_id)
                if entry and not entry.get("stopped"):
                    entry["stopped"] = True
                    entry["stop_reason"] = "human_intervention"
                    entry["updated_at"] = now_iso
                    if not dry_run:
                        _save_state(state)
                continue

            # تأجيل مؤقت (auto_reply_hold_until) — نتخطى هذه الدورة فقط
            if _hold_active(conv.get("auto_reply_hold_until"), now):
                continue

            entry = chats.get(chat_id)

            # ===== استخراج مراسي الوقت (مرة واحدة لكل محادثة) =====
            last_cust_text, last_cust_raw = _last_customer_message(cursor, chat_id)
            if last_cust_raw is None:
                continue
            last_cust_ts = _parse_dt(last_cust_raw)
            if last_cust_ts is None:
                continue
            _, _, last_msg_raw = _last_real_message(cursor, chat_id)
            last_msg_ts = _parse_dt(last_msg_raw) if last_msg_raw is not None else last_cust_ts
            if last_msg_ts is None:
                last_msg_ts = last_cust_ts

            sender_id = str(conv.get("sender_identifier") or "").strip()

            # عدد المحادثات المعالجة فعلياً في هذا التشغيل (حد الـ limit للاختبار)
            processed_chats += 1

            # ===== إيقاف محادثة قديمة قيد السلسلة لمرسل طلب الإيقاف =====
            # إذا طلب العميل عدم التواصل في محادثة أخرى (opt-out دائم بالـ
            # sender_identifier) وكان لدينا محادثة قديمة له قيد السلسلة هنا —
            # نوقفها فوراً ولا نرسل أي متابعة إطلاقاً (قاعدة المدير: لا سلسلة
            # متابعة قديمة لعميل سبق وطلب عدم التواصل حتى لو بدأ محادثة جديدة
            # أو كانت محادثة قديمة ما زالت قيد التتبع).
            if entry is not None and sender_id and sender_id in opted_out_senders:
                if not entry.get("stopped"):
                    entry["stopped"] = True
                    entry["stop_reason"] = "sender_opted_out"
                    entry["updated_at"] = now_iso
                    if not dry_run:
                        _save_state(state)
                continue

            # ===== محادثة جديدة: تهيئة الحالة (ثم نكمل لنفس منطق الجدولة) =====
            if entry is None:
                # نافذة الـ 24 ساعة من آخر رسالة عميل مغلقة → لا نبدأ التتبع أصلاً
                elapsed_cust = (now - last_cust_ts).total_seconds() / 3600.0
                if elapsed_cust >= WINDOW_HOURS:
                    continue
                # عميل سبق وطلب عدم التواصل → لا نرسل له متابعات نهائياً
                # حتى لو بدأ محادثة جديدة من نفس الإعلان (شرط الإيقاف 4)
                if sender_id and sender_id in opted_out_senders:
                    continue
                # أول رسالة قد تحتوي طلب إيقاف / رقم / نية حجز — نعالجها فوراً
                if not _is_media_placeholder(last_cust_text):
                    category, _ = _classify_customer_message(last_cust_text)
                    if category != "reply":
                        entry = _init_entry(conv, last_cust_ts, last_cust_text, last_msg_ts, now_iso)
                        entry["sender_identifier"] = sender_id
                        cat, sent = _handle_new_reply(agent, conv, entry, last_cust_text, now, dry_run)
                        actions[cat] = actions.get(cat, 0) + 1
                        if cat == "opt_out" and sender_id:
                            opted_out_senders[sender_id] = now_iso
                        entry["last_customer_text"] = str(last_cust_text or "")[:200]
                        entry["updated_at"] = now_iso
                        chats[chat_id] = entry
                        if sent:
                            sent_count += 1
                        if not dry_run:
                            _save_state(state)
                        if sent_count >= MAX_SENDS_PER_RUN:
                            break
                        continue
                entry = _init_entry(conv, last_cust_ts, last_cust_text, last_msg_ts, now_iso)
                entry["sender_identifier"] = sender_id
                chats[chat_id] = entry
                if not dry_run:
                    _save_state(state)
                # لا continue هنا — نكمل لنفس منطق الجدولة حتى تُرسل M1 فوراً
                # إذا كانت مستحقة (مرّ 60 دقيقة على آخر رسالة) حسب جدول المدير

            # ===== حالة نهائية: أُوقفت السلسلة → لا نعيد =====
            if entry.get("stopped"):
                continue

            # ===== كشف رد جديد من العميل أثناء السلسلة → إيقاف فوري =====
            prev_cust_ts = _parse_dt(entry.get("last_customer_reply"))
            if prev_cust_ts is None or last_cust_ts > prev_cust_ts:
                cat, sent = _handle_new_reply(agent, conv, entry, last_cust_text, now, dry_run)
                actions[cat if cat in actions else "reply_stop"] = actions.get(cat, 0) + 1
                if cat == "opt_out" and sender_id:
                    opted_out_senders[sender_id] = now_iso
                entry["last_customer_text"] = str(last_cust_text or "")[:200]
                entry["updated_at"] = now_iso
                if sent:
                    sent_count += 1
                if not dry_run:
                    _save_state(state)
                if sent_count >= MAX_SENDS_PER_RUN:
                    break
                continue

            # ===== لا رد جديد → منطق الجدولة الزمنية =====
            elapsed_cust = (now - last_cust_ts).total_seconds() / 3600.0

            # نافذة الـ 24 ساعة انتهت → إيقاف نهائي (لا إرسال بعد اليوم)
            if elapsed_cust >= WINDOW_HOURS:
                if int(entry.get("highest_stage_sent") or 0) == 0:
                    # لم تبدأ السلسلة أبداً → حذف السجل لصغر ملف الحالة
                    chats.pop(chat_id, None)
                else:
                    entry["stopped"] = True
                    entry["stop_reason"] = "window_closed"
                    entry["updated_at"] = now_iso
                actions["window_closed"] = actions.get("window_closed", 0) + 1
                if not dry_run:
                    _save_state(state)
                continue

            target = _due_stage(entry, now, last_cust_ts, last_msg_ts)
            if target == 0:
                continue

            # ===== ساعات الليل الصامتة [00:00, 08:00) بتوقيت القاهرة =====
            # إذا وقع موعد الإرسال في الليل → نؤجّل لأول دورة بعد 8 صباحاً،
            # إلا إذا كانت نافذة الـ 24 ساعة ستُغلق قبل 8 صباحاً فعندها
            # تُرسل المتابعة 3 فوراً بغضّ النظر عن الوقت (آخر فرصة).
            if _in_quiet_hours(now):
                if target == 3 and _window_closes_before_8am(last_cust_ts, now):
                    pass  # استثناء المتابعة 3: أرسل فوراً
                else:
                    actions["deferred_night"] = actions.get("deferred_night", 0) + 1
                    continue

            msg = {1: MSG_STAGE1, 2: MSG_STAGE2, 3: MSG_STAGE3}.get(target, "")
            if not msg:
                continue

            ok, err = _send_message(agent, conv, msg, dry_run)
            if ok:
                entry["highest_stage_sent"] = target
                entry.setdefault("stages", {})[str(target)] = now_iso
                entry["updated_at"] = now_iso
                actions[f"stage{target}"] = actions.get(f"stage{target}", 0) + 1
                sent_count += 1
                if not dry_run:
                    _save_state(state)  # حفظ فوري بعد كل إرسال (منع التكرار)
                if sent_count >= MAX_SENDS_PER_RUN:
                    break
            else:
                errors.append(f"stage{target}->{chat_id}: {err}")

        message = (
            f"Ad {TARGET_AD_ID}: sent={sent_count} | processed={processed_chats} "
            f"| actions={actions} | errors={len(errors)}"
        )
        log.info(f"[Umrah10Day] {message}")
        return {
            "ok": len(errors) == 0,
            "sent_count": sent_count,
            "processed_chats": processed_chats,
            "actions": actions,
            "errors": errors[:20],
            "message": message,
        }
    except Exception as e:
        msg = f"Error in Umrah 10-day follow-up run: {e}"
        log.error(f"[Umrah10Day] {msg}")
        return {"ok": False, "sent_count": sent_count, "errors": [msg], "message": msg}
    finally:
        try:
            if not dry_run:
                _save_state(state)
            conn.close()
        except Exception:
            pass
