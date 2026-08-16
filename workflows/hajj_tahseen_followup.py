# -*- coding: utf-8 -*-
"""
Workflow: Hajj Tahseen 3-Stage Follow-Up - Religious - حج طيران تحسين (ديني)
===========================================================================
نظام Follow-Up تلقائي متعدد المراحل لإعلان برنامج حج طيران تحسين.

شرط التفعيل (فلترة صارمة من الجذور في SQL - لا نلمس أي إعلان أو قسم آخر):
    WHERE facebook_ad_id = '120246971083710757'
    AND (is_deleted IS NULL OR is_deleted = 0)

قاعدة التوقيت الأساسية:
    - يبدأ العد من آخر رسالة أرسلها العميل (sender_type='customer') وليس من
      أول رسالة في المحادثة، وليس من رسائل النظام مثل:
      [Facebook Ad Referral] / [customer sent an audio ...] / [customer sent a video ...]
      (تم استثناء هذه الرسائل لأنها ليست تفاعلاً حقيقياً من العميل).
    - جميع الرسائل تُرسل داخل نافذة الـ 24 ساعة الخاصة بـ Meta:
      المرحلة 3 لا تُرسل بعد مرور 22 ساعة كحد أقصى (هامش أمان لتجنب Error #10).

التسلسل الثلاثي (بعد آخر رد للعميل بدون تفاعل):
    - المرحلة 1: بعد ساعتين (أو 45 دقيقة للـ lead الساخن الذي ضغط زرار "إزاي أحجز؟")
    - المرحلة 2: بعد 8 ساعات
    - المرحلة 3: بعد 21 ساعة (لا تتأخر عن الساعة 22)

الكلمات المفتاحية أثناء التسلسل:
    - "ملخص"        → يُرسل ملخص البرنامج الكامل ثم يعيد ضبط العداد (يوقف التسلسل الحالي).
    - "أحجز"        → يُرسل خطوات الحجز والمستندات ثم يحوّل المحادثة لموظف خدمة العملاء.
    - رقم موبايل    → يُسجَّل الرقم ويُشكر العميل ثم يُحوَّل كـ lead ساخن.
    - طلب إيقاف     → يُوقَف الإرسال نهائياً لهذه المحادثة (opt-out) ولا نرسل مجدداً أبداً.
    - أي رد آخر     → يُعاد ضبط العداد من رده الجديد (المساعد الأساسي يجاوب على استفساره).

قاعدة عدم التكرار:
    - لا نكرر التسلسل لنفس العميل: إذا اكتمل التسلسل الثلاثي بدون أي رد
      (مرور 24 ساعة من آخر رد للعميل مع إرسال مرحلة واحدة على الأقل)
      نضع على المحادثة tag: no-response-hajj-tahseen ونتوقف نهائياً.

ملاحظات هندسية (لماذا هذه الشروط):
    - التوقيت: نستخدم chat_db.get_cairo_time() (توقيت القاهرة UTC+3) كما يفعل
      النظام بالكامل، ولا نستخدم datetime.now(timezone.utc) إطلاقاً لمنع
      انحراف 3 ساعات في منطق المراحل (قاعدة النظام F).
    - الحالة: يُمنع استخدام agent.load_state/save_state (غير موجودة على الـ agent
      في run_script)، لذا نستخدم ملف JSON محلي عبر fts_paths.get_data_path
      (قاعدة النظام G) لمنع التكرار اللانهائي وإعادة الإرسال.
    - الحماية من التداخل البشري: نتخطى المحادثات التي بها needs_help=1 أو
      is_closed=1 أو auto_reply_hold_until في المستقبل حتى لا نتداخل مع موظف بشري.
    - حد أقصى للإرسال في كل تشغيل (MAX_SENDS_PER_RUN) حتى لا تتجاوز مدة
      التشغيل timeout الـ http_request (60 ثانية) — التشغيل التالي يكمل الباقي
      لأن الحالة محفوظة فور كل إرسال.
    - نصوص الرسائل الثلاثة تُرسل كما هي بالحرف (لا نعيد صياغتها).
"""

import os
import sys
import json
import re
import sqlite3
import logging
import time
import threading
from datetime import datetime, timedelta

from fts_paths import get_data_path

# =============================================================================
# ثوابت السير العمل
# =============================================================================
# الإعلان المستهدف فقط (شرط التفعيل الحصري)
TARGET_AD_ID = "120246971083710757"

