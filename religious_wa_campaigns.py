# -*- coding: utf-8 -*-
"""Religious WhatsApp outbound campaigns (Religious number only)."""

import json
import logging
import re
import sqlite3
import threading
import time
import uuid
from datetime import datetime

from fts_paths import get_data_path

log = logging.getLogger("religious_wa_campaigns")

RELIGIOUS_LOCATION = "Religious"
RELIGIOUS_PHONE_ID = "1214164541774422"
RELIGIOUS_DISPLAY = "+201094728015"
DB_FILE = get_data_path("religious_wa_campaigns.db")

_OMRA_BODY = (
    "السلام عليكم ورحمة الله وبركاته 🌙\n\n"
    "بشرى سارة لحضرتك من شركة FTS للسياحة 🎁\n\n"
    "ضوابط الحج السياحي خلاص قربت تصدر خلال أيام إن شاء الله ⏳ وأول ما تنزل هنتواصل مع حضرتك فوراً بكل التفاصيل.\n\n"
    "ولحد ما الضوابط تنزل، اعرف إن حضرتك *كده كده كسبان معانا* 🏆 لأن بمجرد تقديمك، اسم حضرتك دخل تلقائياً:\n"
    "✨ السحب العلني على *٣ رحلات عمرة مجانية*\n\n"
    "والسحب هيتم في *بث مباشر على صفحتنا الرسمية* – قدام الجميع، بالأسماء، وعلى الهواء مباشرة 🔴 مفيش أي خطوة إضافية مطلوبة من حضرتك ✅\n\n"
    "وإن شاء الله ربنا يكرمك ونبشرك قريباً بالفوز في قرعة الحج وتكون من ضيوف الرحمن 🕋🤲\n\n"
    "شركة FTS للسياحة – ترخيص وزارة السياحة فئة (أ) رقم ٢٠٨٩"
)
KNOWN_TEMPLATES = {
    "3omra": {
        "body": _OMRA_BODY,
        "header_image": "https://res.cloudinary.com/dqlurfwet/image/upload/v1787426756/whatsapp_templates/3omra_header.png",
        "buttons": ["معاكم بأذن الله"],
    }
}


def format_wa_template_chat_message(template_name, body="", header_image="", buttons=None):
    name = str(template_name or "").strip()
    known = KNOWN_TEMPLATES.get(name.lower()) or {}
    payload = {
        "name": name,
        "body": str(body or known.get("body") or "").strip(),
        "header_image": str(header_image or known.get("header_image") or "").strip(),
        "buttons": list(buttons or known.get("buttons") or []),
    }
    return "[WA_TEMPLATE]" + json.dumps(payload, ensure_ascii=False)


_SEND_LOCK = threading.Lock()
_RUNNING = set()


def _clean_phone(v) -> str:
    c = "".join(ch for ch in str(v or "") if ch.isdigit())
    if not c:
        return ""
    if c.startswith("00"):
        c = c[2:]
    if c.startswith("0") and len(c) == 11:
        c = "20" + c[1:]
    elif c.startswith("1") and len(c) == 10:
        c = "20" + c
    return c


def parse_phone_list(raw) -> list:
    if isinstance(raw, list):
        parts = raw
    else:
        parts = re.split(r"[\s,;]+", str(raw or ""))
    seen = set()
    out = []
    for p in parts:
        c = _clean_phone(p)
        if not c or len(c) < 10 or c in seen:
            continue
        seen.add(c)
        out.append(c)
    return out


