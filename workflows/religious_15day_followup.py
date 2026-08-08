# -*- coding: utf-8 -*-
"""
Workflow: Religious 15-Day Follow-Up - ديني - برنامج عمرة الـ١٥ يوم
====================================================================
نظام المتابعة التلقائية (Follow-Up) لبرنامج "عمرة الـ١٥ يوم" على فيسبوك
ماسنجر — إعادة تنشيط العملاء الصامتين داخل نافذة الـ 24 ساعة وتحويلهم
لحجز أو الحصول على رقم تليفون/واتساب قبل انتهاء النافذة.

نطاق التطبيق (شرط التفعيل الحصري — من برومبت المدير حرفياً):
    ad_id = 120248067701970757 فقط
    أي محادثة من أي مصدر تاني (إعلان مختلف، رسالة عضوية، تعليق) → تُتجاهل
    تماماً. الفلترة تتم من الجذور في SQL (WHERE facebook_ad_id = ?) ولا
    نلمس أي إعلان أو قسم آخر إطلاقاً.

نظام الجدولة — دورة فحص كل ٦٠ دقيقة (مُسجَّلة في automation_workflows):
    - T = المدة الزمنية منذ آخر رسالة في المحادثة (سواء من العميل أو منّا).
    - الفولو اب الأول (FU1): يُرسل إذا تحققت كل الشروط مع بعض:
        * T أكبر من أو يساوي ٣ ساعات.
        * آخر رسالة حقيقية في المحادثة من عندنا (العميل لم يرد على آخر
          رسالة منّنا).
        * لم يتم إرسال الفولو اب الأول من قبل في المحادثة.
        * نافذة الـ ٢٤ ساعة ما زالت مفتوحة (آخر تفاعل عميل < ٢٤ ساعة، مع
          هامش أمان 23.9 ساعة لتجنب خطأ Meta #10).
    - الفولو اب الثاني (FU2): يُرسل إذا تحققت كل الشروط مع بعض:
        * مرّت ٢٠ ساعة أو أكثر على آخر تفاعل من العميل.
        * لم تمر ٢٣ ساعة (عشان نلحق نبعت قبل قفل نافذة الـ ٢٤ ساعة).
        * العميل لم يرد بعد الفولو اب الأول.
        * لم يتم إرسال الفولو اب الثاني من قبل في المحادثة.
    - الحد الأقصى المطلق: رسالتا فولو اب فقط لكل محادثة مهما كانت الظروف
      (MAX_FU_PER_CHAT = 2) — محسوب بإجمالي مرسل عبر total_fu_sent.

شروط الإيقاف (مهم جداً — من برومبت المدير):
    1) العميل ردّ بأي رسالة → إلغاء الفولو اب المجدول والتعامل مع رسالته
       عادي (المساعد الأساسي يرد لحظياً)، ويبدأ العدّاد من جديد بعد آخر
       رد منّنا (تصفير fu1/fu2 في الدورة الجديدة — مع بقاء سقف الـ ٢).
    2) العميل بعت رقم موبايل أو رقم واتساب → لا نبعث أي فولو اب، ويُحوَّل
       لفريق خدمة العملاء فوراً مع وسم "عميل جاهز للاتصال"
       (needs_help=1 + System Log + tag في sales_customer_state).
    3) العميل أكّد الحجز أو قال إنه حوّل العربون → إيقاف الـ workflow
       وتحويل لفريق الحجز (needs_help=1 + System Log + tag).
    4) العميل طلب عدم التواصل أو رد بشكل سلبي واضح → إيقاف نهائي دائم
       (اعتذار لطيف برسالة واحدة + تسجيل الـ sender في opted_out_senders
       حتى لو بدأ محادثة جديدة من نفس الإعلان).
    5) مرّت ٢٤ ساعة على آخر تفاعل من العميل → إيقاف الإرسال تماماً
       (النافذة قفلت — Meta Error #10).

اختيار نص الرسالة:
    تُختار النسخة حسب آخر زرار ضغط عليه العميل في بداية المحادثة:
        زرار ١: «ابعتولي برنامج الـ١٥ يوم بالتفصيل 📋»
        زرار ٢: «إيه أقرب مواعيد السفر المتاحة؟ 🗓»
        زرار ٣: «السعر ٤٠٬٩٥٠ شامل إيه بالظبط؟ 💰»
    لو مضغطش أي زرار → النسخة العامة (٤).
    (نصوص الرسائل منسوخة حرفياً من برومبت المدير — لا إعادة صياغة إطلاقاً.)

قواعد إضافية (من برومبت المدير):
    - ممنوع إرسال أي فولو اب بين ١١ مساءً و٩ صباحاً بتوقيت القاهرة
      [23:00, 09:00) — يُؤجَّل لأول دورة بعد ٩ صباحاً، مع الالتزام بحد
      الـ ٢٣ ساعة للفولو اب الثاني (لو التأجيل تعدّى ٢٣ ساعة → لا يُرسل).
    - لو العميل رد بلايك أو إيموجي فقط → يعتبر تفاعلاً يفتح نافذة جديدة،
      يُرد عليه رداً طبيعياً (إن لم يكن المساعد الأساسي قد ردّ عليه فعلاً
      لمنع التكرار)، ثم تبدأ دورة الفولو اب من جديد.

ملاحظات هندسية (لماذا هذه الشروط):
    - التوقيت: نستخدم chat_db.get_cairo_time() (توقيت القاهرة UTC+3) كما
      يفعل النظام بالكامل، ولا نستخدم datetime.now(timezone.utc) إطلاقاً
      لمنع انحراف التوقيت (قاعدة النظام F).
    - الحالة: يُمنع استخدام agent.load_state/save_state (غير موجودة على
      الـ agent في run_script)، لذا نستخدم ملف JSON محلي عبر
      fts_paths.get_data_path (قاعدة النظام G) لمنع التكرار اللانهائي.
    - تحسين الأداء (قاعدة النظام 10-7): نفلتر المحادثات من الجذور في SQL
      (facebook_ad_id + آخر رسالة خلال 25 ساعة) بدلاً من جلب كل المحادثات
      وفلترتها برمجياً.
    - حد أقصى للإرسال في كل تشغيل (MAX_SENDS_PER_RUN = 20) حتى لا تتجاوز
      مدة التشغيل timeout الـ http_request (60 ثانية) — التشغيل التالي
      يكمل الباقي لأن الحالة تُحفظ فور كل إرسال.
    - رسائل النظام/الإحالة ([Facebook Ad Referral]، [System Log]،
      [PROPOSED_DRAFT]، [Agent reacted...]) تُستبعد من حساب التوقيت لأنها
      ليست تفاعلاً حقيقياً. أما الميديا والتفاعلات (لايك/إيموجي) من العميل
      فهي تفاعل حقيقي يُحتسب في التوقيت.
    - لا يلمس أي Workflow آخر ولا يعدّل ai_agent.py ولا يعيد تشغيل السيرفر
      (محرك الأتمتة hot-load من قاعدة البيانات في كل tick).
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
# الإعلان المستهدف فقط (شرط التفعيل الحصري — Ad ID من برومبت المدير)
TARGET_AD_ID = "120248067701970757"

# قاعدة بيانات المحادثات (نفس مسار chat_db)
DB_FILE = get_data_path("chat_history.db")

# ملف الحالة المحلي (قاعدة النظام G: يُمنع agent.load_state)
STATE_FILE = get_data_path("religious_15day_followup_state.json")

# عتبات التوقيت (حسب برومبت المدير حرفياً)
FU1_HOURS = 3.0             # الفولو اب الأول بعد ٣ ساعات على الأقل من آخر رسالة
FU2_MIN_HOURS = 20.0        # الفولو اب الثاني بعد ٢٠ ساعة أو أكثر من آخر تفاعل عميل
FU2_MAX_HOURS = 23.0        # لم يمر ٢٣ ساعة (عشان نلحق قبل قفل نافذة الـ ٢٤ ساعة)
WINDOW_HOURS = 24.0         # نافذة Meta الكاملة من آخر تفاعل عميل
SEND_SAFETY_HOURS = 23.9    # هامش أمان قبل إغلاق النافذة (تجنب خطأ Meta #10)

# ساعات الليل الصامتة (بتوقيت القاهرة): من ١١ مساءً حتى ٩ صباحاً [23:00, 09:00)
QUIET_START_HOUR = 23
QUIET_END_HOUR = 9

# الحد الأقصى: رسالتا فولو اب فقط لكل محادثة مهما كانت الظروف
MAX_FU_PER_CHAT = 2

# حد أقصى للإرسال في كل تشغيل (حتى لا يتجاوز timeout الـ http_request)
MAX_SENDS_PER_RUN = 20

log = logging.getLogger("Religious15DayFollowup")

# =============================================================================
# نصوص الرسائل (منسوخة حرفياً من برومبت المدير — لا تغيير ولا إعادة صياغة)
# =============================================================================
# ------------------- زرار ١: «ابعتولي برنامج الـ١٥ يوم بالتفصيل 📋» ----------
MSG_V1_FU1 = (
    "أهلاً بيك تاني 🧡\n"
    "حبينا نطمنك إن الحجز مش محتاج غير جواز سفر ساري ٦ شهور + صورة شخصية، والدفع ٥٠٪ بس مقدم والباقي قبل السفر بأسبوعين.\n"
    "ولو حابب تستشير حد من العيلة الأول، ابعتلنا وهنبعتلك تصميم برنامج الرحلة يوم بيوم — تقدر تبعته لأي حد وتاخدوا القرار مع بعض 📋"
)

MSG_V1_FU2 = (
    "قبل ما نقفل معاك النهارده حبينا نقولك إن رحلة يوم ٢-٩ آخر موعد لحجزها يوم ٢٠-٨، والسعر المعلن ٤٠٬٩٥٠ ج ساري على الأماكن المتاحة فيها .\n"
    "لو حابب تلحق مكانك، ابعت عدد المسافرين ونبعتلك خطوات الحجز.\n"
    "أو لو أسهل ليك نكلمك إحنا — ابعتلنا رقم موبايلك أو رقم الواتس بتاعك وهنتواصل معاك في أقرب وقت 🧡"
)

# ------------------- زرار ٢: «إيه أقرب مواعيد السفر المتاحة؟ 🗓» -------------
MSG_V2_FU1 = (
    "أهلاً بيك تاني 🧡\n"
    "عشان كنت بتسأل عن المواعيد — الأماكن في الرحلات القريبة بتتأكد بالأسبقية، وبنقدر نثبتلك مكان مبدئي بمجرد ما تبعتلنا عدد المسافرين.\n"
    "والحجز مش محتاج غير جواز ساري ٦ شهور + صورة شخصية، والدفع ٥٠٪ بس مقدم 🗓"
)

MSG_V2_FU2 = (
    "قبل ما نقفل معاك النهارده — مواعيد الرحلات الجاية بتتحجز بسرعة ورحله 2-9 قاربت علي الاكتمال\n"
    "ابعت عدد المسافرين ونثبتلك مكان.\n"
    "أو لو أسهل ليك نكلمك إحنا — ابعتلنا رقم موبايلك أو رقم الواتس بتاعك وهنتواصل معاك في أقرب وقت 🧡"
)

# ------------------- زرار ٣: «السعر ٤٠٬٩٥٠ شامل إيه بالظبط؟ 💰» --------------
MSG_V3_FU1 = (
    "أهلاً بيك تاني 🧡\n"
    "نأكدلك إن السعر ده شامل الطيران والتأشيرة والإقامة في المدينتين — من غير أي رسوم بتظهر بعدين.\n"
    "والدفع مريح: ٥٠٪ بس مقدم والباقي قبل السفر بأسبوعين، والحجز محتاج جواز ساري ٦ شهور + صورة شخصية بس.\n"
    "ولو حابب تستشير حد من العيلة، ابعتلنا وهنبعتلك تصميم برنامج الرحلة يوم بيوم تقدر تبعته لأي حد 📋"
)

MSG_V3_FU2 = (
    "قبل ما نقفل معاك النهارده حبينا نقولك إن السعر المعلن ده ساري على الأماكن المتاحة حاليً.\n"
    "لو حابب نحجزلك مكان مبدئي ابعت عدد المسافرين.\n"
    "أو لو أسهل ليك نكلمك إحنا — ابعتلنا رقم موبايلك أو رقم الواتس بتاعك وهنتواصل معاك في أقرب وقت 🧡"
)

# ------------------- النسخة العامة (العميل مضغطش أي زرار) -------------------
MSG_V4_FU1 = (
    "أهلاً بيك تاني 🧡\n"
    "حبينا نطمنك إن الحجز مش محتاج غير جواز سفر ساري ٦ شهور + صورة شخصية، والدفع ٥٠٪ بس مقدم والباقي قبل السفر بأسبوعين.\n"
    "ولو حابب تستشير حد من العيلة الأول، ابعتلنا وهنبعتلك تصميم برنامج الرحلة يوم بيوم 📋"
)

MSG_V4_FU2 = (
    "قبل ما نقفل معاك النهارده حبينا نقولك إن أماكن الرحلات القريبة بتتحجز بالأسبقية.\n"
    "لو حابب نحجزلك مكان مبدئي ابعت عدد المسافرين.\n"
    "أو لو أسهل ليك نكلمك إحنا — ابعتلنا رقم موبايلك أو رقم الواتس بتاعك وهنتواصل معاك في أقرب وقت 🧡"
)

# رد طبيعي عند الرد بلايك/إيموجي فقط (قاعدة المدير: يُرد رداً طبيعياً ثم
# تبدأ دورة فولو اب جديدة). لا يوجد نص محدد من المدير لهذه الحالة، فاخترنا
# رداً قصيراً محايداً لا يبيع ولا يضايق.
MSG_EMOJI_REPLY = (
    "أهلاً بيك يا فندم 🧡\n"
    "لو عندك أي سؤال عن برنامج العمرة الـ١٥ يوم، أو تحب تحجز مكانك، إحنا معاك في أي وقت 😊"
)

# اعتذار لطيف عند طلب العميل عدم التواصل (شرط الإيقاف 4 — رسالة واحدة قصيرة فقط)
MSG_OPTOUT_APOLOGY = (
    "آسفين لو أزعجناك يا فندم 🙏 مش هنتواصل معاك تاني. لو احتجت أي حاجة في أي وقت، إحنا موجودين 🧡"
)

# خريطة نصوص الفولو اب حسب النسخة (١/٢/٣/٤)
MSGS = {
    1: {"fu1": MSG_V1_FU1, "fu2": MSG_V1_FU2},
    2: {"fu1": MSG_V2_FU1, "fu2": MSG_V2_FU2},
    3: {"fu1": MSG_V3_FU1, "fu2": MSG_V3_FU2},
    4: {"fu1": MSG_V4_FU1, "fu2": MSG_V4_FU2},
}

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
    """هل الوقت الحالي ضمن ساعات الليل الصامتة [23:00, 09:00) بتوقيت القاهرة؟"""
    h = now.hour
    return h >= QUIET_START_HOUR or h < QUIET_END_HOUR


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
    وإزالة الإيموجي وعلامات الترقيم — حتى نلتقط رسائل الأزرار بأي صيغة.
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
    "[agent reacted",   # رد فعل منّا (لايك) ليس رسالة حقيقية
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


# نطاقات الإيموجي (للتعرف على الرد بالإيموجي فقط — قاعدة المدير)
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA70-\U0001FAFF"  # supplemental symbols ext
    "\U00002600-\U000027BF"  # misc symbols + dingbats
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # ZWJ
    "\U000020E3"             # keycap
    "]+"
)


def _is_emoji_only(text: str) -> bool:
    """هل النص يتكون من إيموجي فقط (بدون أي حروف/أرقام)؟"""
    s = str(text or "").strip()
    if not s:
        return False
    stripped = _EMOJI_RE.sub("", s)
    stripped = re.sub(r"[\s\u200B-\u200D\u2060]", "", stripped)
    return len(stripped) == 0


def _is_reaction_text(text: str) -> bool:
    """هل الرسالة رد فعل (لايك/إيموجي) مسجَّل كنص من النظام؟"""
    low = str(text or "").strip().lower()
    return low.startswith("[customer reacted") or low.startswith("[customer sent reaction")


_OPTOUT_PATTERNS = (
    r"متبعتليش", r"متبعتلوش", r"متكلمنيش", r"متكلمناش", r"متزعجنيش",
    r"بلاش تبعت", r"بلاش رسا[يئ]ل", r"مش عايز رسا[يئ]ل", r"مش عايز اتصالات",
    r"مش مهتم", r"اوقفوا", r"اوقفو", r"وقفو", r"لا ترسل", r"لا تبعث",
    r"شيلني", r"انزعني", r"ممنوع ترسل", r"مش هحجز", r"مش ححجز",
    r"\bstop\b", r"\bunsubscribe\b", r"don'?t contact", r"no more messages",
    r"leave me alone", r"مكفيني", r"انتو ضايقيني", r"ضايقني",
    # ردود سلبية واضحة (شرط الإيقاف 4 في برومبت المدير)
    r"مش هسافر", r"مش حسافر", r"مش محتاج", r"الغاء", r"كفاية",
    r"سيبني", r"سيبنى", r"مش هعرف", r"مش هقدر", r"مش عايز السفر",
)


def _is_optout(text: str) -> bool:
    """كشف طلب العميل إيقاف التواصل نهائياً أو الرد السلبي الواضح."""
    norm = _normalize_keyword(text)
    for p in _OPTOUT_PATTERNS:
        if re.search(p, norm):
            return True
    return False


def _extract_phone(text: str):
    """استخراج رقم موبايل مصري (بأي صيغة: 010.. / 20 10.. / 002 10.. / +20 10..)."""
    s = _normalize_keyword(text)
    s = re.sub(r"[\s\-\.\(\)]", "", s)
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


# أنماط نية الحجز (العميل أكّد الحجز أو قال إنه حوّل العربون — شرط الإيقاف 3)
# ملاحظة دقة (قاعدة 9): استبعدنا نمط "حجز" المفرد العارم لأنه يلتقط أسئلة
# سعر/موعد تحتوي كلمة "الحجز" (مثل: "كام سعر الحجز؟" أو "الحجز بيبدأ إمتى؟")
# وهي ليست تأكيداً للحجز — الشروط المحددة أدناه (احجز/حجزت/تم الحجز/عربون/...)
# هي التي تعبّر فعلاً عن نية الحجز أو تأكيده.
_BOOKING_PATTERNS = (
    r"عربون",                       # ذكر العربون (حولت/دفعت/هحول العربون)
    r"حولت المبلغ", r"حولت المقدم", r"حولت العربون", r"حولت عربون",
    r"دفعت العربون", r"دفعت عربون", r"دفعت المقدم", r"دفعت المبلغ",
    r"اكدت الحجز", r"اكد الحجز", r"تاكيد الحجز", r"تأكيد الحجز",
    r"تم الحجز", r"حجزت", r"اتحجزت", r"اتأكد الحجز",
    r"احجز", r"عايز احجز", r"نفسي احجز", r"ابدا الحجز", r"ابداء الحجز",
    r"نبدا الحجز", r"نبداء الحجز", r"نبتدي الحجز", r"نبدأ الحجز",
    r"خطوات الحجز", r"طريقة الحجز", r"طريقه الحجز", r"ازاي احجز", r"ازاى احجز",
    r"اجراءات الحجز", r"اكمل الحجز", r"كمل الحجز", r"احجزلي", r"احجز ليا",
    r"حجز مكان",
    r"\bbook\b", r"\breserve\b", r"\bbooking\b", r"\bconfirmed\b",
)


def _is_booking_intent(text: str) -> bool:
    """كشف نية العميل في الحجز أو تأكيده أو تحويل العربون (شرط الإيقاف 3)."""
    norm = _normalize_keyword(text)
    for p in _BOOKING_PATTERNS:
        if re.search(p, norm):
            return True
    return False


# =============================================================================
# الأزرار الثلاثة (لاختيار نسخة نص الرسالة حسب آخر زرار ضغطه العميل)
# =============================================================================
BUTTONS = [
    {"version": 1, "raw": "ابعتولي برنامج الـ١٥ يوم بالتفصيل 📋"},
    {"version": 2, "raw": "إيه أقرب مواعيد السفر المتاحة؟ 🗓"},
    {"version": 3, "raw": "السعر ٤٠٬٩٥٠ شامل إيه بالظبط؟ 💰"},
]
for _b in BUTTONS:
    _b["norm"] = _normalize_keyword(_b["raw"])


def _select_message(version, stage) -> str:
    """اختيار نص الفولو اب حسب نسخة الزرار (١/٢/٣/٤) والمرحلة (1 أو 2)."""
    try:
        version = int(version or 4)
    except Exception:
        version = 4
    if version not in MSGS:
        version = 4
    return MSGS[version].get(f"fu{stage}", MSGS[4][f"fu{stage}"])


# =============================================================================
# استعلامات قاعدة البيانات (فلترة صارمة من الجذور — قاعدة النظام 10-7)
# =============================================================================
def _get_ad_conversations(cursor, now: datetime):
    """المحادثات الواردة من الإعلان المستهدف فقط.
    الفلترة تتم في SQL من الجذور:
      - facebook_ad_id = TARGET_AD_ID (شرط التفعيل الحصري — لا أي إعلان آخر).
      - last_message_time حديثة (خلال 25 ساعة) — أي محادثة أقدم من ذلك تكون
        نافذة الـ 24 ساعة مغلقة ولا يمكن مراسلتها أصلاً، فلا داعي لجلبها
        (تحسين الأداء بدلاً من جلب كل المحادثات وفلترتها برمجياً).
      - نرتب الأقدم أولاً (ASC) بحيث تُعالج المحادثات الأقرب لإغلاق نافذة
        مراحلها قبل الأحدث فلا تُحرم رسالة بسبب MAX_SENDS_PER_RUN.
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
    """آخر رسالة حقيقية في المحادثة (عميل أو رد منّا) — مرساة الفولو اب 1.
    نستبعد رسائل النظام/الإحالة ([Facebook Ad Referral]، [System Log]،
    [PROPOSED_DRAFT]، [Agent reacted...]) لأنها ليست تفاعلاً حقيقياً. أما
    رسائل الميديا من العميل فهي تفاعل حقيقي يُحتسب في التوقيت.
    نزيل أيضاً تكرارات received/sent لرسائل العميل (نحتفظ بالأقدم): فيسبوك
    يسجّل رسالة الزر مرتين (received ثم sent لاحقاً) — والتكرار المتأخر قد
    يسبق ردّنا زمنياً خطأً فيجعل "آخر رسالة" من العميل رغم أن ردّنا هو
    الأحدث فعلاً، مما يوقف الفولو اب 1 نهائياً (شرط "العميل لم يرد على
    آخر رسالة منّنا").
    يعيد (sender_type, text, timestamp) أو (None, None, None).
    """
    rows = cursor.execute(
        """
        SELECT sender_type, text, timestamp
        FROM messages
        WHERE chat_id = ?
        ORDER BY timestamp ASC
        """,
        (chat_id,),
    ).fetchall()
    real = []
    seen_norm_ts = {}
    for row in rows:
        sender_type = str(row[0] or "").strip().lower()
        text = str(row[1] or "")
        ts = _parse_dt(row[2])
        if ts is None:
            continue
        if _is_system_noise(text, sender_type):
            continue
        if sender_type not in ("customer", "agent", "ai"):
            continue
        if sender_type == "customer":
            norm = _normalize_keyword(text)
            if norm:
                # تكرار received/sent لنفس رسالة العميل خلال 5 دقائق → نحتفظ بالأقدم
                if norm in seen_norm_ts and abs((ts - seen_norm_ts[norm]).total_seconds()) < 300:
                    continue
                seen_norm_ts[norm] = ts
        real.append((sender_type, text, ts))
    if not real:
        return (None, None, None)
    real.sort(key=lambda r: r[2])
    return real[-1]