# قاعدة بيانات المحادثات (نفس مسار chat_db)
DB_FILE = get_data_path("chat_history.db")

# ملف الحالة المحلي (قاعدة النظام G: يُمنع agent.load_state)
STATE_FILE = get_data_path("hajj_tahseen_followup_state.json")

# عتبات التوقيت بالساعات (مقاسة من آخر رد للعميل)
STAGE1_HOURS_NORMAL = 2.0          # الرسالة 1 بعد ساعتين
STAGE1_HOURS_HOT = 0.75            # الرسالة 1 بعد 45 دقيقة فقط للـ lead الساخن
STAGE2_HOURS = 8.0                 # الرسالة 2 بعد 8 ساعات
STAGE3_HOURS_MIN = 21.0            # الرسالة 3 بعد 21 ساعة
STAGE3_HOURS_MAX = 22.0            # حد أقصى: لا ترسل بعد الساعة 22 (هامش نافذة 24 ساعة)
WINDOW_HOURS = 24.0                # نافذة Meta الكاملة

# حد أقصى للإرسال في كل تشغيل (حتى لا يتجاوز timeout الـ http_request)
MAX_SENDS_PER_RUN = 20

# الـ tag المطلوب وضعه عند اكتمال التسلسل الثلاثي بدون رد
TAG_NO_RESPONSE = "no-response-hajj-tahseen"
TAG_HOT_LEAD = "hajj-tahseen-hot-lead"

log = logging.getLogger("HajjTahseenFollowup")

# =============================================================================
# نصوص الرسائل (كما هي بالحرف — لا تغيير ولا إعادة صياغة)
# =============================================================================
# تحديث 2026-08-11 من المدير: رسالة 1 الجديدة - مقارنة قرعة الداخلية/التضامن بحج السياحة
MSG_STAGE1_NORMAL = (
    "حضرتك لسه معانا؟ 🕋\n"
    "قبل ما تقرر تقدّم في قرعة الداخلية أو التضامن، في حقيقة لازم تعرفها: اللي بيقدّم في القرعة بيقفل على نفسه باب حج السياحة — مينفعش تقدّم إلا في جهة واحدة بس.\n"
    "وحج السياحة الموسم اللي فات كان أعلى الجهات في نسب الفوز 👌 يعني فرصتك معانا أكبر بكتير.\n"
    "والتقديم أسهل مما تتخيل: صورة البطاقة بس وإحنا نبدأ إجراءات تقديمك فورًا 📋\n"
    "لو في أي سؤال محيّرك — عن الإقامة أو المشاعر أو الدفع — اكتبهولي وأنا أجاوبك حالًا ✅"
)

# بديل الرسالة 1 للـ lead الساخن (ضغط زرار "إزاي أحجز؟") — محتواه عن خطوات
# الحجز مباشرة. (تحديث 2026-08-02 من المدير: المتطلب الجديد صورة البطاقة
# ورقم تليفون — بدل المستندات القديمة جواز السفر والصورة الشخصية)
MSG_STAGE1_HOT = (
    "حضرتك لسه معانا؟ 📋\n"
    "لأن حضرتك سألت عن الحجز، دي خطوات الحجز في برنامج طيران تحسين:\n"
    "✅ المطلوب من حضرتك: صورة البطاقة ورقم تليفون لحضرتك\n"
    "لو في أي سؤال تاني، اكتبهولي وأنا أجاوبك فورًا ✅"
)

# تحديث 2026-08-11 من المدير: رسالة 2 الجديدة - مميزات التقديم في حج السياحة مع FTS
MSG_STAGE2 = (
    "عارفين إن قرار الحج مش سهل، وإن حضرتك ممكن تكون لسا محتار اقدم في الداخليه ولا السياحه 🧡 خلينا نقولك المميزات في التقديم معانا :\n"
    "📌 سحب على 3 عمرات مجانية لو ما فزتش → في بث مباشر .\n"
    "📌 تصعيد الاحتياطي من 1 لـ 3 → يعني حتي لو خسرت في فرصة تحج.\n"
    "📌 سحب على تذكرة طيران هدية → في بث مباشر وممكن تبقي من نصيبك.\n"
    "معانا في FTS — شركة مرخصة من وزارة السياحة فئة (أ) ترخيص رقم 2089 — نسب الفوز في حج السياحة الموسم اللي فات كانت الأعلى، ومعاك مشرفينا من أول يوم لحد الرجوع بالسلامة.\n"
    "السؤال الحقيقي: حضرتك عايز مجرد فرصة في الحج ولا عايز أكبر فرصة حقيقية تحج فعلًا؟ 🕋\n"
    "ابعتلنا صورة بطاقتك دلوقتي وإحنا نبدأ إجراءات تقديمك."
)