def _connect():
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS campaigns (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            send_type TEXT NOT NULL,
            template_name TEXT,
            template_language TEXT,
            template_header_media_url TEXT,
            template_header_media_type TEXT,
            template_variables_json TEXT,
            text_body TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT,
            started_at TEXT,
            finished_at TEXT,
            created_by_user_id TEXT,
            created_by_name TEXT,
            receiving_phone_id TEXT,
            location TEXT,
            delay_sec REAL,
            error TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS recipients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id TEXT NOT NULL,
            phone TEXT NOT NULL,
            chat_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            claimed_at TEXT,
            sent_at TEXT,
            error TEXT,
            UNIQUE(campaign_id, phone)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rwc_recipients_campaign ON recipients(campaign_id, status)")
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(campaigns)").fetchall()]
    except Exception:
        cols = []
    if "company_id" not in cols:
        try:
            conn.execute("ALTER TABLE campaigns ADD COLUMN company_id TEXT DEFAULT 'fts'")
            conn.execute("UPDATE campaigns SET company_id = 'fts' WHERE company_id IS NULL OR TRIM(company_id) = ''")
        except Exception:
            pass
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rwc_campaigns_company ON campaigns(company_id)")
    return conn


def _now():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _row_campaign(row):
    if not row:
        return None
    d = dict(row)
    vars_raw = d.get("template_variables_json") or ""
    variables = []
    if vars_raw:
        try:
            parsed = json.loads(vars_raw)
            if isinstance(parsed, list):
                variables = [str(x) for x in parsed]
        except Exception:
            variables = []
    d["template_variables"] = variables
    d.pop("template_variables_json", None)
    return d


def _truncate(text: str, limit: int = 1500) -> str:
    s = str(text or "").strip()
    if len(s) <= limit:
        return s
    return s[: max(0, limit - 1)] + "…"


def _extract_meta_error_parts(meta) -> dict:
    """Normalize Meta / send failure payloads into structured fields for Note."""
    out = {
        "message_id": "",
        "recipient": "",
        "code": "",
        "title": "",
        "message": "",
        "details": "",
        "status_code": "",
        "raw": "",
    }
    if meta is None:
        return out
    if not isinstance(meta, dict):
        out["raw"] = str(meta)
        out["message"] = str(meta)
        return out

    out["status_code"] = str(meta.get("status_code") or "").strip()
    body = meta.get("body")
    parsed = meta.get("json") if isinstance(meta.get("json"), dict) else None
    if parsed is None and isinstance(body, str) and body.strip().startswith("{"):
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = None
    err = {}
    if isinstance(parsed, dict):
        err = parsed.get("error") if isinstance(parsed.get("error"), dict) else {}
        # Some payloads nest under messages / error_data
        if not err and isinstance(parsed.get("error"), str):
            out["message"] = str(parsed.get("error"))
    if isinstance(meta.get("error"), dict):
        err = meta.get("error") or err

    if isinstance(err, dict) and err:
        out["code"] = str(err.get("code") or "").strip()
        out["title"] = str(err.get("error_user_title") or err.get("type") or err.get("title") or "").strip()
        out["message"] = str(err.get("message") or err.get("error_user_msg") or "").strip()
        details = err.get("error_data") if isinstance(err.get("error_data"), dict) else {}
        if details:
            out["details"] = str(details.get("details") or details.get("message") or "").strip()
        if not out["details"]:
            out["details"] = str(err.get("error_data") or "").strip() if not isinstance(err.get("error_data"), dict) else ""
        fbtrace = str(err.get("fbtrace_id") or "").strip()
        if fbtrace and not out["details"]:
            out["details"] = f"fbtrace_id={fbtrace}"

    # message id from successful structure shouldn't appear on failure, but keep if present
    try:
        msgs = (parsed or {}).get("messages") if isinstance(parsed, dict) else None
        if isinstance(msgs, list) and msgs:
            out["message_id"] = str((msgs[0] or {}).get("id") or "").strip()
    except Exception:
        pass

    if not out["message"] and isinstance(body, str) and body.strip():
        out["raw"] = body.strip()
        out["message"] = body.strip()[:500]
    if not out["message"] and meta.get("error"):
        out["message"] = str(meta.get("error"))
    return out


def _format_send_error(meta, phone: str = None) -> str:
    parts = _extract_meta_error_parts(meta)
    if phone and not parts.get("recipient"):
        parts["recipient"] = str(phone)
    chunks = []
    if parts.get("message_id"):
        chunks.append(f"message_id={parts['message_id']}")
    if parts.get("recipient"):
        chunks.append(f"recipient={parts['recipient']}")
    if parts.get("code"):
        chunks.append(f"code={parts['code']}")
    if parts.get("title"):
        chunks.append(f"title={parts['title']}")
    if parts.get("message"):
        chunks.append(f"message={parts['message']}")
    if parts.get("details"):
        chunks.append(f"details={parts['details']}")
    if parts.get("status_code") and not parts.get("code"):
        chunks.append(f"http={parts['status_code']}")
    if not chunks and parts.get("raw"):
        chunks.append(parts["raw"])
    if not chunks:
        chunks.append("Send failed (unknown error)")
    text = " | ".join(chunks)
    # Friendly Arabic/English prefix for billing / payment Meta issues
    joined = text.lower()
    if any(
        x in joined
        for x in (
            "payment",
            "billing",
            "invoice",
            "business eligibility",
            "131042",
            "account has been restricted",
            "unpaid",
            "فاتورة",
            "دفع",
        )
    ):
        text = "Meta billing/payment issue — " + text
    return _truncate(text, 1500)


def _is_campaign_blocking_failure(err_txt: str, meta=None) -> bool:
    """
    Stop the whole campaign after a failed send.
    Account/billing issues always block; user requested auto-stop on any send failure
    so operators can fix Meta/config before continuing.
    """
    return True


def campaign_counts(campaign_id: str) -> dict:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM recipients WHERE campaign_id = ? GROUP BY status",
            (campaign_id,),
        ).fetchall()
    out = {
        "total": 0,
        "pending": 0,
        "sending": 0,
        "sent": 0,
        "failed": 0,
        "skipped": 0,
    }
    for r in rows:
        st = str(r["status"] or "")
        n = int(r["n"] or 0)
        out["total"] += n
        if st in out:
            out[st] = n
    return out