def _last_customer_message(cursor, chat_id):
    """آخر رسالة حقيقية من العميل — مرساة نافذة الـ 24 ساعة ومرحلة الفولو اب 2.
    (رسائل الميديا والتفاعلات/الإيموجي تُحتسب تفاعلاً حقيقياً لكن لا يُفحص
    نصها للكلمات المفتاحية — نعيد reaction_emoji للتعرف على اللايك/الإيموجي.)
    نزيل تكرارات received/sent (نحتفظ بالأقدم) مثل _last_real_message.
    يعيد (text, timestamp, reaction_emoji) أو (None, None, None).
    """
    rows = cursor.execute(
        """
        SELECT text, timestamp, reaction_emoji
        FROM messages
        WHERE chat_id = ? AND sender_type = 'customer'
        ORDER BY timestamp ASC
        """,
        (chat_id,),
    ).fetchall()
    best = (None, None, None)
    seen_norm_ts = {}
    for row in rows:
        text = str(row[0] or "")
        ts = _parse_dt(row[1])
        if ts is None:
            continue
        if _is_system_noise(text, "customer"):
            continue
        norm = _normalize_keyword(text)
        if norm:
            if norm in seen_norm_ts and abs((ts - seen_norm_ts[norm]).total_seconds()) < 300:
                continue
            seen_norm_ts[norm] = ts
        if best[1] is None or ts > best[1]:
            best = (text, ts, row[2])
    return best