# تحديث 2026-08-11 من المدير: رسالة 3 الجديدة - رسالة الأمل والتفاؤل بالحج مع خصم المبكر
MSG_STAGE3 = (
    "أنت من حجاج هذا العام — أسأل الله أن نُبشرك 🕋🤲\n"
    "الجملة دي نفسنا نقولهالك قريب. وأول خطوة ليها بإيدك النهارده:\n"
    "صورة بطاقتك بس — وإحنا نبدأ إجراءات تقديمك فورًا، ونتابع ملفك خطوة بخطوة، ومشرفينا معاك من لحظة القبول لحد الرجوع بالسلامة.\n"
    "✅ خصم الحجز المبكر (٢٩ ألف جنيه) لسه موجود — لفترة محدودة\n"
    "✅ الاماكن معانا المتبقيه مش كتير والحصص قاربت علي الاكتمال\n"
    "✅ ومعانا فرصتك أعلى — أعلى الجهات نسب فوز الموسم اللي فات\n"
    "اللهم ارزقه حج بيتك 🤲\n"
    "ابعت البطاقة دلوقتي — أو رقم الواتساب لو تحب حد من فريقنا يكلمك الأول ☎️"
)

# رد كلمة "ملخص" — ملخص برنامج طيران تحسين الكامل (حسب مواصفات المدير حرفياً)
MSG_SUMMARY = (
    "تفضل حضرتك، ملخص برنامج طيران تحسين الكامل: 🕋\n\n"
    "💰 السعر: ٢٥٠ ألف جنيه (بدلًا من ٢٧٩ ألف)\n"
    "✈️ غير شامل تذكرة الطيران\n"
    "🚄 قطار الحرمين\n"
    "🕌 أقل فترة إقامة بعيدة عن الحرم\n"
    "🏕️ مخيمات مكيفة\n\n"
    "📌 السعر استرشادي، والتأكيد النهائي بعد ضوابط وزارة السياحة.\n\n"
    "لو حابب تحجز مكانك، ابعت كلمة \"أحجز\" وهنمشي معاك خطوة بخطوة ✅"
)

# رد كلمة "أحجز" — خطوات الحجز المبسطة ثم التحويل لخدمة العملاء
# (تحديث 2026-08-02 من المدير): المطلوب فقط صورة البطاقة ورقم تليفون
MSG_BOOKING_STEPS = (
    "أهلًا بحضرتك، خطوات الحجز في برنامج طيران تحسين: 📋\n\n"
    "✅ المطلوب من حضرتك:\n"
    "صورة البطاقة ورقم تليفون لحضرتك\n\n"
    "واحد من فريق خدمة العملاء هيتواصل معاك فورًا لاستكمال الخطوات. 🧡"
)

