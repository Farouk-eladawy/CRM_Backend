"""
Workflow: External Department - Cancellation Reason Template (القسم الخارجي)
============================================================================
طلب المدير (2026-08-16):
  - بمجرد ما الحجز يِكنسل (Booking Status = Canceled) → يتم إرسال
    Template واتساب ميتا باسم "Cancellation Reason" للعميل.
  - لا توجد فترة زمنية محددة: يعمل على أي حجز ملغي (كل التشغيلات).
  - بدون تكرار الإرسال لنفس العميل/الحجز نهائياً (Dedup دائم Atomic).

النطاق الصارم (قاعدة 8 و11 - لا خلط أقسام):
  - القسم الخارجي فقط = قاعدة Airtable الرئيسية (Main / External)
    base_id = appTp5YgSp9DV2HYc  (جدول List: tblJodXmOWKiYqiXS)
  - يُرفض صراحة أي base_id يخص Religious (appzc9rxT8kfD0HMp) أو Trips
    (apphGHAvy5IhAWVw9) — لا نلمس أي قسم آخر إطلاقاً.

المنطق:
  1) كل تشغيل (Scheduled) يجلب الحجوزات الحالية التي حالة حجزها
     "Canceled / Cancelled / ملغي" من قاعدة الخارجي فقط.
  2) لكل حجز: التحقق من عدم إرسال التمبلت له من قبل (Dedup ذري دائم
     بمفتاح booking_nr + رقم العميل + record_id — بدون انتهاء صلاحية
     لأن طلب المدير "بدون تكرار الإرسال لنفس العميل").
  3) إرسال Template ميتا "Cancellation Reason" عبر الرقم الصحيح
     (Sharm أو Hurghada/Cairo حسب المنتج — رقم واتساب كل منطقة).
  4) لا يوجد Fallback نصي حر إطلاقاً: خارج نافذة الـ 24 ساعة، الرسائل
     الحرة ممنوعة في سياسات ميتا (Error 131-048) — التمبلت المعتمد فقط.
  5) Rate Limiting: تأخير 3 ثوانٍ بين كل رسالة + حد أقصى للسجلات في
     التشغيل الواحد لمنع حظر أرقام واتساب (سياسة ميتا).

ملاحظات هندسية (لماذا):
  - التوقيت: كل التواريخ تُؤخذ من chat_db.get_cairo_time() (قاعدة F)
    وليس datetime.now(timezone.utc).
  - الحالة: ملف JSON محلي + قاعدة SQLite ذرية عبر fts_paths.get_data_path
    (قاعدة G — لا نستخدم agent.load_state/save_state).
  - لا نعدّل أي ملف أساسي (ai_agent.py) ولا ننشئ ملفات .bat.
"""

import os
import re
import json
import sqlite3
import logging
import time

from datetime import datetime

from fts_paths import get_data_path
from offer_send_fts import _clean_str, _clean_phone, _short_name

# =============================================================================
# الثوابت
# =============================================================================
# القاعدة الأساسية الوحيدة المسموح بها: القسم الخارجي (Main / External)
DEFAULT_BASE_ID = "appTp5YgSp9DV2HYc"    # Main / External (الرئيسي / الخارجي)
DEFAULT_TABLE_ID = "tblJodXmOWKiYqiXS"   # جدول List في القاعدة الرئيسية

# قواعد أخرى ممنوعة منعاً باتاً (فلترة صفرية - قاعدة 15)
RELIGIOUS_BASE_ID = "appzc9rxT8kfD0HMp"  # Religious - ممنوع
TRIPS_BASE_ID = "apphGHAvy5IhAWVw9"      # Trips - ممنوع

# التمبلت المطلوب من المدير
DEFAULT_TEMPLATE = "Cancellation Reason"
DEFAULT_TEMPLATE_LANG = "en"

# حدود التشغيل (حماية من حظر ميتا + أداء)
DEFAULT_MAX_RECORDS = 50
SEND_DELAY_SECONDS = 3

# ملفات الحالة (قاعدة G - ملفات محلية فقط)
STATE_FILE = get_data_path("external_cancellation_state.json")
DEDUP_DB = get_data_path("external_cancellation_dedup.db")
LOG_FILE = get_data_path("external_cancellation_log.jsonl")

# منتجات شرم (لتحديد رقم واتساب شرم الصحيح عند الإرسال)
SHARM_PRODUCT_IDS = {"1344400", "1273778", "1195076", "1278027", "1286076", "1366559"}

log = logging.getLogger("ExternalCancellation")


# =============================================================================
# أدوات الحالة المحلية (يمنع استخدام agent.load_state - قاعدة G)
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


def _append_log(entry: dict):
    """سجل تشغيل محلي (JSONL) يوثق كل إرسال/تخطي — توثيق ذاتي (قاعدة 13)."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# =============================================================================
# منع التكرار الذري الدائم (Atomic Dedup - لا ينتهي أبداً)
# =============================================================================
def _ensure_dedup_table():
    try:
        with sqlite3.connect(DEDUP_DB, timeout=30.0) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS external_cancellation_dedup (
                    dedup_key TEXT PRIMARY KEY,
                    record_id TEXT,
                    booking_nr TEXT,
                    phone TEXT,
                    sent_at TEXT NOT NULL,
                    template_name TEXT
                )
                """
            )
            conn.commit()
    except Exception as e:
        log.error(f"Failed to init dedup table: {e}")