def _agent_replied_after(cursor, chat_id, after_dt) -> bool:
    """هل ردّ المساعد الأساسي/الفريق برسالة حقيقية بعد لحظة معينة؟
    (نستخدمها لمنع الرد المزدوج عند الرد بلايك/إيموجي فقط: إذا كان المساعد
    الأساسي قد ردّ لحظياً بالفعل، لا نرسل رداً طبيعياً إضافياً من الـ workflow).
    """
    rows = cursor.execute(
        """
        SELECT sender_type, text, timestamp
        FROM messages
        WHERE chat_id = ? AND sender_type IN ('agent', 'ai')
        ORDER BY timestamp DESC
        LIMIT 40
        """,
        (chat_id,),
    ).fetchall()
    for row in rows:
        text = str(row[1] or "")
        ts = _parse_dt(row[2])
        if ts is None or ts <= after_dt:
            continue
        if _is_system_noise(text, str(row[0] or "")):
            continue
        return True
    return False


def _detect_button_version(cursor, chat_id) -> int:
    """تحديد نسخة نص الرسالة حسب آخر زرار ضغطه العميل في بداية المحادثة.
    نفحص رسائل العميل من الأقدم للأحدث ونحتفظ بآخر تطابق مع أحد الأزرار
    الثلاثة. لو مفيش أي زرار → النسخة العامة (4).
    """
    rows = cursor.execute(
        """
        SELECT text
        FROM messages
        WHERE chat_id = ? AND sender_type = 'customer'
        ORDER BY timestamp ASC
        LIMIT 200
        """,
        (chat_id,),
    ).fetchall()
    version = 4
    for row in rows:
        t = str(row[0] or "")
        if _is_system_noise(t, "customer"):
            continue
        norm = _normalize_keyword(t)
        if not norm:
            continue
        for b in BUTTONS:
            if norm == b["norm"]:
                version = b["version"]
                break
    return version


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


