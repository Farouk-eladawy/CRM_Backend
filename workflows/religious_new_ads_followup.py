# -*- coding: utf-8 -*-
"""
Workflow: Religious New-Ads Follow-Up - ديني (متابعة الإعلانات الجديدة)
========================================================================
متابعة تلقائية (رسالتان كحد أقصى) للعملاء الواردين من الإعلانات الخمسة الجديدة
(فلترة صارمة من الجذور في SQL + قسم Religious فقط).

الإعلانات كما طلبها المدير (2026-09-11) — مع تصحيح كتابة الـ Ad ID:
    ما طلبه المدير        | الموجود فعلاً في قاعدة البيانات (chat_history.db)
    ----------------------|---------------------------------------------------
    120248849213610757    | 120248849213600757   (5 محادثات)
    120248848846300757    | 120248848846290757   (9 محادثات)
    120248843843230757    | 120248843843220757   (82 محادثة)
    120248833392330757    | 120248833392320757   (37 محادثة)
    120248731132960757    | 120248731132970757   (714 محادثة)
  ملاحظة هندسية: الإعلانات التي زوّدنا بها المدير لا تطابق أي صف في قاعدة
  البيانات (0 محادثة)، وأقرب إعلان لكل منها هو الصف أعلاه (كلها location=
  'Religious'). اعتُمدت أرقام قاعدة البيانات لأنها الحقيقة الفعلية للنظام،
  ويمكن للمدير تعديلها من ملف الإعدادات religious_new_ads_followup_config.json
  بدون تعديل الكود.

شرط التفعيل (فلترة صارمة من الجذور — قاعدة النظام 15):
    WHERE facebook_ad_id IN (5 IDs) AND location = 'Religious'
      AND (is_deleted IS NULL OR is_deleted = 0)

آلية العمل (تُشغَّل مجدولة كل 30 دقيقة عبر محرك الأتمتة):
    1) المرساة = آخر رسالة حقيقية أرسلها العميل (نستبعد رسائل الإحالة
       [Facebook Ad Referral] والسجلات لأنها ليست تفاعلاً حقيقياً).
    2) نطبّق جدول القرارات أدناه (مقاس بالساعات من آخر رسالة للعميل).

جدول القرارات (من مواصفات المدير حرفياً):
    الساعات منذ آخر رسالة من العميل | المتابعات المرسلة | الإجراء
    أقل من 3 ساعات                  | أي عدد            | لا ترسل شيئاً
    3 إلى أقل من 23                 | 0                 | أرسل المتابعة رقم 1
    23 إلى أقل من 23.75             | 0 أو 1            | أرسل المتابعة رقم 2
    من 23.75 إلى أقل من 24          | أي عدد            | لا ترسل (هامش أمان لنافذة Meta)
    24 ساعة أو أكثر                 | أي عدد            | توقف نهائياً (انتهت نافذة Meta)

قواعد صارمة:
    - لا ترسل أكثر من رسالة متابعة واحدة في الدورة الواحدة.
    - لا تكرر رسالة سبق إرسالها أبداً.
    - الحد الأقصى رسالتان لكل محادثة (تُحتسب الرسائل السابقة ضمن الحد).
    - لو العميل رد بأي رسالة جديدة → يُعاد ضبط المرساة من رسالته الأخيرة
      (المساعد الأساسي يرد على استفساره)، مع الحفاظ على الحد الأقصى رسالتين.
    - نصوص الرسائل تُرسل كما هي بالحرف من مواصفات المدير (لا إعادة صياغة).

شروط إيقاف المتابعة فوراً:
    1) العميل أرسل رقم واتساب → إيقاف نهائي + تحويل لموظف خدمة العملاء.
    2) العميل أكمل الحجز أو دفع جدية الحجز → إيقاف نهائي + تحويل لبشري.
    3) العميل عبّر عن عدم الاهتمام/طلب إيقاف الرسائل → إيقاف نهائي.

ملاحظات هندسية (لماذا هذه الشروط):
    - التوقيت: chat_db.get_cairo_time() (توقيت القاهرة UTC+3) — قاعدة النظام F
      (ممنوع datetime.now(timezone.utc)).
    - الحالة: ملف JSON محلي عبر fts_paths.get_data_path — قاعدة النظام G
      (ممنوع agent.load_state/save_state).
    - نافذة Meta: المرحلة 2 تُرسل بين 23 و 23.75 فقط (هامش أمان 15 دقيقة قبل
      إغلاق نافذة الـ 24 ساعة لتجنب خطأ Meta Error #10).
    - الحماية من التداخل البشري: نتخطى المحادثات التي بها needs_help=1 أو
      is_closed=1 أو auto_reply_hold_until في المستقبل.
    - حد أقصى للإرسال في كل تشغيل (MAX_SENDS_PER_RUN) حتى لا يتجاوز التشغيل
      timeout الـ http_request (60 ثانية) — التشغيل التالي يكمل الباقي لأن
      الحالة تُحفظ فور كل إرسال.
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
# ثوابت سير العمل
# =============================================================================
# الإعلانات المستهدفة (المصحّحة لتطابق قاعدة البيانات فعلياً).
# يمكن تجاوزها من ملف الإعدادات religious_new_ads_followup_config.json
DEFAULT_TARGET_AD_IDS = [
    "120248849213600757",
    "120248848846290757",
    "120248843843220757",
    "120248833392320757",
    "120248731132970757",
]

# القسم الديني فقط — فلترة صارمة صفرية (ممنوع أي قسم آخر في هذا الـ workflow)
TARGET_LOCATION = "Religious"

# قاعدة بيانات المحادثات (نفس مسار chat_db)
DB_FILE = get_data_path("chat_history.db")

# ملف الحالة المحلي (قاعدة النظام G: يُمنع agent.load_state/save_state)
STATE_FILE = get_data_path("religious_new_ads_followup_state.json")

# ملف الإعدادات الاختياري (يتيح تعديل الإعلانات/التوقيت بدون تعديل الكود)
CONFIG_FILE = get_data_path("religious_new_ads_followup_config.json")

# عتبات التوقيت بالساعات (مقاسة من آخر رسالة حقيقية للعميل)
HOURS_STAGE1 = 3.0        # المتابعة 1: بعد 3 ساعات
HOURS_STAGE2 = 23.0       # المتابعة 2: بعد 23 ساعة
HOURS_STAGE2_MAX = 23.75  # هامش أمان 15 دقيقة قبل قفل نافذة Meta الـ 24 ساعة
WINDOW_HOURS = 24.0       # نافذة Meta الكاملة: بعدها توقف نهائي

# حد أقصى للإرسال في كل تشغيل (حتى لا يتجاوز timeout الـ http_request)
MAX_SENDS_PER_RUN = 20

# الـ tags المستخدمة عند التحويل للبشر
TAG_HOT_LEAD = "new-ads-hot-lead"
TAG_NO_RESPONSE = "no-response-new-ads"

log = logging.getLogger("ReligiousNewAdsFollowup")


# =============================================================================
# تحميل الإعدادات (اختياري) — يسمح بتصحيح الـ Ad IDs من ملف JSON
# =============================================================================
def _load_config() -> dict:
    cfg = {}
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f) or {}
    except Exception as e:
        log.error(f"Failed to load config: {e}")
    return cfg if isinstance(cfg, dict) else {}


_CFG = _load_config()


def _cfg_ad_ids():
    ids = _CFG.get("ad_ids")
    if isinstance(ids, list) and ids:
        out = [str(x).strip() for x in ids if str(x).strip()]
        if out:
            return out
    return list(DEFAULT_TARGET_AD_IDS)


def _cfg_float(key, default):
    try:
        v = _CFG.get(key)
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


TARGET_AD_IDS = _cfg_ad_ids()
STAGE1_HOURS = _cfg_float("stage1_hours", HOURS_STAGE1)
STAGE2_HOURS = _cfg_float("stage2_hours", HOURS_STAGE2)
STAGE2_SAFE_MAX = min(_cfg_float("stage2_safe_max_hours", HOURS_STAGE2_MAX), WINDOW_HOURS)


# =============================================================================
# نصوص الرسائل (كما هي بالحرف — من مواصفات المدير، لا تغيير ولا إعادة صياغة)
# =============================================================================
MSG_FOLLOWUP_1 = (
    "عادي جدًا تاخد وقتك في قرار زي ده.\n"
    "بس قولي: إيه اللي محتاج تعرفه أكتر قبل ما تقرر؟\n"
    "السعر ، البرنامج نفسه، ولا حاجة تانية؟\n"
    "اكتبلي وأنا أرد عليك فورًا او ابعتلي رقم تليفون حضرتك وهكلمك اجاوبك علي اي استفسار عندك ونوصل لقرار بأذن الله"
)

MSG_FOLLOWUP_2 = (
    "آخر رسالة مني قبل ما الخصم يقفل.\n"
    "\n"
    "الخصم بينتهي يوم الخميس ١٧ سبتمبر، ونتيجة القرعة يوم ٣٠ سبتمبر. بعد كده مافيش تقديم للحج السنة دي.\n"
    "\n"
    "واللي بيقدم معانا في قرعة الحج بياخد:\n"
    "\n"
    "فرصة في سحب على ٣ رحلات عمرة مجانية.\n"
    "فرصة في سحب على تذكرة طيران وتذكرة عبّارة، والسحب في بث مباشر على صفحتنا.\n"
    "ولو طلعت احتياطي ١ أو ٢ أو ٣، لسه ليك فرصة تصعيد.\n"
    "ومفاجآت تانية مستنية حجاجنا.\n"
    "\n"
    "جدية الحجز بتتخصم من اجمالي سعر البرنامج عند الفوز - وفي حاله عدم الفوز لا قدر الله بيسترد المبلغ بالكامل علي بنك مصر\n"
    "\n"
    "ابعتلي رقم موبايلك وهنكلمك ونخلص التقديم معاك في دقايق."
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
            return {"chats": data if isinstance(data, dict) else {}}
    except Exception as e:
        log.error(f"Failed to load state: {e}")
    return {"chats": {}}


# قفل ثابت عبر إعادة تحميل الموديول (run_script يعيد exec_module في كل تشغيل)
if not hasattr(sys, "_religious_new_ads_followup_state_lock"):
    sys._religious_new_ads_followup_state_lock = threading.Lock()
_STATE_LOCK = sys._religious_new_ads_followup_state_lock


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
    """تطبيع النص للمطابقة فقط (وليس للتغيير في الرسائل)."""
    s = str(text or "").strip().lower()
    s = re.sub(r"[\u064B-\u065F\u0640]", "", s)
    s = s.translate(_AR_TRANS).translate(_AR_DIGITS).translate(_FA_DIGITS)
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _is_referral_or_media(text: str) -> bool:
    """رسائل النظام/الإحالة/الميديا التي ليست تفاعلاً حقيقياً من العميل."""
    t = str(text or "").strip()
    if not t:
        return True
    if t.startswith("[Facebook Ad Referral]") or t.startswith("[Facebook Referral]"):
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
        "[system log",
        "[system]",
    )
    return any(low.startswith(p) for p in prefixes)


_OPTOUT_PATTERNS = (
    r"متبعتليش", r"متبعتلوش", r"متكلمنيش", r"متكلمناش", r"متزعجنيش",
    r"بلاش تبعت", r"بلاش رسا[يئ]ل", r"مش عايز رسا[يئ]ل", r"مش عايز اتصالات",
    r"مش مهتم", r"اوقفوا", r"اوقفو", r"وقفو", r"لا ترسل", r"لا تبعث",
    r"شيلني", r"انزعني", r"\bstop\b", r"\bunsubscribe\b", r"don'?t contact",
    r"no more messages", r"ممنوع ترسل", r"بطلوا رسا[يئ]ل", r"بطلت رسا[يئ]ل",
    r"شكر[اًا]?.*مش عايز", r"مش عايز منكم", r"مش عايز حاجة", r"مش عايز اي حاجة",
    r"مش عايز حج", r"مش عايز سفر", r"مش عايز عمرة", r"مش عايز حد يكلمني",
)


def _is_optout(text: str) -> bool:
    """كشف طلب العميل إيقاف التواصل نهائياً (لا نرسل له مجدداً أبداً)."""
    norm = _normalize_keyword(text)
    for p in _OPTOUT_PATTERNS:
        if re.search(p, norm):
            return True
    return False


# أنماط إتمام الحجز أو دفع جدية الحجز (إيقاف نهائي)
_BOOKING_DONE_PATTERNS = (
    r"حجزت", r"حجزنا", r"كملت الحجز", r"كمّلنا الحجز", r"تم الحجز",
    r"اتحجز", r"اتأكد الحجز", r"دفعت", r"دفعنا", r"سددت", r"سددنا",
    r"دفع.*جدية", r"جدية الحجز", r"خدت رقم الحجز", r"booked", r"\bpaid\b",
    r"payment done", r"completed the booking",
)


def _is_booking_done(text: str) -> bool:
    """هل أكمل العميل الحجز أو دفع جدية الحجز؟ (إيقاف المتابعة نهائياً)."""
    norm = _normalize_keyword(text)
    for p in _BOOKING_DONE_PATTERNS:
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


# =============================================================================
# استعلامات قاعدة البيانات (فلترة صارمة من الجذور)
# =============================================================================
def _get_ad_conversations(cursor):
    """المحادثات الواردة من الإعلانات الخمسة فقط وفي قسم Religious فقط.
    الفلترة تتم في SQL من الجذور (facebook_ad_id IN (...) AND location='Religious')
    وليس برمجياً — لا نلمس أي إعلان أو قسم آخر (قاعدة النظام 15).
    """
    placeholders = ",".join("?" * len(TARGET_AD_IDS))
    cursor.execute(
        f"""
        SELECT chat_id, sender_identifier, contact_name, source, location,
               receiving_phone_id, last_message_time, needs_help, is_closed,
               auto_reply_hold_until, customer_phone
        FROM conversations
        WHERE facebook_ad_id IN ({placeholders})
          AND location = ?
          AND (is_deleted IS NULL OR is_deleted = 0)
          AND last_message_time IS NOT NULL
        ORDER BY last_message_time ASC
        """,
        (*TARGET_AD_IDS, TARGET_LOCATION),
    )
    rows = cursor.fetchall()
    return [dict(r) for r in rows] if rows else []


def _customer_messages(cursor, chat_id, cap: int = 500):
    """كل رسائل العميل الحقيقية في المحادثة (نص، توقيت) تصاعدياً.
    نستبعد رسائل الإحالة ([Facebook Ad Referral]) والسجلات لأنها ليست تفاعلاً
    حقيقياً من العميل. أما رسائل الميديا (صوت/فيديو/صورة) فهي رد حقيقي.
    """
    cursor.execute(
        """
        SELECT text, timestamp
        FROM messages
        WHERE chat_id = ? AND sender_type = 'customer'
        ORDER BY timestamp ASC
        LIMIT ?
        """,
        (chat_id, cap),
    )
    out = []
    for row in cursor.fetchall():
        text, ts = str(row[0] or ""), row[1]
        if _is_referral_or_media(text):
            continue
        if not text.strip():
            continue
        out.append((text, ts))
    return out


def _hold_active(hold_until, now) -> bool:
    """هل فترة إيقاف الرد الآلي (auto_reply_hold_until) ما زالت سارية؟"""
    if not hold_until:
        return False
    d = _parse_dt(hold_until)
    return bool(d and d > now)


# =============================================================================
# منطق جدول القرارات
# =============================================================================
def _target_stage(elapsed_h: float, highest_sent: int):
    """جدول القرارات — يُعيد رقم المتابعة المستحقة (1/2) أو None.
    القاعدة: لا ترسل أكثر من رسالة واحدة في الدورة الواحدة، ولا تكرر رسالة
    سبق إرسالها، والحد الأقصى رسالتان.
    """
    if elapsed_h < STAGE1_HOURS:
        return None                                     # أقل من 3 ساعات: انتظر
    if elapsed_h < STAGE2_HOURS:
        return 1 if highest_sent < 1 else None          # 3 إلى أقل من 23 و0 مرسل → المتابعة 1
    if elapsed_h < STAGE2_SAFE_MAX:
        return 2 if highest_sent < 2 else None          # 23 → 23.75 و0 أو 1 → المتابعة 2
    return None  # >= 23.75 ساعة: لا نرسل (نافذة الـ 24 ساعة على وشك الإغلاق)


def _stage_message(stage: int) -> str:
    if stage == 1:
        return MSG_FOLLOWUP_1
    if stage == 2:
        return MSG_FOLLOWUP_2
    return ""


# =============================================================================
# الإرسال والتحويل
# =============================================================================
def _send_message(agent, conv: dict, text: str, dry_run: bool = False):
    """إرسال الرسالة عبر القناة الصحيحة (Facebook / WhatsApp) وتسجيلها في السجل."""
    if dry_run:
        return True, None
    source = str(conv.get("source") or "").strip().lower()
    sender_id = str(conv.get("sender_identifier") or "").strip()
    chat_id = str(conv.get("chat_id") or "").strip()
    if not sender_id or not chat_id:
        return False, "missing_sender_or_chat"
    try:
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


def _transfer_to_customer_service(chat_id: str, reason: str, phone: str = None, dry_run: bool = False, tag: str = None):
    """تحويل المحادثة لموظف خدمة العملاء:
    needs_help=1 (يوقف الرد الآلي ويُظهر المحادثة للموظف البشري)
    + تسجيل الـ lead في sales_customer_state.
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
        existing = chat_db.get_sales_state(chat_id) or {}
        tags = str(existing.get("tags") or "")
        use_tag = tag or TAG_HOT_LEAD
        if use_tag not in tags:
            tags = (tags + "," + use_tag) if tags else use_tag
        chat_db.upsert_sales_state(chat_id, {"tags": tags, "lead_status": "new"})
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] New-ads follow-up: transferred to customer service ({reason})",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to transfer {chat_id}: {e}")