def list_campaigns(company_id=None):
    cid = str(company_id or "fts").strip() or "fts"
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM campaigns
            WHERE COALESCE(NULLIF(company_id, ''), 'fts') = ?
            ORDER BY created_at DESC LIMIT 200
            """,
            (cid,),
        ).fetchall()
    items = []
    for row in rows:
        item = _row_campaign(row)
        item["counts"] = campaign_counts(item["id"])
        items.append(item)
    return items


def get_campaign(campaign_id: str):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if not row:
        return None
    item = _row_campaign(row)
    item["counts"] = campaign_counts(campaign_id)
    return item


def create_campaign(payload: dict) -> dict:
    phones = parse_phone_list(payload.get("phones") or payload.get("phone_list") or "")
    send_type = str(payload.get("send_type") or "").strip().lower()
    if send_type not in ("template", "text"):
        raise ValueError("send_type must be template or text")
    name = str(payload.get("name") or "").strip() or ("حملة " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    template_name = str(payload.get("template_name") or "").strip()
    template_language = str(payload.get("template_language") or "en").strip() or "en"
    text_body = str(payload.get("text_body") or payload.get("text") or "").strip()
    if send_type == "template" and not template_name:
        raise ValueError("template_name is required")
    if send_type == "text" and not text_body:
        raise ValueError("text_body is required")
    if not phones:
        raise ValueError("no valid phone numbers")

    variables = payload.get("template_variables") or []
    if not isinstance(variables, list):
        variables = []
    delay_sec = float(payload.get("delay_sec") or 2.5)
    if delay_sec < 1.5:
        delay_sec = 1.5
    if delay_sec > 8:
        delay_sec = 8

    cid = str(uuid.uuid4())
    now = _now()
    company_id = str(payload.get("company_id") or "fts").strip() or "fts"
    phone_id = str(payload.get("receiving_phone_id") or "").strip() or RELIGIOUS_PHONE_ID
    location = str(payload.get("location") or RELIGIOUS_LOCATION).strip() or RELIGIOUS_LOCATION
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO campaigns (
                id, name, send_type, template_name, template_language,
                template_header_media_url, template_header_media_type, template_variables_json,
                text_body, status, created_at, created_by_user_id, created_by_name,
                receiving_phone_id, location, delay_sec, company_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cid,
                name,
                send_type,
                template_name,
                template_language,
                str(payload.get("template_header_media_url") or "").strip(),
                str(payload.get("template_header_media_type") or "image").strip() or "image",
                json.dumps([str(x) for x in variables], ensure_ascii=False),
                text_body,
                now,
                str(payload.get("created_by_user_id") or "").strip(),
                str(payload.get("created_by_name") or "").strip(),
                phone_id,
                location,
                delay_sec,
                company_id,
            ),
        )
        conn.executemany(
            "INSERT OR IGNORE INTO recipients (campaign_id, phone, status) VALUES (?, ?, 'pending')",
            [(cid, p) for p in phones],
        )
        conn.commit()
    return get_campaign(cid)


def _inbound_by_phones(phones: list) -> dict:
    if not phones:
        return {}
    import chat_db

    placeholders = ",".join("?" for _ in phones)
    sql = f"""
        SELECT
            REPLACE(REPLACE(REPLACE(IFNULL(c.sender_identifier, ''), '+', ''), ' ', ''), '-', '') AS phone,
            MAX(m.timestamp) AS last_inbound_at,
            (
                SELECT m2.text FROM messages m2
                WHERE m2.chat_id = c.chat_id
                  AND m2.sender_type = 'customer'
                  AND IFNULL(m2.text, '') NOT LIKE '[Facebook%'
                ORDER BY m2.timestamp DESC
                LIMIT 1
            ) AS last_inbound_text
        FROM conversations c
        JOIN messages m ON m.chat_id = c.chat_id
        WHERE lower(IFNULL(c.source, '')) = 'whatsapp'
          AND m.sender_type = 'customer'
          AND (
                IFNULL(c.receiving_phone_id, '') = ?
             OR IFNULL(c.location, '') = ?
          )
          AND REPLACE(REPLACE(REPLACE(IFNULL(c.sender_identifier, ''), '+', ''), ' ', ''), '-', '') IN ({placeholders})
        GROUP BY c.chat_id
    """
    out = {}
    try:
        with sqlite3.connect(chat_db.DB_FILE, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 30000;")
            rows = conn.execute(sql, [RELIGIOUS_PHONE_ID, RELIGIOUS_LOCATION, *phones]).fetchall()
        for row in rows:
            phone = _clean_phone(row["phone"] if row else "")
            if not phone:
                continue
            prev = out.get(phone) or {}
            last_at = str(row["last_inbound_at"] or "")
            if last_at >= str(prev.get("last_inbound_at") or ""):
                txt = str(row["last_inbound_text"] or "").strip()
                if txt.startswith("[PROPOSED_DRAFT]"):
                    continue
                out[phone] = {
                    "customer_replied": True,
                    "last_inbound_at": last_at,
                    "last_inbound_preview": txt[:180],
                }
    except Exception as e:
        log.warning("inbound lookup failed: %s", e)
    return out


def list_recipients(campaign_id: str) -> list:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM recipients WHERE campaign_id = ? ORDER BY id ASC",
            (campaign_id,),
        ).fetchall()
    items = [dict(r) for r in rows]
    phones = [str(r.get("phone") or "") for r in items]
    inbound = _inbound_by_phones(phones)
    for item in items:
        extra = inbound.get(item.get("phone")) or {
            "customer_replied": False,
            "last_inbound_at": None,
            "last_inbound_preview": "",
        }
        item.update(extra)
    return items


def _ensure_conversation(phone: str):
    import chat_db

    conv = None
    try:
        with sqlite3.connect(chat_db.DB_FILE, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 30000;")
            row = conn.execute(
                """
                SELECT * FROM conversations
                WHERE lower(source) = 'whatsapp'
                  AND REPLACE(REPLACE(REPLACE(IFNULL(sender_identifier, ''), '+', ''), ' ', ''), '-', '') = ?
                  AND (
                        IFNULL(receiving_phone_id, '') = ?
                     OR IFNULL(location, '') = ?
                  )
                ORDER BY last_message_time DESC
                LIMIT 1
                """,
                (phone, RELIGIOUS_PHONE_ID, RELIGIOUS_LOCATION),
            ).fetchone()
            conv = dict(row) if row else None
    except Exception:
        conv = None
    if not conv:
        conv = chat_db.get_or_create_conversation(
            source="WhatsApp",
            sender_identifier=phone,
            contact_name=phone,
            location=RELIGIOUS_LOCATION,
            thread_id="",
            receiving_phone_id=RELIGIOUS_PHONE_ID,
        ) or {}
    chat_id = str(conv.get("chat_id") or "").strip()
    if not chat_id:
        return None
    try:
        with sqlite3.connect(chat_db.DB_FILE, timeout=30.0) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute(
                """
                UPDATE conversations
                SET receiving_phone_id = COALESCE(NULLIF(receiving_phone_id, ''), ?),
                    location = COALESCE(NULLIF(location, ''), ?)
                WHERE chat_id = ?
                """,
                (RELIGIOUS_PHONE_ID, RELIGIOUS_LOCATION, chat_id),
            )
            conn.commit()
    except Exception as e:
        log.warning("conversation tag skipped for %s: %s", phone, e)
    return chat_id


def _claim(campaign_id: str, phone: str) -> bool:
    now = _now()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE recipients
            SET status = 'sending', claimed_at = ?, error = NULL
            WHERE campaign_id = ? AND phone = ? AND status IN ('pending', 'failed')
            """,
            (now, campaign_id, phone),
        )
        conn.commit()
        return cur.rowcount > 0