def _tag_chat(chat_id: str, tag: str, now_iso: str, dry_run: bool = False):
    """إضافة وسم (Tag) للمحادثة في sales_customer_state.tags (إضافة فقط —
    لا حذف لأي وسم أو حقل موجود، احتراماً لقاعدة النظام 8).
    """
    if dry_run:
        return
    try:
        conn = sqlite3.connect(DB_FILE, timeout=15.0)
        c = conn.cursor()
        c.execute("SELECT tags FROM sales_customer_state WHERE chat_id = ?", (chat_id,))
        row = c.fetchone()
        tags = []
        if row and row[0]:
            try:
                tags = json.loads(str(row[0]))
                if not isinstance(tags, list):
                    tags = []
            except Exception:
                tags = []
        if tag not in tags:
            tags.append(tag)
        c.execute(
            """
            INSERT INTO sales_customer_state (chat_id, tags, updated_at, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                tags = excluded.tags,
                updated_at = excluded.updated_at
            """,
            (chat_id, json.dumps(tags, ensure_ascii=False), now_iso, now_iso),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning(f"Failed to tag chat {chat_id} with '{tag}': {e}")


def _save_phone_and_notify(chat_id: str, phone: str, now_iso: str, dry_run: bool = False):
    """شرط الإيقاف 2: تسجيل الرقم في بيانات العميل (customer_phone) +
    إشعار فوري لفريق خدمة العملاء مع وسم "عميل جاهز للاتصال":
    needs_help=1 (يُظهر المحادثة للموظف البشري في لوحة التحكم) + System Log
    يحمل الوسم + tag في sales_customer_state.tags.
    ملاحظة: لا نرسل أي رسالة رد للعميل عند استلام الرقم — المساعد الأساسي/
    الفريق البشري هو من يتواصل معه (نفس سياسة Workflows المتابعة السابقة).
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
            f"[System Log] Umrah 15-day follow-up: customer phone received ({phone}) - وسم: عميل جاهز للاتصال - notify customer service team",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to save/notify phone for {chat_id}: {e}")
    _tag_chat(chat_id, "عميل جاهز للاتصال", now_iso, dry_run)


def _transfer_to_booking(chat_id: str, reason: str, now_iso: str, dry_run: bool = False):
    """شرط الإيقاف 3: تحويل المحادثة لفريق الحجز (إشعار للفريق البشري) +
    إيقاف السلسلة.
    """
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
            f"[System Log] Umrah 15-day follow-up: transferred to booking team ({reason})",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to transfer {chat_id}: {e}")
    _tag_chat(chat_id, "تحويل لفريق الحجز", now_iso, dry_run)


def _log_stop_reason(chat_id: str, reason: str, dry_run: bool = False):
    """تسجيل سبب إيقاف السلسلة في سجل المحادثة (أثر توثيقي فقط — لا رسالة للعميل)."""
    if dry_run:
        return
    try:
        import chat_db
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] Umrah 15-day follow-up: chain stopped ({reason})",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to log stop reason for {chat_id}: {e}")


# =============================================================================
# منطق الحالة ومعالجة الردود
# =============================================================================
def _init_entry(conv: dict, last_customer_ts: datetime, last_customer_text: str,
                now_iso: str) -> dict:
    """تهيئة سجل الحالة لمحادثة جديدة."""
    return {
        "last_customer_reply": last_customer_ts.isoformat(),
        "last_customer_text": str(last_customer_text or "")[:200],
        "button_version": 4,
        "fu1_sent_at": None,
        "fu2_sent_at": None,
        "total_fu_sent": 0,
        "stopped": False,
        "stop_reason": "",
        "opted_out": False,
        "sender_identifier": str(conv.get("sender_identifier") or "").strip(),
        "updated_at": now_iso,
    }


def _classify_customer_message(text: str, reaction_emoji=None):
    """تصنيف رسالة العميل الواردة:
    يعيد (category, phone) حيث category ∈ {opt_out, phone, booking, emoji, reply}.
    - opt_out: طلب إيقاف التواصل نهائياً أو رد سلبي واضح (إيقاف 4).
    - phone:   تحتوي رقم تليفون/واتساب (إيقاف 2 — تحويل لخدمة العملاء).
    - booking: نية حجز/تأكيد حجز/تحويل عربون (إيقاف 3 — تحويل لفريق الحجز).
    - emoji:   رد بلايك/إيموجي فقط (تفاعل يفتح نافذة جديدة — قاعدة المدير).
    - reply:   أي رد آخر (المساعد الأساسي يتعامل معه، ويبدأ العدّاد من جديد).
    """
    text = str(text or "")
    if _is_optout(text):
        return "opt_out", None
    phone = _extract_phone(text)
    if phone:
        return "phone", phone
    if _is_booking_intent(text):
        return "booking", None
    # لايك/إيموجي فقط (تفاعل أو رسالة إيموجي خالصة)
    if reaction_emoji or _is_reaction_text(text) or _is_emoji_only(text):
        return "emoji", None
    return "reply", None


def _handle_stop_categories(agent, conv, entry, category, phone, now, dry_run):
    """معالجة الفئات الإيقافية (opt_out / phone / booking) — تُوقف السلسلة.
    يعيد (action_key, sent) حيث sent = هل أُرسلت رسالة للعميل.
    """
    chat_id = str(conv.get("chat_id") or "").strip()
    sender_id = str(conv.get("sender_identifier") or "").strip()
    now_iso = now.isoformat()

    if category == "opt_out":
        _send_message(agent, conv, MSG_OPTOUT_APOLOGY, dry_run)
        _log_stop_reason(chat_id, "customer_opt_out_or_negative", dry_run)
        entry["opted_out"] = True
        entry["stopped"] = True
        entry["stop_reason"] = "customer_opt_out"
        return "opt_out", True, sender_id

    if category == "phone":
        # لا نرسل أي رد للعميل — فقط تسجيل الرقم + إشعار خدمة العملاء + وسم
        _save_phone_and_notify(chat_id, phone, now_iso, dry_run)
        entry["stopped"] = True
        entry["stop_reason"] = f"phone_received:{phone}"
        return "phone", False, sender_id

    if category == "booking":
        _transfer_to_booking(chat_id, "booking_confirmed_or_deposit", now_iso, dry_run)
        entry["stopped"] = True
        entry["stop_reason"] = "booking_intent"
        return "booking", False, sender_id

    return "reply", False, sender_id


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
    actions = {"fu1": 0, "fu2": 0, "emoji_reply": 0, "opt_out": 0, "phone": 0,
               "booking": 0, "reply_reset": 0, "window_closed": 0,
               "deferred_night": 0, "cap_reached": 0}

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        msg = f"Failed to connect to DB: {e}"
        log.error(f"[15DayFollowup] {msg}")
        return {"ok": False, "sent_count": 0, "errors": [msg], "message": msg}

    state = _load_state()
    chats = state.setdefault("chats", {})
    opted_out_senders = state.setdefault("opted_out_senders", {})

    try:
        conversations = _get_ad_conversations(cursor, now)
        log.info(f"[15DayFollowup] Found {len(conversations)} recent conversations for ad {TARGET_AD_ID}")

        # ===== تنظيف سجلات الحالة القديمة (نافذة مغلقة نهائياً منذ أكثر من ساعة) =====
        # أي محادثة انتهت نافذتها (أكثر من 25 ساعة من آخر تفاعل عميل) لا يمكن
        # مراسلتها بعد اليوم — نحذف سجلها لصغر ملف الحالة. لو ردّ العميل لاحقاً
        # تظهر المحادثة من جديد في الاستعلام ويُبنى سجل جديد تلقائياً.
        try:
            for cid in list(chats.keys()):
                e = chats.get(cid) or {}
                lc = _parse_dt(e.get("last_customer_reply"))
                if lc and (now - lc).total_seconds() / 3600.0 > (WINDOW_HOURS + 1):
                    chats.pop(cid, None)
        except Exception:
            pass

        for conv in conversations:
            chat_id = str(conv.get("chat_id") or "").strip()
            if not chat_id:
                continue
            if limit and processed_chats >= limit:
                break

            # ===== تدخّل موظف بشري → إيقاف السلسلة نهائياً =====
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

            # ===== استخراج مراسي الوقت (مرة واحدة لكل محادثة) =====
            last_cust_text, last_cust_ts, last_cust_reaction = _last_customer_message(cursor, chat_id)
            if last_cust_ts is None:
                continue
            last_sender, _, last_msg_ts = _last_real_message(cursor, chat_id)
            if last_msg_ts is None:
                last_msg_ts = last_cust_ts
            if last_sender is None:
                last_sender = "customer"

            sender_id = str(conv.get("sender_identifier") or "").strip()
            processed_chats += 1

            entry = chats.get(chat_id)
            is_new_entry = entry is None

            # ===== إيقاف محادثة قديمة قيد السلسلة لمرسل طلب الإيقاف =====
            # (opt-out دائم بالـ sender_identifier — لا سلسلة متابعة قديمة لعميل
            #  سبق وطلب عدم التواصل حتى لو كانت محادثة قديمة ما زالت قيد التتبع)
            if sender_id and sender_id in opted_out_senders:
                if entry is not None and not entry.get("stopped"):
                    entry["stopped"] = True
                    entry["stop_reason"] = "sender_opted_out"
                    entry["updated_at"] = now_iso
                    if not dry_run:
                        _save_state(state)
                continue

            if is_new_entry:
                entry = _init_entry(conv, last_cust_ts, last_cust_text, now_iso)
                entry["sender_identifier"] = sender_id
                entry["button_version"] = _detect_button_version(cursor, chat_id)
                chats[chat_id] = entry

            if entry.get("stopped"):
                continue

            # ===== نافذة الـ 24 ساعة من آخر تفاعل عميل انتهت → إيقاف نهائي =====
            elapsed_cust = (now - last_cust_ts).total_seconds() / 3600.0
            if elapsed_cust >= WINDOW_HOURS:
                if int(entry.get("total_fu_sent") or 0) == 0 and is_new_entry:
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

            # ===== كشف رد جديد من العميل أثناء السلسلة → معالجة فورية =====
            # ملاحظة: للمحادثة الجديدة نعتبر آخر رسالة عميل "جديدة" دائماً حتى
            # نصنّف أول رسالة (رقم/حجز/إيقاف/إيموجي) فوراً — لو تركناه كما هو
            # كان last_customer_reply يساوي آخر رسالة فلا تُصنَّف أبداً.
            if is_new_entry:
                new_cust_msg = True
            else:
                prev_cust_ts = _parse_dt(entry.get("last_customer_reply"))
                new_cust_msg = prev_cust_ts is None or last_cust_ts > prev_cust_ts
            if new_cust_msg:
                category, phone = _classify_customer_message(last_cust_text, last_cust_reaction)

                if category in ("opt_out", "phone", "booking"):
                    action_key, sent, opted_sender = _handle_stop_categories(
                        agent, conv, entry, category, phone, now, dry_run)
                    actions[action_key] = actions.get(action_key, 0) + 1
                    if category == "opt_out" and opted_sender:
                        opted_out_senders[opted_sender] = now_iso
                    entry["last_customer_text"] = str(last_cust_text or "")[:200]
                    entry["last_customer_reply"] = last_cust_ts.isoformat()
                    entry["updated_at"] = now_iso
                    if sent:
                        sent_count += 1
                    if not dry_run:
                        _save_state(state)
                    if sent_count >= MAX_SENDS_PER_RUN:
                        break
                    continue

                if category == "emoji":
                    # لايك/إيموجي فقط → تفاعل يفتح نافذة جديدة: نرد رداً طبيعياً
                    # (إن لم يسبق المساعد الأساسي بالرد لحظياً — منع الرد المزدوج)
                    if not _agent_replied_after(cursor, chat_id, last_cust_ts):
                        ok, err = _send_message(agent, conv, MSG_EMOJI_REPLY, dry_run)
                        if ok:
                            sent_count += 1
                            actions["emoji_reply"] = actions.get("emoji_reply", 0) + 1
                        else:
                            errors.append(f"emoji_reply->{chat_id}: {err}")
                    # تبدأ دورة الفولو اب من جديد (نافذة جديدة — تصفير المراحل)
                    entry["fu1_sent_at"] = None
                    entry["fu2_sent_at"] = None
                    entry["button_version"] = _detect_button_version(cursor, chat_id)
                    entry["last_customer_text"] = str(last_cust_text or "")[:200]
                    entry["last_customer_reply"] = last_cust_ts.isoformat()
                    entry["updated_at"] = now_iso
                    if not dry_run:
                        _save_state(state)
                    if sent_count >= MAX_SENDS_PER_RUN:
                        break
                    continue

                # أي رد آخر → إلغاء الفولو اب المجدول + إعادة العدّاد من جديد
                # (المساعد الأساسي يرد على العميل لحظياً — العدّاد يبدأ بعد آخر
                #  رد منّنا، وسقف الـ ٢ رسالة يبقى كما هو)
                entry["fu1_sent_at"] = None
                entry["fu2_sent_at"] = None
                entry["button_version"] = _detect_button_version(cursor, chat_id)
                entry["last_customer_text"] = str(last_cust_text or "")[:200]
                entry["last_customer_reply"] = last_cust_ts.isoformat()
                entry["updated_at"] = now_iso
                actions["reply_reset"] = actions.get("reply_reset", 0) + 1
                if not dry_run:
                    _save_state(state)
                # لا نرسل فولو اب في نفس دورة وصول رد العميل (النافذة بدأت للتو)
                if not is_new_entry:
                    continue
                # لمحادثة جديدة (seed): نكمل لمنطق الجدولة — قد تكون المتابعة
                # مستحقة بالفعل إن مرّت ٣ ساعات على آخر رد منّنا.

            # ===== لا رد جديد → منطق الجدولة الزمنية =====
            total_fu = int(entry.get("total_fu_sent") or 0)
            # الحد الأقصى: رسالتا فولو اب فقط لكل محادثة مهما كانت الظروف
            if total_fu >= MAX_FU_PER_CHAT:
                actions["cap_reached"] = actions.get("cap_reached", 0) + 1
                continue

            # ساعات الليل الصامتة [23:00, 09:00) بتوقيت القاهرة:
            # نؤجّل لأول دورة بعد ٩ صباحاً (التأجيل يحترم حد الـ ٢٣ ساعة
            # للفولو اب الثاني تلقائياً لأن شرط اللياقة يقيّمه كل دورة)
            if _in_quiet_hours(now):
                actions["deferred_night"] = actions.get("deferred_night", 0) + 1
                continue

            elapsed_msg = (now - last_msg_ts).total_seconds() / 3600.0

            # المرحلة 1: الفولو اب الأول
            # T >= 3 ساعات منذ آخر رسالة (عميل أو منّا) + آخر رسالة من عندنا
            # (العميل لم يرد على آخر رسالة منّنا) + لم يُرسل من قبل + النافذة
            # ما زالت مفتوحة بهامش أمان 23.9 ساعة.
            # ملاحظة: الشرط total_fu < MAX_FU_PER_CHAT (وليس < 1) حتى تعمل
            # إعادة تعيين الدورة بعد رد/إيموجي العميل (قاعدة المدير: "يبدأ
            # العدّاد من جديد بعد آخر رد منّنا") مع بقاء السقف الكلي ٢ فقط.
            if (total_fu < MAX_FU_PER_CHAT
                    and not entry.get("fu1_sent_at")
                    and last_sender in ("agent", "ai")
                    and elapsed_msg >= FU1_HOURS
                    and elapsed_cust < SEND_SAFETY_HOURS):
                target = 1
            # المرحلة 2: الفولو اب الثاني
            # مرّ 20 ساعة أو أكثر على آخر تفاعل عميل + لم يمر 23 ساعة +
            # أُرسل الفولو اب الأول + لم يُرسل الثاني + لا رد عميل جديد بعده
            # (لو رد العميل، كنا صفّرنا المراحل في معالجة الردود أعلاه) +
            # السقف الكلي (٢ رسالة فولو اب فقط لكل محادثة مهما كانت الظروف).
            elif (total_fu < MAX_FU_PER_CHAT
                    and entry.get("fu1_sent_at")
                    and not entry.get("fu2_sent_at")
                    and elapsed_cust >= FU2_MIN_HOURS
                    and elapsed_cust < FU2_MAX_HOURS):
                target = 2
            else:
                target = 0

            if target == 0:
                continue

            msg = _select_message(entry.get("button_version") or 4, target)
            if not msg:
                continue

            ok, err = _send_message(agent, conv, msg, dry_run)
            if ok:
                entry[f"fu{target}_sent_at"] = now_iso
                entry["total_fu_sent"] = total_fu + 1
                entry["updated_at"] = now_iso
                actions[f"fu{target}"] = actions.get(f"fu{target}", 0) + 1
                sent_count += 1
                if not dry_run:
                    _save_state(state)  # حفظ فوري بعد كل إرسال (منع التكرار)
                if sent_count >= MAX_SENDS_PER_RUN:
                    break
            else:
                errors.append(f"fu{target}->{chat_id}: {err}")

        message = (
            f"Ad {TARGET_AD_ID}: sent={sent_count} | processed={processed_chats} "
            f"| actions={actions} | errors={len(errors)}"
        )
        log.info(f"[15DayFollowup] {message}")
        return {
            "ok": len(errors) == 0,
            "sent_count": sent_count,
            "processed_chats": processed_chats,
            "actions": actions,
            "errors": errors[:20],
            "message": message,
        }
    except Exception as e:
        msg = f"Error in 15-day follow-up run: {e}"
        log.error(f"[15DayFollowup] {msg}")
        return {"ok": False, "sent_count": sent_count, "errors": [msg], "message": msg}
    finally:
        try:
            if not dry_run:
                _save_state(state)
            conn.close()
        except Exception:
            pass