# رد عند إرسال رقم موبايل/واتساب — شكر وتسجيل وتحويل كـ lead ساخن
MSG_PHONE_THANKS = (
    "تم استلام رقم حضرتك، شكرًا لثقتك في FTS للسياحة 🧡\n"
    "واحد من فريقنا هيتواصل معاك في أقرب وقت."
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


# =============================================================================
# أدوات الحالة المحلية (قاعدة النظام G - ملف JSON عبر fts_paths)
# =============================================================================
def _load_state() -> dict:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            if isinstance(data, dict) and "chats" in data:
                return data
            # توافق مع الصيغ القديمة إن وُجدت
            return {"chats": data if isinstance(data, dict) else {}}
    except Exception as e:
        log.error(f"Failed to load state: {e}")
    return {"chats": {}}


# قفل ثابت عبر إعادة تحميل الموديول (run_script يعيد exec_module في كل تشغيل)
if not hasattr(sys, "_hajj_tahseen_followup_state_lock"):
    sys._hajj_tahseen_followup_state_lock = threading.Lock()
_STATE_LOCK = sys._hajj_tahseen_followup_state_lock


def _save_state(state: dict):
    """حفظ فوري بعد كل حدث مهم حتى لا نكرر الإرسال لو توقف التشغيل فجأة."""
    tmp_path = STATE_FILE + ".tmp"
    last_err = None
    with _STATE_LOCK:
        for attempt in range(6):
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(state, f, ensure_ascii=False)
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        pass
                os.replace(tmp_path, STATE_FILE)
                return
            except OSError as e:
                last_err = e
                # 22=EINVAL, 13=EACCES, 5=EIO — قفل مؤقت شائع على Windows
                if getattr(e, "errno", None) not in (5, 13, 22):
                    break
                time.sleep(0.05 * (attempt + 1))
            except Exception as e:
                last_err = e
                break
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        log.error(f"Failed to save state: {last_err}")


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


def _is_referral_or_media(text: str) -> bool:
    """رسائل النظام/الميديا التي ليست تفاعلاً حقيقياً من العميل:
    [Facebook Ad Referral] (وصول من إعلان) ورسائل الميديا غير النصية.
    """
    t = str(text or "").strip()
    if not t:
        return True
    if t.startswith("[Facebook Ad Referral]"):
        return True
    low = t.lower()
    prefixes = (
        "[customer sent an audio message",
        "[customer sent a video",
        "[customer sent a sticker",
        "[customer sent a document",
        "[customer sent a message of type",
        "[customer shared a location",
        "[customer shared contacts",
    )
    return any(low.startswith(p) for p in prefixes)


_OPTOUT_PATTERNS = (
    r"متبعتليش", r"متبعتلوش", r"متكلمنيش", r"متكلمناش", r"متزعجنيش",
    r"بلاش تبعت", r"بلاش رسا[يئ]ل", r"مش عايز رسا[يئ]ل", r"مش عايز اتصالات",
    r"مش مهتم", r"اوقفوا", r"اوقفو", r"وقفو", r"لا ترسل", r"لا تبعث",
    r"شيلني", r"انزعني", r"\bstop\b", r"\bunsubscribe\b", r"don'?t contact",
    r"no more messages", r"ممنوع ترسل",
)


def _is_optout(text: str) -> bool:
    """كشف طلب العميل إيقاف التواصل نهائياً (لا نرسل له مجدداً أبداً)."""
    norm = _normalize_keyword(text)
    for p in _OPTOUT_PATTERNS:
        if re.search(p, norm):
            return True
    return False


def _extract_phone(text: str):
    """استخراج رقم موبايل مصري (بأي صيغة: 010.. / 20 10.. / 002 10.. / +20 10..).
    ملاحظة: _normalize_keyword يحذف '+' والمسافات لذا نتعامل مع الأرقام فقط بعد
    التنظيف، ونتعامل مع البادئات الدولية 002 / 20 / +20.
    """
    s = _normalize_keyword(text)
    s = re.sub(r"[\s\-\.\(\)]", "", s)
    # البادئات الاختيارية: 002 / 20 — ثم 0?1[0125] متبوعاً بـ 8 أرقام
    # (يغطي: 01012345678 / 201012345678 / 00201012345678 / 1012345678)
    m = re.search(r"(?<!\d)(?:002|20)?0?1[0125][0-9]{8}(?!\d)", s)
    if not m:
        return None
    digits = m.group(0)
    if digits.startswith("002"):
        digits = digits[3:]
    elif digits.startswith("20") and len(digits) >= 12:
        digits = digits[2:]
    # توحيد الصيغة النهائية: 10xxxxxxxx (بدون صفر بادئ) → 010xxxxxxxx
    if len(digits) == 10 and digits.startswith("1"):
        digits = "0" + digits
    return digits if len(digits) >= 11 else None


# =============================================================================
# استعلامات قاعدة البيانات (فلترة صارمة من الجذور)
# =============================================================================
def _get_ad_conversations(cursor):
    """المحادثات الواردة من الإعلان المستهدف فقط (شرط التفعيل الحصري).
    الفلترة تتم في SQL من الجذور (facebook_ad_id = TARGET_AD_ID) وليس برمجياً.
    """
    cursor.execute(
        """
        SELECT chat_id, sender_identifier, contact_name, source, location,
               receiving_phone_id, last_message_time, needs_help, is_closed,
               auto_reply_hold_until, customer_phone
        FROM conversations
        WHERE facebook_ad_id = ?
          AND (is_deleted IS NULL OR is_deleted = 0)
          AND last_message_time IS NOT NULL
        -- ملاحظة هندسية: نرتب الأقدم أولاً (ASC) بحيث تُعالج المحادثات الأقرب
        -- لإغلاق نافذة مراحلها (مثل نافذة M3 [21,22)) قبل المحادثات الأحدث،
        -- فلا تُحرم رسالة M3 بسبب حد MAX_SENDS_PER_RUN عند وجود تراكم (Backlog).
        ORDER BY last_message_time ASC
        """,
        (TARGET_AD_ID,),
    )
    rows = cursor.fetchall()
    return [dict(r) for r in rows] if rows else []


def _last_customer_message(cursor, chat_id):
    """
    آخر رسالة أرسلها العميل فعلياً (توقيت العد الأساسي).
    نستبعد فقط رسائل الإحالة/النظام ([Facebook Ad Referral]...) لأنها ليست
    تفاعلاً حقيقياً من العميل. أما رسائل الميديا (صوت/فيديو/صورة/ستيكر) فهي
    رد حقيقي من العميل → تُبقي المرساة سليمة (تعيد ضبط العداد) لكن نصها لا
    يُفحص للكلمات المفتاحية لأنه لا يحتوي كلاماً مكتوباً.
    """
    cursor.execute(
        """
        SELECT text, timestamp
        FROM messages
        WHERE chat_id = ? AND sender_type = 'customer'
        ORDER BY timestamp DESC
        LIMIT 10
        """,
        (chat_id,),
    )
    for row in cursor.fetchall():
        text, ts = str(row[0] or ""), row[1]
        if text.startswith("[Facebook Ad Referral]") or text.startswith("[Facebook Referral]") \
           or text.startswith("[System Log]") or text.startswith("[System]"):
            continue
        return text, ts
    return None, None


def _first_customer_messages(cursor, chat_id, limit: int = 5):
    """
    أول رسائل العميل النصية الحقيقية (نستبعد رسائل الإحالة/النظام).
    تُستخدم لتصنيف الـ lead حسب الزرار الذي ضغطه العميل في بداية المحادثة —
    نفحص أكثر من رسالة لأن الزرار قد يأتي بعد رسالة إحالة أو مع رسالة أخرى.
    """
    cursor.execute(
        """
        SELECT text, timestamp
        FROM messages
        WHERE chat_id = ? AND sender_type = 'customer'
        ORDER BY timestamp ASC
        LIMIT 20
        """,
        (chat_id,),
    )
    out = []
    for row in cursor.fetchall():
        text = str(row[0] or "")
        if _is_referral_or_media(text):
            continue
        out.append(text)
        if len(out) >= limit:
            break
    return out


def _first_customer_message(cursor, chat_id):
    """أول رسالة نصية حقيقية من العميل (للعرض والتسجيل فقط)."""
    msgs = _first_customer_messages(cursor, chat_id, limit=1)
    return msgs[0] if msgs else ""


def _hold_active(hold_until, now) -> bool:
    """هل فترة إيقاف الرد الآلي (auto_reply_hold_until) ما زالت سارية؟"""
    if not hold_until:
        return False
    d = _parse_dt(hold_until)
    return bool(d and d > now)


# =============================================================================
# منطق المراحل والتصنيف
# =============================================================================
def _classify_hot_lead(first_messages) -> bool:
    """
    تصنيف حسب الزرار الذي ضغطه العميل في بداية المحادثة:
    - زرار "إزاي أحجز؟" → lead ساخن (رسالة 1 بعد 45 دقيقة + محتوى خطوات الحجز)
    - "تفاصيل البرنامج" / "مميزات طيران تحسين" → التسلسل العادي
    نفحص كل الرسائل الأولى (قائمة) وليس رسالة واحدة فقط حتى لا نفوت زرار
    الساخن إذا سبقته رسالة أخرى (مثل رسالة الإحالة أو زرار عادي).
    """
    for first_text in (first_messages or []):
        norm = _normalize_keyword(first_text)
        if re.search(r"احجز", norm):
            return True
    return False


def _target_stage(elapsed_h: float, hot_lead: bool):
    """تحديد المرحلة المستحقة بناءً على الوقت المنقضي من آخر رد للعميل.
    ترتيب إجباري مع Catch-up: لو فاتت مرحلة سابقة ننتقل للمرحلة التالية
    مباشرة بدلاً من إرسال مرحلتين في نفس التشغيل (لا رسالة أكثر من واحدة
    في كل مرحلة، ولا رسالة واحدة مضاعفة في التشغيل الواحد).
    """
    th1 = STAGE1_HOURS_HOT if hot_lead else STAGE1_HOURS_NORMAL
    if elapsed_h < th1:
        return None
    if elapsed_h < STAGE2_HOURS:
        return 1
    if elapsed_h < STAGE3_HOURS_MIN:
        return 2
    if elapsed_h < STAGE3_HOURS_MAX:
        return 3
    return None  # >= 22 ساعة: لا نرسل (نافذة الـ 24 ساعة على وشك الإغلاق)


def _stage_message(stage: int, hot_lead: bool) -> str:
    if stage == 1:
        return MSG_STAGE1_HOT if hot_lead else MSG_STAGE1_NORMAL
    if stage == 2:
        return MSG_STAGE2
    if stage == 3:
        return MSG_STAGE3
    return ""


# =============================================================================
# الإرسال والتحويل والتاج
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
        # القناة تُحدَّد من عمود source أساساً (أدق وأأمن من تخمين المعرفات:
        # بعض معرّفات Facebook PSID قد تبدأ بأرقام مشابهة لأرقام الهواتف).
        # استدلال الرقم المصري (20...) احتياطي فقط عندما يكون المصدر غير معروف.
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


def _transfer_to_customer_service(chat_id: str, reason: str, phone: str = None, dry_run: bool = False):
    """تحويل المحادثة لموظف خدمة العملاء:
    needs_help=1 (يوقف الرد الآلي ويُظهر المحادثة للموظف البشري)
    + تسجيل الـ lead الساخن في sales_customer_state.
    """
    if dry_run:
        return
    try:
        import chat_db
        if phone:
            try:
                chat_db.update_conversation_info(chat_id, customer_phone=phone)
            except Exception:
                pass
        chat_db.update_conversation_info(chat_id, needs_help=True)
        # دمج الـ tag مع أي tags موجودة (لا نحذف الموجود)
        existing = chat_db.get_sales_state(chat_id) or {}
        tags = str(existing.get("tags") or "")
        if TAG_HOT_LEAD not in tags:
            tags = (tags + "," + TAG_HOT_LEAD) if tags else TAG_HOT_LEAD
        chat_db.upsert_sales_state(chat_id, {"tags": tags, "lead_status": "new"})
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] Follow-up workflow: transferred to customer service ({reason})",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to transfer {chat_id}: {e}")