def _mark(campaign_id: str, phone: str, status: str, error: str = None, chat_id: str = None):
    now = _now()
    with _connect() as conn:
        if status == "sent":
            conn.execute(
                """
                UPDATE recipients
                SET status = 'sent', sent_at = ?, error = NULL, chat_id = COALESCE(?, chat_id)
                WHERE campaign_id = ? AND phone = ?
                """,
                (now, chat_id, campaign_id, phone),
            )
        else:
            conn.execute(
                """
                UPDATE recipients
                SET status = ?, error = ?, chat_id = COALESCE(?, chat_id)
                WHERE campaign_id = ? AND phone = ?
                """,
                (status, _truncate(error or "", 1500), chat_id, campaign_id, phone),
            )
        conn.commit()


def _set_campaign_status(campaign_id: str, status: str, error: str = None):
    now = _now()
    with _connect() as conn:
        if status == "sending":
            conn.execute(
                "UPDATE campaigns SET status = ?, started_at = COALESCE(started_at, ?), error = NULL WHERE id = ?",
                (status, now, campaign_id),
            )
        elif status in ("completed", "cancelled"):
            if error is None:
                # Preserve an existing auto-stop reason (do not wipe Note/error).
                conn.execute(
                    "UPDATE campaigns SET status = ?, finished_at = COALESCE(finished_at, ?) WHERE id = ?",
                    (status, now, campaign_id),
                )
            else:
                conn.execute(
                    "UPDATE campaigns SET status = ?, finished_at = ?, error = ? WHERE id = ?",
                    (status, now, _truncate(error, 1500), campaign_id),
                )
        else:
            conn.execute(
                "UPDATE campaigns SET status = ?, error = ? WHERE id = ?",
                (status, _truncate(error or "", 1500) if error else None, campaign_id),
            )
        conn.commit()