def _claim_booking(record_id: str, booking_nr: str, phone: str, template_name: str) -> bool:
    """
    حجز ذري: يمنع إرسال التمبلت لنفس الحجز/العميل أكثر من مرة في كل
    التشغيلات المستقبلية (بدون نافذة زمنية — طلب المدير).
    المفتاح: record_id + booking_nr + رقم العميل.
    """
    _ensure_dedup_table()
    key_bits = [str(record_id or "").strip(), str(booking_nr or "").strip(), str(phone or "").strip()]
    key_bits = [b for b in key_bits if b]
    if not key_bits:
        return False
    dedup_key = "|".join(key_bits)
    try:
        now = _now_cairo_iso()
        with sqlite3.connect(DEDUP_DB, timeout=30.0) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            cur = conn.cursor()
            cur.execute(
                "INSERT OR IGNORE INTO external_cancellation_dedup (dedup_key, record_id, booking_nr, phone, sent_at, template_name) VALUES (?, ?, ?, ?, ?, ?)",
                (dedup_key, str(record_id or ""), str(booking_nr or ""), str(phone or ""), now, str(template_name or "")),
            )
            conn.commit()
            return cur.rowcount > 0
    except Exception as e:
        log.error(f"Failed to claim dedup: {e}")
        # احتياطي: ملف JSON
        state = _load_state()
        processed = state.get("processed", [])
        if dedup_key in processed:
            return False
        processed.append(dedup_key)
        state["processed"] = processed[-5000:]
        _save_state(state)
        return True


def _release_booking(record_id: str, booking_nr: str, phone: str):
    """تحرير الحجز عند فشل الإرسال حتى يُعاد الالتقاط في التشغيل التالي
    (لا نفقد العميل بسبب خطأ مؤقت مثل انقطاع النت أو تمبلت غير مفعّل)."""
    key_bits = [str(record_id or "").strip(), str(booking_nr or "").strip(), str(phone or "").strip()]
    key_bits = [b for b in key_bits if b]
    if not key_bits:
        return
    dedup_key = "|".join(key_bits)
    try:
        with sqlite3.connect(DEDUP_DB, timeout=30.0) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("DELETE FROM external_cancellation_dedup WHERE dedup_key = ?", (dedup_key,))
            conn.commit()
    except Exception as e:
        log.error(f"Failed to release dedup: {e}")
        # احتياطي: إزالة من ملف JSON
        try:
            state = _load_state()
            processed = [k for k in state.get("processed", []) if k != dedup_key]
            state["processed"] = processed
            _save_state(state)
        except Exception:
            pass


def _now_cairo_iso() -> str:
    """التوقيت الرسمي للنظام: القاهرة UTC+3 (قاعدة F — لا utcnow أبداً)."""
    try:
        import chat_db
        now = datetime.fromisoformat(chat_db.get_cairo_time())
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        return now.isoformat()
    except Exception:
        return datetime.now().isoformat()


# =============================================================================
# أدوات قراءة الحقول (نفس نمط cancelled_recovery_fts)
# =============================================================================
def _get_field(agent, fields: dict, field_name: str) -> str:
    try:
        val = agent.get_field_value(fields, field_name)
        if val is not None:
            return val
    except Exception:
        pass
    return fields.get(field_name)


def _is_cancelled_status(value) -> bool:
    s = _clean_str(value).lower()
    if not s:
        return False
    # يغطي: Canceled / Cancelled / Cancel / CXL / ملغي / ملغية
    return ("cancel" in s) or ("ملغ" in s) or s in ("cxl",)


def _booking_phone(fields: dict) -> str:
    for key in ("Customer Phone", "Customer phone", "customer phone", "Phone"):
        val = _clean_phone(fields.get(key))
        if val:
            return val
    return ""


def _booking_nr(fields: dict) -> str:
    for key in ("Booking Nr.", "Booking Nr", "Booking Number", "Booking nr."):
        val = _clean_str(fields.get(key))
        if val:
            return val
    return ""


def _product_id(fields: dict) -> str:
    for key in ("Product ID", "Product Id", "product id"):
        val = _clean_str(fields.get(key))
        if val:
            return val
    return ""


def _wa_location_for_booking(fields: dict, default_location: str) -> str:
    """رقم واتساب المنطقة الصحيح: شرم ← رقم شرم، وإلا الافتراضي (Hurghada/Cairo)."""
    pid = _product_id(fields)
    if pid in SHARM_PRODUCT_IDS:
        return "Sharm"
    return _clean_str(default_location) or "Hurghada/Cairo"