def _apply_no_response_tag(chat_id: str, dry_run: bool = False):
    """وضع tag: no-response-hajj-tahseen بعد اكتمال التسلسل الثلاثي بدون رد."""
    if dry_run:
        return
    try:
        import chat_db
        existing = chat_db.get_sales_state(chat_id) or {}
        tags = str(existing.get("tags") or "")
        if TAG_NO_RESPONSE not in tags:
            tags = (tags + "," + TAG_NO_RESPONSE) if tags else TAG_NO_RESPONSE
            chat_db.upsert_sales_state(chat_id, {"tags": tags})
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] Tagged: {TAG_NO_RESPONSE} (3-stage follow-up completed with no response)",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to tag {chat_id}: {e}")


def _init_entry(first_messages, last_text: str, last_ts: datetime, now_iso: str) -> dict:
    """تهيئة سجل الحالة لمحادثة جديدة (يُصنَّف الـ lead مرة واحدة ويُحفظ)."""
    first_msgs = list(first_messages or [])
    return {
        "last_customer_reply": last_ts.isoformat(),
        "highest_stage_sent": 0,
        "stages": {},
        "hot_lead": _classify_hot_lead(first_msgs),
        "first_customer_text": str((first_msgs[0] if first_msgs else "") or "")[:200],
        "last_customer_text": str(last_text or "")[:200],
        "opted_out": False,
        "handled": False,
        "handled_reason": "",
        "sequence_done": False,
        "tagged": False,
        "updated_at": now_iso,
    }