def _auto_stop_campaign(campaign_id: str, reason: str):
    """Stop sending immediately and keep pending numbers for later resume."""
    with _SEND_LOCK:
        _RUNNING.discard(campaign_id)
    _set_campaign_status(campaign_id, "cancelled", reason)
    with _connect() as conn:
        conn.execute(
            "UPDATE recipients SET status = 'pending', error = NULL WHERE campaign_id = ? AND status = 'sending'",
            (campaign_id,),
        )
        conn.commit()
    log.warning("Campaign %s auto-stopped: %s", campaign_id, _truncate(reason, 300))


def _is_campaign_running(campaign_id: str) -> bool:
    with _SEND_LOCK:
        return campaign_id in _RUNNING


def _send_loop(agent, campaign_id: str):
    stopped_early = False
    try:
        camp = get_campaign(campaign_id)
        if not camp:
            return
        delay_sec = float(camp.get("delay_sec") or 2.5)
        send_type = str(camp.get("send_type") or "")
        with _connect() as conn:
            phones = [
                str(r["phone"])
                for r in conn.execute(
                    "SELECT phone FROM recipients WHERE campaign_id = ? AND status IN ('pending', 'failed') ORDER BY id ASC",
                    (campaign_id,),
                ).fetchall()
            ]
        sent_n = 0
        for idx, phone in enumerate(phones):
            if not _is_campaign_running(campaign_id):
                stopped_early = True
                break
            live = get_campaign(campaign_id) or {}
            if str(live.get("status") or "") == "cancelled":
                stopped_early = True
                break
            if not _claim(campaign_id, phone):
                continue
            chat_id = None
            try:
                chat_id = _ensure_conversation(phone)
            except Exception as e:
                err_txt = _format_send_error(str(e), phone=phone)
                _mark(campaign_id, phone, "failed", err_txt)
                if _is_campaign_blocking_failure(err_txt):
                    _auto_stop_campaign(
                        campaign_id,
                        f"Auto-stopped: conversation setup failed for {phone} — {err_txt}",
                    )
                    stopped_early = True
                    break
                continue

            ok = False
            meta = None
            err_txt = ""
            try:
                if send_type == "template":
                    ok, meta = agent.send_whatsapp_message(
                        phone,
                        text="",
                        location=RELIGIOUS_LOCATION,
                        template_name=camp.get("template_name"),
                        template_language=camp.get("template_language") or "en",
                        receiving_phone_id=RELIGIOUS_PHONE_ID,
                        template_header_media_url=camp.get("template_header_media_url") or None,
                        template_header_media_type=camp.get("template_header_media_type") or "image",
                        template_variables=camp.get("template_variables") or None,
                        _template_phone_fallback=False,
                    )
                else:
                    ok, meta = agent.send_whatsapp_message(
                        phone,
                        text=camp.get("text_body") or "",
                        location=RELIGIOUS_LOCATION,
                        receiving_phone_id=RELIGIOUS_PHONE_ID,
                        _template_phone_fallback=False,
                    )
            except Exception as e:
                ok = False
                meta = str(e)

            uncertain = bool(isinstance(meta, dict) and meta.get("uncertain"))
            if ok or uncertain:
                _mark(campaign_id, phone, "sent", chat_id=chat_id)
                sent_n += 1
                status_txt = "sent"
                if send_type == "template":
                    body_txt = ""
                    if isinstance(meta, dict):
                        body_txt = str(meta.get("template_text") or meta.get("text") or "").strip()
                    header = format_wa_template_chat_message(
                        camp.get("template_name") or "",
                        body=body_txt,
                        header_image=camp.get("template_header_media_url") or "",
                    )
                else:
                    header = str(camp.get("text_body") or "").strip() or f"[Religious Campaign {campaign_id[:8]}] Text"
            else:
                err_txt = _format_send_error(meta, phone=phone)
                _mark(campaign_id, phone, "failed", err_txt, chat_id=chat_id)
                status_txt = "error"
                header = f"[Religious Campaign {campaign_id[:8]}] FAILED - {err_txt[:200]}"

            if chat_id:
                try:
                    import chat_db
                    chat_db.add_message(
                        chat_id=chat_id,
                        sender_type="agent",
                        text=header,
                        status=status_txt,
                        increment_unread=False,
                        source="WhatsApp",
                    )
                except Exception as e:
                    log.warning("log message failed for %s: %s", phone, e)

            if status_txt == "error" and _is_campaign_blocking_failure(err_txt, meta):
                _auto_stop_campaign(
                    campaign_id,
                    f"Auto-stopped after send failure to {phone}: {err_txt}",
                )
                stopped_early = True
                break

            if idx < len(phones) - 1:
                time.sleep(delay_sec)
                if not _is_campaign_running(campaign_id):
                    stopped_early = True
                    break
                if (idx + 1) % 20 == 0:
                    time.sleep(5)
        final = get_campaign(campaign_id) or {}
        if stopped_early or str(final.get("status") or "") == "cancelled":
            # Preserve auto-stop error already stored on the campaign.
            _set_campaign_status(campaign_id, "cancelled")
        else:
            _set_campaign_status(campaign_id, "completed")
    except Exception as e:
        log.exception("campaign send loop crashed")
        _auto_stop_campaign(campaign_id, f"Auto-stopped: campaign crashed — {e}")
    finally:
        with _SEND_LOCK:
            _RUNNING.discard(campaign_id)