# =============================================================================
# نقطة الدخول الرئيسية
# =============================================================================
def run(agent, payload: dict = None) -> dict:
    """
    Scheduled Workflow — القسم الخارجي فقط.
    payload:
      base_id, table_id, template_name, template_language,
      max_records, dry_run, default_location, template_variables
    """
    payload = payload or {}

    base_id = _clean_str(payload.get("base_id")) or DEFAULT_BASE_ID
    table_id = _clean_str(payload.get("table_id")) or DEFAULT_TABLE_ID
    template_name = _clean_str(payload.get("template_name")) or DEFAULT_TEMPLATE
    template_language = _clean_str(payload.get("template_language")) or DEFAULT_TEMPLATE_LANG
    max_records = max(1, min(int(payload.get("max_records") or DEFAULT_MAX_RECORDS), 200))
    dry_run = bool(payload.get("dry_run", False))
    default_location = _clean_str(payload.get("default_location")) or "Hurghada/Cairo"
    template_variables = payload.get("template_variables")

    # ===== فلترة صفرية صارمة: القسم الخارجي فقط (قاعدة 8 و11 و15) =====
    # ممنوع منعاً باتاً المساس بقاعدة Religious أو Trips
    if base_id in (RELIGIOUS_BASE_ID, TRIPS_BASE_ID):
        return {"ok": False, "error": "forbidden_base_id", "base_id": base_id}

    # ===== جلب جدول القاعدة الخارجية =====
    try:
        api = getattr(agent, "airtable_api", None)
        if api is not None:
            table = api.table(base_id, table_id)
        else:
            table = agent.table
    except Exception as e:
        return {"ok": False, "error": f"resolve_table_failed:{e}"}

    # ===== استعلام دقيق: الحجوزات الملغية فقط (لا نجلب كل الجدول) =====
    formula = (
        "OR("
        "FIND('Cancel', {Booking Status}&''),"
        "FIND('cancel', {Booking Status}&''),"
        "FIND('CANCEL', {Booking Status}&''),"
        "FIND('ملغ', {Booking Status}&'')"
        ")"
    )
    try:
        records = list(table.all(formula=formula, max_records=max_records) or [])
    except Exception as e:
        log.error(f"Fetch cancelled bookings failed: {e}")
        return {"ok": False, "error": f"fetch_failed:{e}"}

    results = []
    sent = 0
    skipped = 0
    for rec in records or []:
        rid = _clean_str((rec or {}).get("id"))
        fields = (rec or {}).get("fields") or {}
        if not rid:
            continue

        booking_nr = _booking_nr(fields)
        phone = _booking_phone(fields)
        status = _clean_str(fields.get("Booking Status"))
        customer_name = _clean_str(_get_field(agent, fields, "Customer Name")) or "Guest"
        short_name = _short_name(customer_name)

        # شروط التخطي
        if not _is_cancelled_status(status):
            results.append({"record_id": rid, "status": "skipped", "message": "not_cancelled", "booking_status": status})
            skipped += 1
            continue
        if not phone:
            results.append({"record_id": rid, "status": "skipped", "message": "missing_phone", "booking_nr": booking_nr})
            skipped += 1
            continue
        if not _claim_booking(rid, booking_nr, phone, template_name):
            results.append({"record_id": rid, "status": "skipped", "message": "already_sent", "booking_nr": booking_nr, "phone": phone})
            skipped += 1
            continue

        wa_location = _wa_location_for_booking(fields, default_location)
        results.append({
            "record_id": rid,
            "status": "dry_run" if dry_run else "success",
            "booking_nr": booking_nr,
            "phone": phone,
            "customer": short_name,
            "template_name": template_name,
            "whatsapp_location": wa_location,
        })
        if dry_run:
            continue

        # ===== إرسال Template ميتا (بدون أي نص حر) =====
        wa_ok = False
        wa_meta = None
        try:
            wa_ok, wa_meta = agent.send_whatsapp_message(
                phone,
                text="",
                location=wa_location,
                template_name=template_name,
                template_language=template_language,
                booking_data=fields,
                template_variables=template_variables,
            )
        except Exception as e:
            wa_ok = False
            wa_meta = {"error": str(e)[:300]}

        if not wa_ok:
            # فشل الإرسال: تحرير الحجز حتى يُعاد في التشغيل التالي
            _release_booking(rid, booking_nr, phone)
            results[-1]["status"] = "error"
            results[-1]["whatsapp_error"] = str(wa_meta or "")[:300]
            log.warning("Cancellation template send failed for %s (%s): %s", booking_nr, phone, wa_meta)
        else:
            sent += 1

        _append_log({
            "ts": _now_cairo_iso(),
            "record_id": rid,
            "booking_nr": booking_nr,
            "phone": phone,
            "customer": short_name,
            "template_name": template_name,
            "template_language": template_language,
            "whatsapp_location": wa_location,
            "wa_ok": bool(wa_ok),
            "wa_meta": wa_meta if isinstance(wa_meta, dict) else None,
        })

        # Rate Limiting: تأخير بين الرسائل (سياسة ميتا - قاعدة 8-8)
        time.sleep(SEND_DELAY_SECONDS)

    return {
        "ok": True,
        "scope": "external_only",
        "base_id": base_id,
        "table_id": table_id,
        "records_fetched": len(records),
        "sent": sent,
        "skipped": skipped,
        "template_name": template_name,
        "dry_run": dry_run,
        "results": results,
    }
