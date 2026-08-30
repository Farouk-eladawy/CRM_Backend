"""
Workflow: Religious "برنامج الـ٥ نجوم 👍" Auto-Reply - ديني (Exact Match لحظي)
طلب المدير (2026-08-30): Exact Match 100% على "برنامج الـ٥ نجوم 👍" — Religious + FB/WA فقط.
"""

import os
import json
import re
import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta

from fts_paths import get_data_path

REPLY_5_STARS = (
    "اتفضل حضرتك برنامج حج الـ٥ نجوم يوم بيوم 🕋\n"
    "\n"
    "🕌 المدينة (١ – ٤ ذي الحجة): فندق إعمار رويال — ٣ دقايق من الحرم النبوي، قريب من باب السيدات\n"
    "🚄 يوم ٤: قطار الحرمين لمكة، والشنط بتتنقل عنك\n"
    "🕋 مكة (٤ – ٨ ذي الحجة): فندق الشهداء ٥ نجوم — ٥ دقايق من الحرم، خلف برج الساعة\n"
    "⛺ المناسك (٩ – ١٢): عرفات ومزدلفة ومنى مع طوافة ٥ نجوم\n"
    "🏨 (١٢ – ١٤): رجوع للشهداء وختام مريح\n"
    "\n"
    "✅ صالة كبار الزوار ✅ إشراف ديني وإداري مرافق \n"
    "\n"
    "💰 ٤٩٠ ألف جنيه للفرد (سعر الموسم اللي فات، والنهائي بعد ضوابط الوزارة) + تذكرة الطيران بسعرها وقت الحجز\n"
    "\n"
    "اسهل حاجه اكلم حضرتك دقيقتين وهجاوبك على أي سؤال — ابعتلي رقم الموبايل ومناسب اكلم حضرتك امتي ؟ 📱"
)

KEYWORDS = [
    {
        "keyword": "برنامج الـ٥ نجوم 👍",
        "reply": REPLY_5_STARS,
        "enabled": True,
    },
]

STATE_FILE = get_data_path("religious_5_stars_program_autoreply_state.json")
DEDUP_DB = get_data_path("religious_5_stars_program_autoreply_dedup.db")
MAX_STATE_RECORDS = 2000
DEDUP_WINDOW_SECONDS = 600
DEDUP_TABLE = "religious_5_stars_program_reply_dedup"
CANCEL_REASON = "religious_5_stars_program_autoreply"

log = logging.getLogger("Religious5StarsProgramAutoReply")


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
    if external_id:
        return f"ext:{external_id}"
    return f"{chat_id}:{str(message_body or '')[:60]}"


def _normalize_body_for_dedup(message_body: str) -> str:
    try:
        s = str(message_body or "").strip().lower()
        s = re.sub(r"[\u0610-\u061A\u0640\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)
        s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
        s = re.sub(r"\s+", " ", s, flags=re.UNICODE)
        return s.strip()
    except Exception:
        return str(message_body or "").strip()


def _ensure_dedup_table():
    try:
        with sqlite3.connect(DEDUP_DB, timeout=30.0) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {DEDUP_TABLE} (
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
            try:
                cutoff = (datetime.utcnow() - timedelta(seconds=DEDUP_WINDOW_SECONDS)).isoformat()
                cur.execute(f"DELETE FROM {DEDUP_TABLE} WHERE replied_at < ?", (cutoff,))
            except Exception:
                pass
            cur.execute(
                f"INSERT OR IGNORE INTO {DEDUP_TABLE} (dedup_key, chat_id, replied_at, keyword) VALUES (?, ?, ?, ?)",
                (unified_key, str(chat_id or ""), now, str(keyword or "")),
            )
            conn.commit()
            claimed = cur.rowcount > 0
        return claimed
    except Exception as e:
        log.error(f"Failed to claim dedup: {e}")
        return _legacy_claim(chat_id, external_id, message_body)


def _legacy_claim(chat_id: str, external_id: str, message_body: str) -> bool:
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


def _normalize_for_match(text: str) -> str:
    try:
        s = str(text or "").strip().lower()
        s = re.sub(r"[\u0610-\u061A\u0640\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)
        s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
        s = re.sub(r"\s+", " ", s, flags=re.UNICODE)
        return s.strip()
    except Exception:
        return str(text or "").strip().lower()


def _match_keyword(message_body: str):
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
        if normalized_message == normalized_keyword:
            return entry
    return None


def _is_non_text_media(message_body: str) -> bool:
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
    try:
        import chat_db
        conv = chat_db.get_conversation(chat_id) or {}
        hold_raw = str(conv.get("auto_reply_hold_until") or "").strip()
        if not hold_raw:
            return False
        try:
            now = datetime.fromisoformat(chat_db.get_cairo_time())
            if now.tzinfo is not None:
                now = now.replace(tzinfo=None)
            hold_dt = datetime.fromisoformat(hold_raw)
            if hold_dt.tzinfo is not None:
                hold_dt = hold_dt.replace(tzinfo=None)
            if hold_dt > now:
                return True
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


def run(agent, payload: dict = None) -> dict:
    payload = payload or {}
    chat_id = str(payload.get("chat_id") or "").strip()
    message_body = str(payload.get("message_body") or "").strip()
    source = str(payload.get("source") or "").strip()
    sender_identifier = str(payload.get("sender_identifier") or "").strip()
    location = str(payload.get("location") or "").strip()
    receiving_phone_id = str(payload.get("receiving_phone_id") or "").strip() or None
    incoming_external_message_id = str(payload.get("incoming_external_message_id") or "").strip()

    if location.lower() != "religious":
        return {"ok": True, "skipped": "not_religious", "chat_id": chat_id}

    if source.lower() not in ("facebook", "whatsapp"):
        return {"ok": True, "skipped": "unsupported_source", "chat_id": chat_id}

    if not chat_id or not message_body or not sender_identifier:
        return {"ok": True, "skipped": "missing_data", "chat_id": chat_id}

    if _is_non_text_media(message_body):
        return {"ok": True, "skipped": "non_text_media", "chat_id": chat_id}

    if _is_chat_on_hold(chat_id):
        return {"ok": True, "skipped": "human_hold", "chat_id": chat_id}

    if _is_human_active(chat_id):
        return {"ok": True, "skipped": "human_active", "chat_id": chat_id}

    matched = _match_keyword(message_body)
    if not matched:
        return {"ok": True, "skipped": "no_keyword_match", "chat_id": chat_id}

    answer = str(matched.get("reply") or "").strip()
    if not answer:
        return {"ok": True, "skipped": "empty_reply", "chat_id": chat_id}

    claimed = _claim_reply(chat_id, incoming_external_message_id, message_body, matched.get("keyword"))
    if not claimed:
        return {"ok": True, "skipped": "already_processed", "chat_id": chat_id}

    channel, ok, error = _send_one(
        agent, answer, source, sender_identifier, location,
        receiving_phone_id, chat_id,
    )

    if not ok:
        log.warning(f"Send failed for chat {chat_id}: {error}")
        return {
            "ok": False,
            "skipped": "send_failed",
            "chat_id": chat_id,
            "keyword": matched.get("keyword"),
            "error": str(error)[:500],
        }

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
        try:
            chat_db.delete_proposed_drafts(chat_id)
        except Exception:
            pass
        try:
            if agent and hasattr(agent, "cancel_whatsapp_ai_processing"):
                agent.cancel_whatsapp_ai_processing(
                    chat_id=chat_id,
                    reason=CANCEL_REASON,
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