def start_campaign(agent, campaign_id: str, retry_failed: bool = False) -> dict:
    camp = get_campaign(campaign_id)
    if not camp:
        raise ValueError("campaign not found")
    with _SEND_LOCK:
        if campaign_id in _RUNNING:
            raise ValueError("campaign already running")
        _RUNNING.add(campaign_id)
    if retry_failed:
        with _connect() as conn:
            conn.execute(
                "UPDATE recipients SET status = 'pending', error = NULL WHERE campaign_id = ? AND status = 'failed'",
                (campaign_id,),
            )
            conn.commit()
    _set_campaign_status(campaign_id, "sending")
    t = threading.Thread(target=_send_loop, args=(agent, campaign_id), daemon=True)
    t.start()
    return get_campaign(campaign_id)


def cancel_campaign(campaign_id: str) -> dict:
    camp = get_campaign(campaign_id)
    if not camp:
        raise ValueError("campaign not found")
    with _SEND_LOCK:
        _RUNNING.discard(campaign_id)
    _set_campaign_status(campaign_id, "cancelled")
    with _connect() as conn:
        conn.execute(
            "UPDATE recipients SET status = 'pending', error = NULL WHERE campaign_id = ? AND status = 'sending'",
            (campaign_id,),
        )
        conn.commit()
    return get_campaign(campaign_id)