def _apply_no_response_tag(chat_id: str, dry_run: bool = False):
    """وضع tag: no-response-new-ads بعد انتهاء نافذة الـ 24 ساعة بدون رد."""
    if dry_run:
        return
    try:
        import chat_db
        existing = chat_db.get_sales_state(chat_id) or {}
        tags = str(existing.get("tags") or "")
        if TAG_NO_RESPONSE not in tags:
            tags = (tags + "," + TAG_NO_RESPONSE) if tags else TAG_NO_RESPONSE
            chat_db.upsert_sales_state(chat_id, {"tags": tags})
    except Exception as e:
        log.error(f"Failed to tag {chat_id}: {e}")


def _init_entry(last_text: str, last_ts: datetime, now_iso: str) -> dict:
    """تهيئة سجل الحالة لمحادثة جديدة."""
    return {
        "last_customer_reply": last_ts.isoformat(),   # المرساة: آخر رسالة من العميل
        "highest_stage_sent": 0,                      # عدد المتابعات المرسلة (0-2)
        "stages": {},
        "last_customer_text": str(last_text or "")[:200],
        "opted_out": False,
        "handled": False,
        "handled_reason": "",
        "sequence_done": False,
        "tagged": False,
        "updated_at": now_iso,
    }


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
    actions = {"stop_optout": 0, "stop_phone": 0, "stop_booking": 0, "reset_reply": 0, "tagged": 0}

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        msg = f"Failed to connect to DB: {e}"
        log.error(f"[NewAds] {msg}")
        return {"ok": False, "sent_count": 0, "errors": [msg], "message": msg}

    state = _load_state()
    chats = state.setdefault("chats", {})

    try:
        conversations = _get_ad_conversations(cursor)
        log.info(f"[NewAds] Found {len(conversations)} conversations for {len(TARGET_AD_IDS)} ads "
                 f"in location '{TARGET_LOCATION}'")

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

            # ===== تخطٍ سريع: محادثة غير متتبعة ونشاطها أقدم من نافذة الـ 24 ساعة =====
            if entry is None:
                lmt = _parse_dt(conv.get("last_message_time"))
                if lmt is None or (now - lmt).total_seconds() / 3600.0 > WINDOW_HOURS:
                    continue

            # ===== حالة نهائية: أُوقفت أو اكتملت → لا نعيد =====
            if entry is not None and (entry.get("opted_out") or entry.get("handled") or entry.get("sequence_done")):
                processed_chats += 1
                continue

            # ===== لقطة رسائل العميل (استعلام واحد لكل محادثة) =====
            cust_msgs = _customer_messages(cursor, chat_id)
            if not cust_msgs:
                continue
            last_customer_text, last_ts_raw = cust_msgs[-1]
            last_customer_ts = _parse_dt(last_ts_raw)
            if last_customer_ts is None:
                continue

            # ===== فحص شروط الإيقاف "في أي وقت خلال المحادثة" =====
            phone_anytime = None
            optout_anytime = None
            booking_anytime = None
            for t, _ts in cust_msgs:
                if phone_anytime is None:
                    phone_anytime = _extract_phone(t)
                if optout_anytime is None:
                    optout_anytime = t if _is_optout(t) else None
                if booking_anytime is None:
                    booking_anytime = t if _is_booking_done(t) else None
                if phone_anytime is not None and optout_anytime is not None and booking_anytime is not None:
                    break

            # ===== محادثة جديدة: تهيئة الحالة ثم فحص شروط الإيقاف فوراً =====
            if entry is None:
                entry = _init_entry(last_customer_text, last_customer_ts, now_iso)
                chats[chat_id] = entry
                processed_chats += 1
                if optout_anytime is not None:
                    entry["handled"] = True
                    entry["handled_reason"] = "optout_anytime"
                    actions["stop_optout"] += 1
                elif phone_anytime is not None:
                    entry["handled"] = True
                    entry["handled_reason"] = f"phone_anytime:{phone_anytime}"
                    _transfer_to_customer_service(chat_id, reason="hot_lead_phone", phone=phone_anytime, dry_run=dry_run)
                    actions["stop_phone"] += 1
                elif booking_anytime is not None:
                    entry["handled"] = True
                    entry["handled_reason"] = "booking_done"
                    _transfer_to_customer_service(chat_id, reason="booking_done", dry_run=dry_run)
                    actions["stop_booking"] += 1
                entry["updated_at"] = now_iso
                if not dry_run:
                    _save_state(state)
                continue

            # ===== كشف رد جديد من العميل أثناء المتابعة =====
            prev_ts = _parse_dt(entry.get("last_customer_reply"))
            if prev_ts is None or last_customer_ts > prev_ts:
                if optout_anytime is not None:
                    entry["handled"] = True
                    entry["handled_reason"] = "optout"
                    actions["stop_optout"] += 1
                elif phone_anytime is not None:
                    entry["handled"] = True
                    entry["handled_reason"] = f"phone:{phone_anytime}"
                    _transfer_to_customer_service(chat_id, reason="hot_lead_phone", phone=phone_anytime, dry_run=dry_run)
                    actions["stop_phone"] += 1
                elif booking_anytime is not None:
                    entry["handled"] = True
                    entry["handled_reason"] = "booking_done"
                    _transfer_to_customer_service(chat_id, reason="booking_done", dry_run=dry_run)
                    actions["stop_booking"] += 1
                else:
                    # العميل رد بأي رسالة → يبدأ حساب الساعات من جديد من رسالته الأخيرة.
                    # تُحتسب المتابعات السابقة ضمن الحد الأقصى (لا نعيد ضبط highest_stage_sent).
                    entry["last_customer_reply"] = last_customer_ts.isoformat()
                    actions["reset_reply"] += 1
                entry["last_customer_text"] = str(last_customer_text or "")[:200]
                entry["updated_at"] = now_iso
                processed_chats += 1
                if not dry_run:
                    _save_state(state)
                if sent_count >= MAX_SENDS_PER_RUN:
                    break
                continue

            # ===== لا رد جديد → منطق جدول القرارات (المرساة = آخر رسالة عميل) =====
            anchor = _parse_dt(entry.get("last_customer_reply")) or last_customer_ts
            elapsed_h = (now - anchor).total_seconds() / 3600.0
            highest = int(entry.get("highest_stage_sent") or 0)

            # نافذة الـ 24 ساعة انتهت: توقف نهائي مهما كانت الظروف
            if elapsed_h >= WINDOW_HOURS:
                if highest >= 1 and not entry.get("tagged"):
                    _apply_no_response_tag(chat_id, dry_run)
                    entry["tagged"] = True
                    entry["sequence_done"] = True
                    actions["tagged"] = actions.get("tagged", 0) + 1
                elif highest == 0:
                    chats.pop(chat_id, None)
                entry["updated_at"] = now_iso
                processed_chats += 1
                if not dry_run:
                    _save_state(state)
                continue

            target = _target_stage(elapsed_h, highest)
            if target is None:
                processed_chats += 1
                continue
            if highest >= target:
                processed_chats += 1
                continue

            msg = _stage_message(target)
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
            f"NewAds({len(TARGET_AD_IDS)}): sent={sent_count} | processed={processed_chats} "
            f"| actions={actions} | errors={len(errors)}"
        )
        log.info(f"[NewAds] {message}")
        return {
            "ok": len(errors) == 0,
            "sent_count": sent_count,
            "processed_chats": processed_chats,
            "actions": actions,
            "errors": errors[:20],
            "message": message,
        }
    except Exception as e:
        msg = f"Error in Religious New-Ads follow-up run: {e}"
        log.error(f"[NewAds] {msg}")
        return {"ok": False, "sent_count": sent_count, "errors": [msg], "message": msg}
    finally:
        try:
            if not dry_run:
                _save_state(state)
            conn.close()
        except Exception:
            pass