def _reset_counter(entry: dict, ts: datetime):
    """إعادة ضبط العداد من رد العميل الجديد (قاعدة التوقيت الأساسية)."""
    entry["last_customer_reply"] = ts.isoformat()
    entry["highest_stage_sent"] = 0
    entry["stages"] = {}
    entry["sequence_done"] = False
    entry["tagged"] = False


def _process_new_reply(agent, conv, entry, text, ts, now, dry_run):
    """معالجة رد/رسالة جديدة من العميل:
    - opt-out → إيقاف نهائي.
    - "ملخص" → ملخص البرنامج + إعادة ضبط العداد.
    - "أحجز" → خطوات الحجز + تحويل لخدمة العملاء.
    - رقم موبايل → تسجيل + شكر + تحويل كـ lead ساخن.
    - أي رد آخر → إعادة ضبط العداد فقط (المساعد الأساسي يجيب على الاستفسار).
    يعيد (action, sent) حيث sent=هل تم إرسال رسالة.
    """
    chat_id = str(conv.get("chat_id") or "").strip()
    norm = _normalize_keyword(text)

    if _is_optout(text):
        entry["opted_out"] = True
        entry["handled"] = True
        entry["handled_reason"] = "customer_opt_out"
        return "opt_out", False

    phone = _extract_phone(text)
    if phone:
        _send_message(agent, conv, MSG_PHONE_THANKS, dry_run)
        _transfer_to_customer_service(chat_id, reason="hot_lead_phone", phone=phone, dry_run=dry_run)
        entry["handled"] = True
        entry["handled_reason"] = f"hot_lead_phone:{phone}"
        entry["last_customer_reply"] = ts.isoformat()
        return "phone", True

    if "ملخص" in norm or "summary" in norm:
        _send_message(agent, conv, MSG_SUMMARY, dry_run)
        # أوقف التسلسل الحالي وأعد ضبط العداد من رد العميل الجديد
        _reset_counter(entry, ts)
        return "summary", True

    if re.search(r"احجز", norm):
        _send_message(agent, conv, MSG_BOOKING_STEPS, dry_run)
        _transfer_to_customer_service(chat_id, reason="booking_steps", dry_run=dry_run)
        entry["handled"] = True
        entry["handled_reason"] = "booking_steps"
        entry["last_customer_reply"] = ts.isoformat()
        return "booking", True

    # أي رد آخر: أعد ضبط العداد من رده الجديد (المساعد الأساسي يجاوب عليه)
    _reset_counter(entry, ts)
    return "other_reply", False


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
    actions = {"opt_out": 0, "phone": 0, "summary": 0, "booking": 0, "other_reply": 0, "tagged": 0}

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        msg = f"Failed to connect to DB: {e}"
        log.error(f"[HajjTahseen] {msg}")
        return {"ok": False, "sent_count": 0, "errors": [msg], "message": msg}

    state = _load_state()
    chats = state.setdefault("chats", {})

    try:
        conversations = _get_ad_conversations(cursor)
        log.info(f"[HajjTahseen] Found {len(conversations)} conversations for ad {TARGET_AD_ID}")

        for conv in conversations:
            chat_id = str(conv.get("chat_id") or "").strip()
            if not chat_id:
                continue
            if limit and processed_chats >= limit:
                break

            # ===== لا نتداخل مع موظف بشري أو محادثة مغلقة =====
            try:
                if int(conv.get("needs_help") or 0) == 1:
                    continue
            except Exception:
                pass
            try:
                if int(conv.get("is_closed") or 0) == 1:
                    continue
            except Exception:
                pass
            if _hold_active(conv.get("auto_reply_hold_until"), now):
                continue

            entry = chats.get(chat_id)

            # ===== تحسين الأداء: تخطٍ سريع للمحادثات غير النشطة وغير المتتبعة =====
            # المحادثات غير المتتبعة (بدون سجل حالة) التي تجاوز نشاطها نافذة الـ 24 ساعة
            # لا يمكن مراسلتها إطلاقاً (نافذة Meta مغلقة) ولم نبدأ لها تسلسلاً → نتخطاها
            # من الجذور دون أي استعلام إضافي على الرسائل.
            if entry is None:
                lmt = _parse_dt(conv.get("last_message_time"))
                if lmt is None or (now - lmt).total_seconds() / 3600.0 > WINDOW_HOURS:
                    continue

            last_text, last_ts_raw = _last_customer_message(cursor, chat_id)
            if last_ts_raw is None:
                continue
            last_ts = _parse_dt(last_ts_raw)
            if last_ts is None:
                continue
            first_msgs = _first_customer_messages(cursor, chat_id)

            # ===== محادثة جديدة: تهيئة الحالة ولا نرسل شيئاً الآن =====
            if entry is None:
                entry = _init_entry(first_msgs, last_text, last_ts, now_iso)
                chats[chat_id] = entry
                processed_chats += 1
                if not dry_run:
                    _save_state(state)
                continue

            # ===== حالة نهائية: اكتمل التسلسل أو أُوقف أو حُوّل → لا نعيد =====
            if entry.get("opted_out") or entry.get("handled") or entry.get("sequence_done"):
                processed_chats += 1
                continue

            # ===== كشف رد جديد من العميل أثناء التسلسل =====
            prev_ts = _parse_dt(entry.get("last_customer_reply"))
            if prev_ts is None or last_ts > prev_ts:
                action, sent = _process_new_reply(agent, conv, entry, last_text, last_ts, now, dry_run)
                actions[action] = actions.get(action, 0) + 1
                entry["last_customer_text"] = str(last_text or "")[:200]
                entry["updated_at"] = now_iso
                if sent:
                    sent_count += 1
                processed_chats += 1
                if not dry_run:
                    _save_state(state)
                if sent_count >= MAX_SENDS_PER_RUN:
                    break
                continue

            # ===== لا رد جديد → منطق إرسال المراحل =====
            last_reply_dt = prev_ts or last_ts
            elapsed_h = (now - last_reply_dt).total_seconds() / 3600.0

            # نافذة الـ 24 ساعة انتهت: لا نرسل شيئاً
            if elapsed_h >= WINDOW_HOURS:
                if int(entry.get("highest_stage_sent") or 0) >= 1 and not entry.get("tagged"):
                    # اكتمل التسلسل بدون رد → tag ونتوقف نهائياً
                    _apply_no_response_tag(chat_id, dry_run)
                    entry["tagged"] = True
                    entry["sequence_done"] = True
                    actions["tagged"] = actions.get("tagged", 0) + 1
                elif int(entry.get("highest_stage_sent") or 0) == 0:
                    # لم يبدأ التسلسل أبداً → حذف السجل من الحالة لصغر الملف
                    chats.pop(chat_id, None)
                entry["updated_at"] = now_iso
                processed_chats += 1
                if not dry_run:
                    _save_state(state)
                continue

            # نافذة الإغلاق [22, 24): لا إرسال، ننتظر لنرى هل سيرد العميل
            if elapsed_h >= STAGE3_HOURS_MAX:
                processed_chats += 1
                continue

            target = _target_stage(elapsed_h, bool(entry.get("hot_lead")))
            if target is None:
                processed_chats += 1
                continue
            if int(entry.get("highest_stage_sent") or 0) >= target:
                processed_chats += 1
                continue

            msg = _stage_message(target, bool(entry.get("hot_lead")))
            ok, err = _send_message(agent, conv, msg, dry_run)
            if ok:
                entry["highest_stage_sent"] = target
                entry.setdefault("stages", {})[str(target)] = now_iso
                entry["updated_at"] = now_iso
                sent_count += 1
                processed_chats += 1
                if not dry_run:
                    _save_state(state)  # حفظ فوري بعد كل إرسال (منع التكرار)
                if sent_count >= MAX_SENDS_PER_RUN:
                    break
            else:
                errors.append(f"stage{target}->{chat_id}: {err}")
                processed_chats += 1

        message = (
            f"Ad {TARGET_AD_ID}: sent={sent_count} | processed={processed_chats} "
            f"| actions={actions} | errors={len(errors)}"
        )
        log.info(f"[HajjTahseen] {message}")
        return {
            "ok": len(errors) == 0,
            "sent_count": sent_count,
            "processed_chats": processed_chats,
            "actions": actions,
            "errors": errors[:20],
            "message": message,
        }
    except Exception as e:
        msg = f"Error in Hajj Tahseen follow-up run: {e}"
        log.error(f"[HajjTahseen] {msg}")
        return {"ok": False, "sent_count": sent_count, "errors": [msg], "message": msg}
    finally:
        try:
            if not dry_run:
                _save_state(state)
            conn.close()
        except Exception:
            pass