def update_campaign(campaign_id: str, payload: dict) -> dict:
    """Edit draft/cancelled/completed campaign content and optionally add phones."""
    camp = get_campaign(campaign_id)
    if not camp:
        raise ValueError("campaign not found")
    status = str(camp.get("status") or "")
    if status == "sending" or _is_campaign_running(campaign_id):
        raise ValueError("cannot edit while campaign is sending — stop it first")

    name = payload.get("name")
    send_type = payload.get("send_type")
    template_name = payload.get("template_name")
    template_language = payload.get("template_language")
    template_header_media_url = payload.get("template_header_media_url")
    template_header_media_type = payload.get("template_header_media_type")
    text_body = payload.get("text_body") if "text_body" in payload else payload.get("text")
    delay_sec = payload.get("delay_sec")
    variables = payload.get("template_variables")
    phones_raw = payload.get("phones") if "phones" in payload else payload.get("phone_list")
    reset_to_draft = bool(payload.get("reset_to_draft", True))

    next_send_type = str(send_type or camp.get("send_type") or "").strip().lower()
    if next_send_type not in ("template", "text"):
        raise ValueError("send_type must be template or text")

    next_name = str(name if name is not None else camp.get("name") or "").strip()
    if not next_name:
        raise ValueError("name is required")

    next_template_name = str(
        template_name if template_name is not None else camp.get("template_name") or ""
    ).strip()
    next_template_language = str(
        template_language if template_language is not None else camp.get("template_language") or "en"
    ).strip() or "en"
    next_text_body = str(
        text_body if text_body is not None else camp.get("text_body") or ""
    ).strip()
    if next_send_type == "template" and not next_template_name:
        raise ValueError("template_name is required")
    if next_send_type == "text" and not next_text_body:
        raise ValueError("text_body is required")

    next_delay = float(delay_sec if delay_sec is not None else camp.get("delay_sec") or 2.5)
    if next_delay < 1.5:
        next_delay = 1.5
    if next_delay > 8:
        next_delay = 8

    if variables is None:
        next_vars = camp.get("template_variables") or []
    elif isinstance(variables, list):
        next_vars = [str(x) for x in variables]
    else:
        next_vars = []

    next_header_url = str(
        template_header_media_url
        if template_header_media_url is not None
        else camp.get("template_header_media_url")
        or ""
    ).strip()
    next_header_type = str(
        template_header_media_type
        if template_header_media_type is not None
        else camp.get("template_header_media_type")
        or "image"
    ).strip() or "image"

    new_phones = parse_phone_list(phones_raw) if phones_raw is not None else []

    with _connect() as conn:
        conn.execute(
            """
            UPDATE campaigns SET
                name = ?,
                send_type = ?,
                template_name = ?,
                template_language = ?,
                template_header_media_url = ?,
                template_header_media_type = ?,
                template_variables_json = ?,
                text_body = ?,
                delay_sec = ?,
                status = CASE WHEN ? THEN 'draft' ELSE status END,
                finished_at = CASE WHEN ? THEN NULL ELSE finished_at END,
                error = CASE WHEN ? THEN NULL ELSE error END
            WHERE id = ?
            """,
            (
                next_name,
                next_send_type,
                next_template_name,
                next_template_language,
                next_header_url,
                next_header_type,
                json.dumps(next_vars, ensure_ascii=False),
                next_text_body,
                next_delay,
                1 if reset_to_draft and status in ("cancelled", "completed", "draft") else 0,
                1 if reset_to_draft and status in ("cancelled", "completed") else 0,
                1 if reset_to_draft else 0,
                campaign_id,
            ),
        )
        if new_phones:
            conn.executemany(
                "INSERT OR IGNORE INTO recipients (campaign_id, phone, status) VALUES (?, ?, 'pending')",
                [(campaign_id, p) for p in new_phones],
            )
        conn.commit()
    return get_campaign(campaign_id)


def religious_from_info(company_id=None):
    cid = str(company_id or "fts").strip() or "fts"
    phone_id = RELIGIOUS_PHONE_ID
    display = RELIGIOUS_DISPLAY
    locked = cid == "fts"
    try:
        import company_tenancy
        conn = company_tenancy.get_connections(cid)
        if conn.get("religiousWaPhoneNumberId"):
            phone_id = conn["religiousWaPhoneNumberId"]
            locked = False
        if conn.get("religiousWaDisplay"):
            display = conn["religiousWaDisplay"]
            locked = False
    except Exception:
        pass
    return {
        "location": RELIGIOUS_LOCATION,
        "phone_number_id": phone_id,
        "display_phone_number": display,
        "locked": locked,
        "company_id": cid,
    }


def register_routes(app, agent):
    from flask import jsonify, request
    import company_tenancy

    def _ok_options():
        return jsonify({"status": "ok"}), 200

    def _actor_company_id():
        username = str(request.args.get("actor_username") or "").strip()
        payload = request.get_json(silent=True) or {}
        if not username:
            actor = payload.get("actor") if isinstance(payload, dict) else {}
            if isinstance(actor, dict):
                username = str(actor.get("username") or actor.get("id") or "").strip()
        if not username:
            username = str(payload.get("actor_username") or "").strip()
        return company_tenancy.resolve_company_id(username=username)

    def _guard_campaign(campaign_id):
        camp = get_campaign(campaign_id)
        if not camp:
            return None, (jsonify({"status": "error", "message": "not found"}), 404)
        camp_company = str(camp.get("company_id") or "fts").strip() or "fts"
        if camp_company != _actor_company_id():
            return None, (jsonify({"status": "error", "message": "not found"}), 404)
        return camp, None

    @app.route("/api/religious_wa_campaigns/from", methods=["GET", "OPTIONS"])
    def api_rwc_from():
        if request.method == "OPTIONS":
            return _ok_options()
        return jsonify({"status": "success", "data": religious_from_info(_actor_company_id())}), 200

    @app.route("/api/religious_wa_campaigns", methods=["GET", "POST", "OPTIONS"])
    def api_rwc_list_create():
        if request.method == "OPTIONS":
            return _ok_options()
        try:
            company_id = _actor_company_id()
            if request.method == "GET":
                return jsonify({"status": "success", "data": list_campaigns(company_id), "from": religious_from_info(company_id)}), 200
            payload = request.get_json(silent=True) or {}
            payload["company_id"] = company_id
            from_info = religious_from_info(company_id)
            payload.setdefault("receiving_phone_id", from_info.get("phone_number_id"))
            camp = create_campaign(payload)
            return jsonify({"status": "success", "data": camp}), 200
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            log.exception("religious_wa_campaigns list/create")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/religious_wa_campaigns/<campaign_id>", methods=["GET", "PUT", "PATCH", "OPTIONS"])
    def api_rwc_get_or_update(campaign_id):
        if request.method == "OPTIONS":
            return _ok_options()
        if request.method in ("PUT", "PATCH"):
            try:
                camp, err = _guard_campaign(campaign_id)
                if err:
                    return err
                payload = request.get_json(silent=True) or {}
                camp = update_campaign(campaign_id, payload)
                return jsonify({"status": "success", "data": camp}), 200
            except ValueError as e:
                return jsonify({"status": "error", "message": str(e)}), 400
            except Exception as e:
                log.exception("update campaign")
                return jsonify({"status": "error", "message": str(e)}), 500
        camp, err = _guard_campaign(campaign_id)
        if err:
            return err
        recipients = list_recipients(campaign_id)
        return jsonify({"status": "success", "data": camp, "recipients": recipients, "from": religious_from_info(_actor_company_id())}), 200

    @app.route("/api/religious_wa_campaigns/<campaign_id>/start", methods=["POST", "OPTIONS"])
    def api_rwc_start(campaign_id):
        if request.method == "OPTIONS":
            return _ok_options()
        try:
            camp, err = _guard_campaign(campaign_id)
            if err:
                return err
            payload = request.get_json(silent=True) or {}
            camp = start_campaign(agent, campaign_id, retry_failed=bool(payload.get("retry_failed")))
            return jsonify({"status": "success", "data": camp}), 200
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            log.exception("start campaign")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/religious_wa_campaigns/<campaign_id>/cancel", methods=["POST", "OPTIONS"])
    def api_rwc_cancel(campaign_id):
        if request.method == "OPTIONS":
            return _ok_options()
        try:
            camp, err = _guard_campaign(campaign_id)
            if err:
                return err
            camp = cancel_campaign(campaign_id)
            return jsonify({"status": "success", "data": camp}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
