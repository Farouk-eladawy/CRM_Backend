import sqlite3
import uuid
import os
import re
import time
import json
import logging
import threading
from email.utils import parseaddr
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from fts_paths import get_data_path

DB_FILE = get_data_path('chat_history.db')
DEFAULT_COMPANY_ID = 'fts'
_COMPANY_ID_SQL = "COALESCE(NULLIF(company_id, ''), 'fts')"
CAIRO_OFFSET = timedelta(hours=3)
_LAST_TRASH_PURGE_TS = 0.0
_FACEBOOK_REFERRAL_KV_RE = re.compile(
    r'(source|type|ad_id|ad_title|post_id|ref|referer_uri|hop_metadata)=([^=]+?)(?=\s+(?:source|type|ad_id|ad_title|post_id|ref|referer_uri|hop_metadata)=|$)',
    re.IGNORECASE,
)

def _connect(timeout=30.0):
    conn = sqlite3.connect(DB_FILE, timeout=float(timeout or 30.0))
    try:
        conn.execute("PRAGMA busy_timeout = 30000;")
    except Exception:
        pass
    return conn


def _get_db():
    return _connect()


def _get_cairo_timezone():
    if ZoneInfo is not None:
        try:
            return ZoneInfo("Africa/Cairo")
        except Exception:
            pass
    return timezone(CAIRO_OFFSET)


def _get_cairo_now():
    return datetime.now(_get_cairo_timezone())


def _parse_facebook_referral_notice(text):
    raw = str(text or "").strip()
    if not raw.startswith("[Facebook") or "Referral]" not in raw:
        return {}

    parsed = {}
    for match in _FACEBOOK_REFERRAL_KV_RE.finditer(raw):
        key = str(match.group(1) or "").strip().lower()
        value = str(match.group(2) or "").strip()
        if key and value:
            parsed[key] = value
    return parsed


def _assume_utc_to_cairo(value):
    if not value:
        return None
    dt = value if isinstance(value, datetime) else _parse_iso_dt(value)
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_get_cairo_timezone())


def _assume_cairo_local(value):
    if not value:
        return None
    dt = value if isinstance(value, datetime) else _parse_iso_dt(value)
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_get_cairo_timezone())
    return dt.astimezone(_get_cairo_timezone())


def _serialize_dt(value):
    if not value:
        return None
    try:
        return value.isoformat()
    except Exception:
        return None


def _resolve_dashboard_window(range_key=None, start=None, end=None):
    now_cairo = _get_cairo_now()
    end_dt = _assume_cairo_local(end) or now_cairo
    key = str(range_key or "today").strip().lower()
    if key in ("7d", "last_7_days", "last7days", "week"):
        start_dt = (end_dt - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        label = "Last 7 Days"
        granularity = "day"
        normalized = "7d"
    elif key in ("30d", "last_30_days", "last30days", "month"):
        start_dt = (end_dt - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
        label = "Last 30 Days"
        granularity = "day"
        normalized = "30d"
    else:
        start_dt = end_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        label = "Today"
        granularity = "hour"
        normalized = "today"
    start_dt = _assume_cairo_local(start) or start_dt
    return {
        "range_key": normalized,
        "label": label,
        "start": start_dt,
        "end": end_dt,
        "granularity": granularity,
    }


def _normalize_email_identifier(sender_identifier):
    raw = str(sender_identifier or "").strip()
    if not raw:
        return ""
    if "::" in raw:
        base, suffix = raw.split("::", 1)
        parsed = parseaddr(base)[1] or base
        parsed = str(parsed or "").strip().lower()
        suffix = str(suffix or "").strip()
        return f"{parsed}::{suffix}" if parsed and suffix else (parsed or raw.lower())
    parsed = parseaddr(raw)[1] or raw
    return str(parsed or "").strip().lower()


def _find_email_conversation_by_normalized_identifier(cursor, normalized_identifier, company_id=None):
    normalized_identifier = _normalize_email_identifier(normalized_identifier)
    if not normalized_identifier:
        return None
    like_value = f"%{normalized_identifier.split('::', 1)[0]}%"
    company_key = str(company_id or DEFAULT_COMPANY_ID).strip() or DEFAULT_COMPANY_ID
    cursor.execute(
        f"""
        SELECT *
        FROM conversations
        WHERE source = 'Email'
          AND lower(sender_identifier) LIKE ?
          AND {_COMPANY_ID_SQL} = ?
        ORDER BY last_message_time DESC
        """,
        (like_value, company_key),
    )
    for row in cursor.fetchall():
        try:
            row_norm = _normalize_email_identifier(row["sender_identifier"])
            if row_norm == normalized_identifier:
                return row
        except Exception:
            continue
    return None

def purge_trashed_conversations(retention_days=7, max_per_run=200, min_interval_seconds=60):
    global _LAST_TRASH_PURGE_TS
    now_ts = time.time()
    if _LAST_TRASH_PURGE_TS and (now_ts - _LAST_TRASH_PURGE_TS) < float(min_interval_seconds or 0):
        return {"purged": 0}
    _LAST_TRASH_PURGE_TS = now_ts

    try:
        days_i = int(retention_days or 7)
    except Exception:
        days_i = 7
    days_i = max(1, min(days_i, 365))

    try:
        max_i = int(max_per_run or 0)
    except Exception:
        max_i = 200
    max_i = max(1, min(max_i, 5000))

    cutoff = (datetime.utcnow() - timedelta(days=days_i)).isoformat()
    purged = 0
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute(
            """
            SELECT chat_id
            FROM conversations
            WHERE COALESCE(is_deleted, 0) = 1
              AND deleted_at IS NOT NULL
              AND deleted_at < ?
            ORDER BY deleted_at ASC
            LIMIT ?
            """,
            (cutoff, max_i),
        )
        chat_ids = [str(r[0]) for r in c.fetchall() if r and r[0]]
        if not chat_ids:
            return {"purged": 0}
        placeholders = ",".join(["?"] * len(chat_ids))
        try:
            c.execute(f"DELETE FROM messages WHERE chat_id IN ({placeholders})", chat_ids)
        except sqlite3.OperationalError:
            pass
        try:
            c.execute(f"DELETE FROM sales_customer_state WHERE chat_id IN ({placeholders})", chat_ids)
        except sqlite3.OperationalError:
            pass
        try:
            c.execute(f"DELETE FROM sales_activity WHERE chat_id IN ({placeholders})", chat_ids)
        except sqlite3.OperationalError:
            pass
        try:
            c.execute(f"DELETE FROM conversations WHERE chat_id IN ({placeholders})", chat_ids)
        except sqlite3.OperationalError:
            pass
        purged = len(chat_ids)
        conn.commit()
    return {"purged": purged}

def trash_conversation(chat_id, actor=None, reason=""):
    if not chat_id:
        return {"ok": False, "error": "missing_chat_id"}
    actor_obj = actor or {}
    actor_name = str(actor_obj.get("name") or actor_obj.get("username") or actor_obj.get("id") or actor_obj.get("user_id") or "Admin")
    actor_user_id = str(actor_obj.get("id") or actor_obj.get("username") or actor_obj.get("user_id") or actor_name)
    ts = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute(
            """
            UPDATE conversations
            SET is_deleted = 1, deleted_at = ?, deleted_by = ?, deleted_reason = ?
            WHERE chat_id = ?
            """,
            (ts, actor_user_id, str(reason or "").strip(), str(chat_id)),
        )
        conn.commit()
    try:
        log_text = f"[System Log] Conversation moved to Trash by {actor_name}"
        if str(reason or "").strip():
            log_text = log_text + f". Reason: {str(reason).strip()}"
        add_message(chat_id=str(chat_id), sender_type="agent", text=log_text)
    except Exception:
        pass
    return {"ok": True}

def restore_conversation(chat_id, actor=None):
    if not chat_id:
        return {"ok": False, "error": "missing_chat_id"}
    actor_obj = actor or {}
    actor_name = str(actor_obj.get("name") or actor_obj.get("username") or actor_obj.get("id") or actor_obj.get("user_id") or "Admin")
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute(
            """
            UPDATE conversations
            SET is_deleted = 0, deleted_at = NULL, deleted_by = NULL, deleted_reason = NULL
            WHERE chat_id = ?
            """,
            (str(chat_id),),
        )
        conn.commit()
    try:
        add_message(chat_id=str(chat_id), sender_type="agent", text=f"[System Log] Conversation restored from Trash by {actor_name}")
    except Exception:
        pass
    return {"ok": True}

def get_cairo_time():
    return (datetime.utcnow() + CAIRO_OFFSET).isoformat()

_CHANNEL_UNIQUE_READY = False
_CHANNEL_UNIQUE_LOCK = threading.Lock()


def ensure_conversations_channel_unique():
    """Allow the same phone on another company channel.

    The live table was created with UNIQUE(source, sender_identifier), so a
    Nile Crystal WhatsApp message could not get its own row beside an FTS chat.
    The replacement key is UNIQUE(source, sender_identifier, thread_id).
    """
    global _CHANNEL_UNIQUE_READY
    if _CHANNEL_UNIQUE_READY:
        return False
    with _CHANNEL_UNIQUE_LOCK:
        if _CHANNEL_UNIQUE_READY:
            return False
        with _connect(60.0) as conn:
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='conversations'"
            ).fetchone()
            sql = str((row[0] if row else "") or "")
            compact = "".join(sql.split()).lower()
            if "unique(source,sender_identifier,thread_id)" in compact:
                _CHANNEL_UNIQUE_READY = True
                return False
            cols = list(conn.execute("PRAGMA table_info(conversations)"))
            if not cols:
                _CHANNEL_UNIQUE_READY = True
                return False
            col_names = []
            col_defs = []
            for _cid, name, coltype, _notnull, dflt, pk in cols:
                col_names.append(name)
                if pk:
                    col_defs.append(f'"{name}" {coltype or "TEXT"} PRIMARY KEY')
                    continue
                piece = f'"{name}" {coltype or "TEXT"}'
                if dflt is not None:
                    piece += f" DEFAULT {dflt}"
                col_defs.append(piece)
            col_defs.append("UNIQUE(source, sender_identifier, thread_id)")
            extras = conn.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE tbl_name='conversations' AND sql IS NOT NULL AND type IN ('index', 'trigger')
                """
            ).fetchall()
            names_sql = ", ".join(f'"{name}"' for name in col_names)
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    f"CREATE TABLE conversations__channel_uniq ({', '.join(col_defs)})"
                )
                conn.execute(
                    f"INSERT INTO conversations__channel_uniq ({names_sql}) SELECT {names_sql} FROM conversations"
                )
                conn.execute("DROP TABLE conversations")
                conn.execute("ALTER TABLE conversations__channel_uniq RENAME TO conversations")
                for (extra_sql,) in extras:
                    if extra_sql:
                        conn.execute(extra_sql)
                conn.execute("COMMIT")
            except Exception:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                raise
        _CHANNEL_UNIQUE_READY = True
        return True


def init_db():
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute('PRAGMA journal_mode=WAL;')
        try:
            c.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        # Conversations Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                chat_id TEXT PRIMARY KEY,
                source TEXT,
                sender_identifier TEXT,
                contact_name TEXT,
                airtable_record_id TEXT,
                last_message_time TIMESTAMP,
                unread_count INTEGER DEFAULT 0,
                location TEXT DEFAULT 'Unknown',
                needs_help INTEGER DEFAULT 0,
                lead_owner_user_id TEXT,
                lead_owner_name TEXT,
                lead_owner_assigned_at TIMESTAMP,
                thread_id TEXT,
                UNIQUE(source, sender_identifier, thread_id)
            )
        ''')
        
        # Check if needs_help column exists and add if not (for existing databases)
        c.execute("PRAGMA table_info(conversations)")
        columns = [col[1] for col in c.fetchall()]
        if 'needs_help' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN needs_help INTEGER DEFAULT 0")
        if 'thread_id' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN thread_id TEXT")
        if 'receiving_phone_id' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN receiving_phone_id TEXT")
        if 'booking_number' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN booking_number TEXT")
        if 'force_read_at' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN force_read_at TIMESTAMP")
        if 'lead_owner_user_id' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN lead_owner_user_id TEXT")
        if 'lead_owner_name' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN lead_owner_name TEXT")
        if 'lead_owner_assigned_at' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN lead_owner_assigned_at TIMESTAMP")
        if 'sales_inbox' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN sales_inbox INTEGER DEFAULT 0")
        if 'last_customer_channel' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN last_customer_channel TEXT")
        if 'is_deleted' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN is_deleted INTEGER DEFAULT 0")
        if 'deleted_at' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN deleted_at TIMESTAMP")
        if 'deleted_by' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN deleted_by TEXT")
        if 'deleted_reason' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN deleted_reason TEXT")
        if 'quality_from_location' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN quality_from_location TEXT")
        if 'customer_note' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN customer_note TEXT")
        if 'customer_note_updated_at' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN customer_note_updated_at TIMESTAMP")
        if 'customer_note_updated_by' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN customer_note_updated_by TEXT")
        if 'customer_note_owner_user_id' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN customer_note_owner_user_id TEXT")
        if 'company_id' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN company_id TEXT DEFAULT 'fts'")
            try:
                c.execute("UPDATE conversations SET company_id = 'fts' WHERE company_id IS NULL OR TRIM(company_id) = ''")
            except Exception:
                pass
        c.execute('CREATE INDEX IF NOT EXISTS idx_conversations_company_id ON conversations(company_id);')
        c.execute('CREATE INDEX IF NOT EXISTS idx_conversations_last_message_time ON conversations(last_message_time DESC);')
        c.execute('CREATE INDEX IF NOT EXISTS idx_conversations_location_last_message_time ON conversations(location, last_message_time DESC);')
        c.execute('CREATE INDEX IF NOT EXISTS idx_conversations_deleted_at ON conversations(is_deleted, deleted_at);')
        c.execute('CREATE INDEX IF NOT EXISTS idx_conversations_quality_from_location_last_message_time ON conversations(quality_from_location, last_message_time DESC);')
        try:
            ensure_conversations_channel_unique()
        except Exception as uniq_err:
            logging.warning("Conversation channel unique migration skipped: %s", uniq_err)
        # Messages Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                msg_id TEXT PRIMARY KEY,
                chat_id TEXT,
                sender_type TEXT, -- 'customer', 'agent', 'ai'
                text TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT
            )
        ''')
        c.execute("PRAGMA table_info(messages)")
        msg_columns = [col[1] for col in c.fetchall()]
        if 'source' not in msg_columns:
            c.execute("ALTER TABLE messages ADD COLUMN source TEXT")
        if 'external_message_id' not in msg_columns:
            c.execute("ALTER TABLE messages ADD COLUMN external_message_id TEXT")
        if 'reaction_to_external_message_id' not in msg_columns:
            c.execute("ALTER TABLE messages ADD COLUMN reaction_to_external_message_id TEXT")
        if 'reaction_emoji' not in msg_columns:
            c.execute("ALTER TABLE messages ADD COLUMN reaction_emoji TEXT")
        c.execute('CREATE INDEX IF NOT EXISTS idx_messages_chat_id_timestamp ON messages(chat_id, timestamp DESC);')
        
        # User Settings Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS sales_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor_user_id TEXT,
                actor_name TEXT,
                meta_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_sales_activity_chat_id_created_at ON sales_activity(chat_id, created_at DESC);')

        c.execute('''
            CREATE TABLE IF NOT EXISTS hr_audit_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_user_id TEXT NOT NULL,
                actor_name TEXT,
                actor_role TEXT,
                event_type TEXT NOT NULL,
                meta_json TEXT,
                details_json TEXT,
                details_enc TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_hr_audit_actor_time ON hr_audit_activity(actor_user_id, created_at DESC);')
        c.execute('CREATE INDEX IF NOT EXISTS idx_hr_audit_time ON hr_audit_activity(created_at DESC);')
        c.execute('CREATE INDEX IF NOT EXISTS idx_hr_audit_role ON hr_audit_activity(actor_role);')
        c.execute("PRAGMA table_info(hr_audit_activity)")
        hr_cols = [col[1] for col in c.fetchall()]
        if 'meta_json' not in hr_cols:
            c.execute("ALTER TABLE hr_audit_activity ADD COLUMN meta_json TEXT")
        if 'details_json' not in hr_cols:
            c.execute("ALTER TABLE hr_audit_activity ADD COLUMN details_json TEXT")

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS sales_customer_state (
                chat_id TEXT PRIMARY KEY,
                lead_status TEXT,
                priority TEXT,
                ai_priority TEXT,
                tags TEXT,
                ai_tags TEXT,
                lead_score INTEGER,
                follow_up_date TEXT,
                last_contact_date TEXT,
                next_action TEXT,
                ai_next_action TEXT,
                sales_notes TEXT,
                ai_sales_summary TEXT,
                is_starred INTEGER DEFAULT 0,
                reason_for_marking TEXT,
                assigned_sales_user TEXT,
                needs_ai_review INTEGER DEFAULT 0,
                overdue_followup INTEGER DEFAULT 0,
                ready_to_close INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_sales_state_assigned_sales_user ON sales_customer_state(assigned_sales_user);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sales_state_follow_up_date ON sales_customer_state(follow_up_date);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sales_state_lead_score ON sales_customer_state(lead_score DESC);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sales_state_priority ON sales_customer_state(priority);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sales_state_last_contact_date ON sales_customer_state(last_contact_date DESC);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sales_state_is_starred ON sales_customer_state(is_starred);")

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP,
                department TEXT,
                source TEXT,
                system_role TEXT,
                provider TEXT,
                model TEXT,
                location TEXT,
                chat_id TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                estimated INTEGER DEFAULT 0
            )
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_ai_usage_created_at ON ai_usage_events(created_at DESC);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ai_usage_department_created_at ON ai_usage_events(department, created_at DESC);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ai_usage_provider_created_at ON ai_usage_events(provider, created_at DESC);")
        c.execute("PRAGMA table_info(ai_usage_events)")
        ai_usage_cols = [col[1] for col in c.fetchall()]
        if "prompt_cache_hit_tokens" not in ai_usage_cols:
            c.execute("ALTER TABLE ai_usage_events ADD COLUMN prompt_cache_hit_tokens INTEGER DEFAULT 0")
        if "prompt_cache_miss_tokens" not in ai_usage_cols:
            c.execute("ALTER TABLE ai_usage_events ADD COLUMN prompt_cache_miss_tokens INTEGER DEFAULT 0")
        if "pricing_tier" not in ai_usage_cols:
            c.execute("ALTER TABLE ai_usage_events ADD COLUMN pricing_tier TEXT")
        conn.commit()

def _get_hr_audit_fernet():
    import os
    key = os.environ.get("HR_AUDIT_KEY") or ""
    key = key.strip()
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
    except Exception:
        return None
    try:
        return Fernet(key.encode("utf-8"))
    except Exception:
        return None

def log_hr_audit_activity(actor_user_id, actor_name, actor_role, event_type, description="", meta=None):
    if not actor_user_id or not event_type:
        return False
    import json
    import logging
    meta_obj = meta or {}
    meta_min = {}
    try:
        for k in [
            "chat_id",
            "location",
            "from_location",
            "to_location",
            "source",
            "sender_identifier",
            "booking_number",
            "airtable_record_id",
            "contact_name",
            "has_file",
            "template_name",
            "idle_minutes",
            "reason",
            "tab",
        ]:
            if k in meta_obj:
                meta_min[k] = meta_obj.get(k)
    except Exception:
        meta_min = {}
    payload = {"description": description or "", "meta": meta_obj}
    details_json = None
    try:
        details_json = json.dumps(payload, ensure_ascii=False)
    except Exception:
        details_json = None
    meta_json = None
    try:
        meta_json = json.dumps(meta_min, ensure_ascii=False)
    except Exception:
        meta_json = None
    attempts = 4
    for attempt in range(attempts):
        try:
            with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                try:
                    conn.execute("PRAGMA busy_timeout = 30000;")
                except Exception:
                    pass
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO hr_audit_activity (actor_user_id, actor_name, actor_role, event_type, meta_json, details_json, details_enc, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(actor_user_id),
                        str(actor_name or ""),
                        str(actor_role or ""),
                        str(event_type),
                        meta_json,
                        details_json,
                        None,
                        get_cairo_time(),
                    ),
                )
                conn.commit()
                return True
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < (attempts - 1):
                time.sleep(0.2 * (attempt + 1))
                continue
            logging.error(f"HR audit sqlite write failed: {e}", exc_info=True)
            return False
        except Exception as e:
            logging.error(f"HR audit write failed: {e}", exc_info=True)
            return False
    return False

def query_hr_audit_activity(actor_user_id=None, actor_role=None, start=None, end=None, sort="desc", page=1, page_size=50, exclude_admin=True, event_type=None, q=None):
    where = []
    params = []
    if actor_user_id:
        where.append("actor_user_id = ?")
        params.append(str(actor_user_id))
    if actor_role:
        where.append("LOWER(COALESCE(actor_role, '')) = LOWER(?)")
        params.append(str(actor_role))
    if exclude_admin:
        where.append("LOWER(COALESCE(actor_role, '')) != 'admin'")
    if event_type:
        where.append("event_type = ?")
        params.append(str(event_type))
    if start:
        where.append("created_at >= ?")
        params.append(str(start))
    if end:
        where.append("created_at <= ?")
        params.append(str(end))

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    order = "ASC" if str(sort or "").lower() == "asc" else "DESC"
    page = int(page) if page else 1
    page_size = int(page_size) if page_size else 50
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 50
    if page_size > 200:
        page_size = 200
    offset = (page - 1) * page_size

    import json

    q_str = str(q or "").strip()
    q_lower = q_str.lower()

    try:
        with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            if not q_lower:
                c.execute(f"SELECT COUNT(1) as cnt FROM hr_audit_activity {where_sql}", params)
                cnt_row = c.fetchone()
                if cnt_row is None:
                    total = 0
                else:
                    try:
                        total = int(cnt_row["cnt"])
                    except Exception:
                        try:
                            total = int(cnt_row[0])
                        except Exception:
                            total = 0

                try:
                    c.execute(
                        f"""
                        SELECT id, actor_user_id, actor_name, actor_role, event_type, meta_json, details_json, details_enc, created_at
                        FROM hr_audit_activity
                        {where_sql}
                        ORDER BY created_at {order}, id {order}
                        LIMIT ? OFFSET ?
                        """,
                        params + [page_size, offset],
                    )
                except sqlite3.OperationalError as e:
                    msg = str(e).lower()
                    if "no such column: meta_json" in msg or "no such column: details_json" in msg:
                        c.execute(
                            f"""
                            SELECT id, actor_user_id, actor_name, actor_role, event_type, details_enc, created_at
                            FROM hr_audit_activity
                            {where_sql}
                            ORDER BY created_at {order}, id {order}
                            LIMIT ? OFFSET ?
                            """,
                            params + [page_size, offset],
                        )
                    else:
                        raise
                rows = [dict(r) for r in c.fetchall()]
            else:
                try:
                    c.execute(
                        f"""
                        SELECT id, actor_user_id, actor_name, actor_role, event_type, meta_json, details_json, details_enc, created_at
                        FROM hr_audit_activity
                        {where_sql}
                        ORDER BY created_at {order}, id {order}
                        LIMIT 5000
                        """,
                        params,
                    )
                except sqlite3.OperationalError as e:
                    msg = str(e).lower()
                    if "no such column: meta_json" in msg or "no such column: details_json" in msg:
                        c.execute(
                            f"""
                            SELECT id, actor_user_id, actor_name, actor_role, event_type, details_enc, created_at
                            FROM hr_audit_activity
                            {where_sql}
                            ORDER BY created_at {order}, id {order}
                            LIMIT 5000
                            """,
                            params,
                        )
                    else:
                        raise
                all_rows = [dict(r) for r in c.fetchall()]
                rows = []
                for r in all_rows:
                    hay = " ".join(
                        [
                            str(r.get("actor_user_id") or ""),
                            str(r.get("actor_name") or ""),
                            str(r.get("event_type") or ""),
                            str(r.get("meta_json") or ""),
                            str(r.get("details_json") or ""),
                            str(r.get("details_enc") or ""),
                        ]
                    ).lower()
                    if q_lower in hay:
                        rows.append(r)
                total = len(rows)
                rows = rows[offset : offset + page_size]
    except sqlite3.OperationalError as e:
        if "no such table: hr_audit_activity" in str(e).lower():
            return {"items": [], "total": 0, "page": page, "page_size": page_size}
        raise

    items = []
    for r in rows:
        out = {
            "id": r.get("id"),
            "actor_user_id": r.get("actor_user_id"),
            "actor_name": r.get("actor_name"),
            "actor_role": r.get("actor_role"),
            "event_type": r.get("event_type"),
            "created_at": r.get("created_at"),
            "description": "",
            "meta": None,
        }
        meta_json = r.get("meta_json")
        meta_plain = None
        if meta_json:
            try:
                meta_plain = json.loads(str(meta_json))
            except Exception:
                meta_plain = None
        details_json = r.get("details_json")
        if details_json:
            try:
                payload = json.loads(str(details_json))
                out["description"] = str(payload.get("description") or "")
                out["meta"] = payload.get("meta")
            except Exception:
                pass
        if out["meta"] is None and meta_plain is not None:
            out["meta"] = meta_plain
        items.append(out)

    return {"items": items, "total": total, "page": page, "page_size": page_size}

def _parse_iso_dt(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v))
    except Exception:
        return None

def _decrypt_hr_audit_details(details_enc):
    if not details_enc:
        return {"description": "", "meta": None}
    f = _get_hr_audit_fernet()
    if not f:
        return {"description": "", "meta": None}
    import json
    try:
        raw = f.decrypt(str(details_enc).encode("utf-8")).decode("utf-8")
        payload = json.loads(raw)
        return {"description": str(payload.get("description") or ""), "meta": payload.get("meta")}
    except Exception:
        return {"description": "", "meta": None}

def get_hr_audit_events(event_types=None, start=None, end=None, exclude_admin=True):
    event_types = event_types or []
    where = []
    params = []
    if event_types:
        placeholders = ",".join(["?"] * len(event_types))
        where.append(f"event_type IN ({placeholders})")
        params.extend([str(t) for t in event_types])
    if start:
        where.append("created_at >= ?")
        params.append(str(start))
    if end:
        where.append("created_at <= ?")
        params.append(str(end))
    if exclude_admin:
        where.append("LOWER(COALESCE(actor_role, '')) != 'admin'")
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    try:
        with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            try:
                c.execute(
                    f"""
                    SELECT id, actor_user_id, actor_name, actor_role, event_type, meta_json, details_json, details_enc, created_at
                    FROM hr_audit_activity
                    {where_sql}
                    ORDER BY created_at ASC, id ASC
                    """,
                    params,
                )
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if "no such column: meta_json" in msg or "no such column: details_json" in msg:
                    c.execute(
                        f"""
                        SELECT id, actor_user_id, actor_name, actor_role, event_type, details_enc, created_at
                        FROM hr_audit_activity
                        {where_sql}
                        ORDER BY created_at ASC, id ASC
                        """,
                        params,
                    )
                else:
                    raise
            rows = [dict(r) for r in c.fetchall()]
    except sqlite3.OperationalError as e:
        if "no such table: hr_audit_activity" in str(e).lower():
            return []
        raise

    out = []
    for r in rows:
        meta_plain = None
        mj = r.get("meta_json")
        if mj:
            try:
                import json
                meta_plain = json.loads(str(mj))
            except Exception:
                meta_plain = None
        meta_final = None
        desc = ""
        dj = r.get("details_json")
        if dj:
            try:
                import json
                payload = json.loads(str(dj))
                desc = str(payload.get("description") or "")
                meta_final = payload.get("meta")
            except Exception:
                pass
        if meta_final is None and meta_plain is not None:
            meta_final = meta_plain
        out.append(
            {
                "id": r.get("id"),
                "actor_user_id": r.get("actor_user_id"),
                "actor_name": r.get("actor_name"),
                "actor_role": r.get("actor_role"),
                "event_type": r.get("event_type"),
                "created_at": r.get("created_at"),
                "dt": _parse_iso_dt(r.get("created_at")),
                "description": desc,
                "meta": meta_final,
            }
        )
    return out

def compute_hr_audit_summary(start=None, end=None, top_n=10):
    events = get_hr_audit_events(
        event_types=["open_chat", "send_message", "send_template"],
        start=start,
        end=end,
        exclude_admin=True,
    )
    if not events:
        return {
            "top_openers": [],
            "top_unreplied_chats": [],
            "avg_response_seconds": None,
            "per_user": [],
        }

    from bisect import bisect_right

    def _conv_info(chat_id):
        try:
            with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT chat_id, source, sender_identifier, contact_name, booking_number, airtable_record_id FROM conversations WHERE chat_id = ?", (str(chat_id),))
                row = c.fetchone()
                if not row:
                    return {}
                d = dict(row)
                return {
                    "source": d.get("source") or "",
                    "sender_identifier": d.get("sender_identifier") or "",
                    "contact_name": d.get("contact_name") or "",
                    "booking_number": d.get("booking_number") or "",
                    "airtable_record_id": d.get("airtable_record_id") or "",
                }
        except Exception:
            return {}

    def _conv_key(chat_id, meta):
        try:
            m = meta or {}
            k = str(m.get("airtable_record_id") or "").strip()
            if k:
                return "rec:" + k
            s = str(m.get("sender_identifier") or "").strip()
            if s:
                return "id:" + s
        except Exception:
            pass
        try:
            info = _conv_info(chat_id) or {}
            k2 = str(info.get("airtable_record_id") or "").strip()
            if k2:
                return "rec:" + k2
            s2 = str(info.get("sender_identifier") or "").strip()
            if s2:
                return "id:" + s2
        except Exception:
            pass
        return "chat:" + str(chat_id)

    open_events = []
    send_times_by_chat_user = {}
    for e in events:
        meta = e.get("meta") or {}
        chat_id = meta.get("chat_id")
        dt = e.get("dt")
        if not chat_id or not dt:
            continue
        conv_key = _conv_key(chat_id, meta)
        if e.get("event_type") == "open_chat":
            open_events.append((dt, conv_key, str(chat_id), str(e.get("actor_user_id") or ""), str(e.get("actor_name") or ""), meta))
        elif e.get("event_type") in ("send_message", "send_template"):
            key = (conv_key, str(e.get("actor_user_id") or ""))
            send_times_by_chat_user.setdefault(key, []).append(dt)

    for k in list(send_times_by_chat_user.keys()):
        send_times_by_chat_user[k].sort()

    opens_by_user = {}
    response_by_user = {}
    unreplied_by_chat = {}
    response_times_all = []

    for open_dt, conv_key, chat_id, actor_user_id, actor_name, meta in open_events:
        if not actor_user_id:
            continue
        opens_by_user.setdefault(actor_user_id, {"actor_user_id": actor_user_id, "actor_name": actor_name, "opens": 0})
        opens_by_user[actor_user_id]["opens"] += 1

        send_list = send_times_by_chat_user.get((conv_key, actor_user_id), [])
        idx = bisect_right(send_list, open_dt)
        base_info = {
            "source": str((meta or {}).get("source") or ""),
            "sender_identifier": str((meta or {}).get("sender_identifier") or ""),
            "contact_name": str((meta or {}).get("contact_name") or ""),
            "booking_number": str((meta or {}).get("booking_number") or ""),
            "airtable_record_id": str((meta or {}).get("airtable_record_id") or ""),
        }
        if not any(base_info.values()):
            base_info = _conv_info(chat_id) or {}
        if idx < len(send_list):
            delta = (send_list[idx] - open_dt).total_seconds()
            response_times_all.append(delta)
            u = response_by_user.setdefault(actor_user_id, {"sum": 0.0, "count": 0, "unreplied": 0})
            u["sum"] += float(delta)
            u["count"] += 1
        else:
            u = response_by_user.setdefault(actor_user_id, {"sum": 0.0, "count": 0, "unreplied": 0})
            u["unreplied"] += 1
            x = unreplied_by_chat.setdefault(
                conv_key,
                {
                    "chat_id": chat_id,
                    "opens_without_reply": 0,
                    "last_open_at": None,
                    "last_open_by": None,
                    "source": base_info.get("source") or "",
                    "sender_identifier": base_info.get("sender_identifier") or "",
                    "contact_name": base_info.get("contact_name") or "",
                    "booking_number": base_info.get("booking_number") or "",
                    "airtable_record_id": base_info.get("airtable_record_id") or "",
                },
            )
            x["opens_without_reply"] += 1
            if not x["last_open_at"] or open_dt > x["last_open_at"]:
                x["last_open_at"] = open_dt
                x["last_open_by"] = actor_name or actor_user_id
                if base_info.get("source"):
                    x["source"] = base_info.get("source") or ""
                if base_info.get("sender_identifier"):
                    x["sender_identifier"] = base_info.get("sender_identifier") or ""
                if base_info.get("contact_name"):
                    x["contact_name"] = base_info.get("contact_name") or ""
                if base_info.get("booking_number"):
                    x["booking_number"] = base_info.get("booking_number") or ""
                if base_info.get("airtable_record_id"):
                    x["airtable_record_id"] = base_info.get("airtable_record_id") or ""

    top_openers = sorted(opens_by_user.values(), key=lambda x: (-int(x.get("opens") or 0), str(x.get("actor_user_id") or "")))[: int(top_n or 10)]
    top_unreplied = sorted(unreplied_by_chat.values(), key=lambda x: (-int(x.get("opens_without_reply") or 0), str(x.get("chat_id") or "")))[: int(top_n or 10)]

    avg_response_seconds = None
    if response_times_all:
        avg_response_seconds = float(sum(response_times_all) / max(1, len(response_times_all)))

    per_user = []
    for actor_user_id, u in response_by_user.items():
        avg_u = None
        if u.get("count"):
            avg_u = float(u["sum"] / max(1, u["count"]))
        base = opens_by_user.get(actor_user_id) or {"actor_user_id": actor_user_id, "actor_name": actor_user_id, "opens": 0}
        per_user.append(
            {
                "actor_user_id": actor_user_id,
                "actor_name": base.get("actor_name") or actor_user_id,
                "opens": int(base.get("opens") or 0),
                "avg_response_seconds": avg_u,
                "replied_opens": int(u.get("count") or 0),
                "unreplied_opens": int(u.get("unreplied") or 0),
            }
        )
    per_user.sort(key=lambda x: (-int(x.get("opens") or 0), str(x.get("actor_user_id") or "")))

    for x in top_unreplied:
        dt = x.get("last_open_at")
        x["last_open_at"] = dt.isoformat() if dt else None

    return {
        "top_openers": top_openers,
        "top_unreplied_chats": top_unreplied,
        "avg_response_seconds": avg_response_seconds,
        "per_user": per_user[: int(top_n or 10)],
    }


def _cairo_naive_iso(value):
    dt = _assume_cairo_local(value)
    if not dt:
        return None
    return dt.replace(tzinfo=None).isoformat()


def _trim_preview(text, limit=260):
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(s) <= int(limit or 0):
        return s
    return s[: max(0, int(limit or 0) - 1)].rstrip() + "…"


def _load_hr_send_events_for_actor(actor_user_id):
    if not actor_user_id:
        return []
    rows = []
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        try:
            c.execute(
                """
                SELECT id, actor_user_id, actor_name, actor_role, event_type, meta_json, details_json, details_enc, created_at
                FROM hr_audit_activity
                WHERE actor_user_id = ?
                  AND event_type IN ('send_message', 'send_template')
                ORDER BY created_at ASC, id ASC
                """,
                (str(actor_user_id),),
            )
            rows = [dict(r) for r in c.fetchall()]
        except sqlite3.OperationalError as e:
            if "no such table: hr_audit_activity" in str(e).lower():
                return []
            raise

    out = []
    for row in rows:
        meta_plain = None
        if row.get("meta_json"):
            try:
                import json
                meta_plain = json.loads(str(row.get("meta_json")))
            except Exception:
                meta_plain = None
        details_payload = None
        if row.get("details_json"):
            try:
                import json
                details_payload = json.loads(str(row.get("details_json")))
            except Exception:
                details_payload = None
        elif row.get("details_enc"):
            try:
                details_payload = _decrypt_hr_audit_details(row.get("details_enc"))
            except Exception:
                details_payload = None
        meta = None
        if isinstance(details_payload, dict):
            meta = details_payload.get("meta")
        if meta is None:
            meta = meta_plain
        created_at_cairo = _assume_utc_to_cairo(row.get("created_at"))
        out.append(
            {
                "id": row.get("id"),
                "actor_user_id": str(row.get("actor_user_id") or ""),
                "actor_name": str(row.get("actor_name") or ""),
                "actor_role": str(row.get("actor_role") or ""),
                "event_type": str(row.get("event_type") or ""),
                "created_at": row.get("created_at"),
                "created_at_cairo": created_at_cairo,
                "meta": meta if isinstance(meta, dict) else {},
            }
        )
    return out


def _load_messages_for_chat_ids(chat_ids, start_cairo=None, end_cairo=None, sender_type=None):
    ids = [str(x) for x in (chat_ids or []) if str(x or "").strip()]
    if not ids:
        return {}
    params = list(ids)
    where = ["chat_id IN (" + ",".join(["?"] * len(ids)) + ")"]
    if sender_type:
        where.append("sender_type = ?")
        params.append(str(sender_type))
    start_local = _cairo_naive_iso(start_cairo)
    end_local = _cairo_naive_iso(end_cairo)
    if start_local:
        where.append("timestamp >= ?")
        params.append(start_local)
    if end_local:
        where.append("timestamp <= ?")
        params.append(end_local)

    out = {cid: [] for cid in ids}
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute(
            f"""
            SELECT msg_id, chat_id, sender_type, text, timestamp, status, source
            FROM messages
            WHERE {' AND '.join(where)}
            ORDER BY chat_id ASC, timestamp ASC
            """,
            params,
        )
        for row in c.fetchall():
            item = dict(row)
            item["timestamp_cairo"] = _assume_cairo_local(item.get("timestamp"))
            out.setdefault(str(item.get("chat_id") or ""), []).append(item)
    return out


def _load_messages_by_sender_between(sender_type, start_cairo, end_cairo):
    out = []
    start_local = _cairo_naive_iso(start_cairo)
    end_local = _cairo_naive_iso(end_cairo)
    if not start_local or not end_local:
        return []
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute(
            """
            SELECT msg_id, chat_id, sender_type, text, timestamp, status, source
            FROM messages
            WHERE sender_type = ?
              AND timestamp >= ?
              AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            (str(sender_type or ""), start_local, end_local),
        )
        for row in c.fetchall():
            item = dict(row)
            item["timestamp_cairo"] = _assume_cairo_local(item.get("timestamp"))
            out.append(item)
    return out


def _match_event_to_agent_message(event, messages_for_chat, used_msg_ids=None):
    used_ids = used_msg_ids or set()
    event_dt = _assume_cairo_local((event or {}).get("created_at_cairo"))
    if not event_dt:
        return None
    actor_name = str((event or {}).get("actor_name") or "").strip().lower()
    candidates = []
    for msg in messages_for_chat or []:
        if str(msg.get("sender_type") or "") != "agent":
            continue
        msg_id = str(msg.get("msg_id") or "")
        if msg_id and msg_id in used_ids:
            continue
        msg_dt = _assume_cairo_local(msg.get("timestamp_cairo") or msg.get("timestamp"))
        if not msg_dt:
            continue
        delta_seconds = (msg_dt - event_dt).total_seconds()
        if delta_seconds < -900 or delta_seconds > 120:
            continue
        score = abs(delta_seconds)
        text_low = str(msg.get("text") or "").lower()
        if actor_name and actor_name in text_low:
            score -= 60
        if str((event or {}).get("event_type") or "") == "send_template":
            score -= 5
        candidates.append((score, abs(delta_seconds), msg_dt, msg))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1], x[2]))
    return candidates[0][3]


def _build_timeline_24h(now_cairo, human_events, ai_messages):
    now_local = _assume_cairo_local(now_cairo)
    if not now_local:
        return []
    start_bucket = (now_local - timedelta(hours=23)).replace(minute=0, second=0, microsecond=0)
    buckets = []
    index = {}
    for i in range(24):
        bucket_dt = start_bucket + timedelta(hours=i)
        key = bucket_dt.strftime("%Y-%m-%d %H:00")
        entry = {
            "key": key,
            "label": bucket_dt.strftime("%H:00"),
            "human": 0,
            "ai": 0,
            "total": 0,
        }
        buckets.append(entry)
        index[key] = entry
    for event in human_events or []:
        dt = _assume_cairo_local((event or {}).get("created_at_cairo"))
        if not dt:
            continue
        bucket_key = dt.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:00")
        if bucket_key in index:
            index[bucket_key]["human"] += 1
            index[bucket_key]["total"] += 1
    for msg in ai_messages or []:
        dt = _assume_cairo_local(msg.get("timestamp_cairo") or msg.get("timestamp"))
        if not dt:
            continue
        bucket_key = dt.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:00")
        if bucket_key in index:
            index[bucket_key]["ai"] += 1
            index[bucket_key]["total"] += 1
    return buckets


def _build_period_timeline(start_cairo, end_cairo, human_events, ai_messages, granularity="hour"):
    start_dt = _assume_cairo_local(start_cairo)
    end_dt = _assume_cairo_local(end_cairo)
    if not start_dt or not end_dt or start_dt > end_dt:
        return []

    if str(granularity or "").lower() == "day":
        cursor = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        final = end_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        step = timedelta(days=1)
        fmt_key = "%Y-%m-%d"
        fmt_label = "%m-%d"
    else:
        cursor = start_dt.replace(minute=0, second=0, microsecond=0)
        final = end_dt.replace(minute=0, second=0, microsecond=0)
        step = timedelta(hours=1)
        fmt_key = "%Y-%m-%d %H:00"
        fmt_label = "%H:00"

    buckets = []
    index = {}
    while cursor <= final:
        key = cursor.strftime(fmt_key)
        entry = {
            "key": key,
            "label": cursor.strftime(fmt_label),
            "human": 0,
            "ai": 0,
            "total": 0,
        }
        buckets.append(entry)
        index[key] = entry
        cursor += step

    def _bucket_key(dt):
        local = _assume_cairo_local(dt)
        if not local:
            return None
        if str(granularity or "").lower() == "day":
            local = local.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            local = local.replace(minute=0, second=0, microsecond=0)
        return local.strftime(fmt_key)

    for event in human_events or []:
        key = _bucket_key((event or {}).get("created_at_cairo"))
        if key in index:
            index[key]["human"] += 1
            index[key]["total"] += 1
    for msg in ai_messages or []:
        key = _bucket_key(msg.get("timestamp_cairo") or msg.get("timestamp"))
        if key in index:
            index[key]["ai"] += 1
            index[key]["total"] += 1
    return buckets


def compute_employee_dashboard_data(actor_user_id, actor_name=None, range_key="today", start=None, end=None):
    user_id = str(actor_user_id or "").strip()
    if not user_id:
        return None

    window = _resolve_dashboard_window(range_key=range_key, start=start, end=end)
    now_cairo = window["end"]
    period_start = window["start"]
    granularity = window["granularity"]

    all_send_events = _load_hr_send_events_for_actor(user_id)
    period_send_events = []
    resolved_name = str(actor_name or "").strip()
    for event in all_send_events:
        event_dt = _assume_cairo_local(event.get("created_at_cairo"))
        if not event_dt:
            continue
        if not resolved_name and str(event.get("actor_name") or "").strip():
            resolved_name = str(event.get("actor_name") or "").strip()
        if period_start <= event_dt <= now_cairo:
            period_send_events.append(event)

    actor_label = resolved_name or user_id

    chat_ids_period = []
    for event in period_send_events:
        meta = event.get("meta") or {}
        chat_id = str(meta.get("chat_id") or "").strip()
        if chat_id:
            chat_ids_period.append(chat_id)
    chat_ids_period = sorted(set(chat_ids_period))

    if granularity == "day":
        context_start = period_start - timedelta(days=2)
    else:
        context_start = period_start - timedelta(hours=8)
    messages_by_chat = _load_messages_for_chat_ids(chat_ids_period, start_cairo=context_start, end_cairo=now_cairo + timedelta(minutes=2))
    ai_messages_period = _load_messages_by_sender_between("ai", period_start, now_cairo)

    used_msg_ids = set()
    reply_samples = []
    period_index = {}
    for event in period_send_events:
        event_dt = _assume_cairo_local(event.get("created_at_cairo"))
        if not event_dt:
            continue
        if granularity == "day":
            bucket_key = event_dt.strftime("%Y-%m-%d")
            bucket_label = event_dt.strftime("%m-%d")
        else:
            bucket_key = f"{event_dt.hour:02d}"
            bucket_label = f"{event_dt.hour:02d}:00"
        if bucket_key not in period_index:
            period_index[bucket_key] = {"label": bucket_label, "human": 0}
        period_index[bucket_key]["human"] = int(period_index[bucket_key].get("human") or 0) + 1
        meta = event.get("meta") or {}
        chat_id = str(meta.get("chat_id") or "").strip()
        chat_messages = messages_by_chat.get(chat_id) or []
        matched_msg = _match_event_to_agent_message(event, chat_messages, used_msg_ids=used_msg_ids)
        if matched_msg and matched_msg.get("msg_id"):
            used_msg_ids.add(str(matched_msg.get("msg_id")))
        pivot_dt = _assume_cairo_local(
            (matched_msg or {}).get("timestamp_cairo")
            or (matched_msg or {}).get("timestamp")
            or event_dt
        ) or event_dt
        previous_customer = None
        next_customer = None
        for msg in chat_messages:
            msg_dt = _assume_cairo_local(msg.get("timestamp_cairo") or msg.get("timestamp"))
            if not msg_dt or str(msg.get("sender_type") or "") != "customer":
                continue
            if msg_dt <= pivot_dt:
                previous_customer = msg
            elif msg_dt > pivot_dt and next_customer is None and (msg_dt - pivot_dt).total_seconds() <= 21600:
                next_customer = msg
        reply_samples.append(
            {
                "reply_id": f"reply-{event.get('id')}",
                "event_id": event.get("id"),
                "chat_id": chat_id,
                "event_type": event.get("event_type"),
                "sent_at_cairo": _serialize_dt(event_dt),
                "matched": bool(matched_msg),
                "reply_text": _trim_preview((matched_msg or {}).get("text") or ""),
                "customer_message": _trim_preview((previous_customer or {}).get("text") or ""),
                "next_customer_message": _trim_preview((next_customer or {}).get("text") or "", limit=180),
                "source": str(meta.get("source") or ""),
                "contact_name": str(meta.get("contact_name") or ""),
                "sender_identifier": str(meta.get("sender_identifier") or ""),
                "booking_number": str(meta.get("booking_number") or ""),
            }
        )

    if granularity == "day":
        period_timeline = _build_period_timeline(period_start, now_cairo, period_send_events, ai_messages_period, granularity="day")
    else:
        period_timeline = _build_period_timeline(period_start, now_cairo, period_send_events, ai_messages_period, granularity="hour")

    human_replies_period = len(period_send_events)
    ai_replies_period = len(ai_messages_period)
    total_replies_period = human_replies_period + ai_replies_period
    human_share_pct = round((human_replies_period / total_replies_period) * 100, 1) if total_replies_period else 0.0
    ai_share_pct = round((ai_replies_period / total_replies_period) * 100, 1) if total_replies_period else 0.0

    return {
        "user": {
            "user_id": user_id,
            "display_name": actor_label,
        },
        "timezone": "Africa/Cairo",
        "generated_at_cairo": _serialize_dt(now_cairo),
        "scope": "employee",
        "filter": {
            "range_key": window["range_key"],
            "range_label": window["label"],
            "granularity": granularity,
        },
        "period_window": {
            "start": _serialize_dt(period_start),
            "end": _serialize_dt(now_cairo),
            "date": now_cairo.strftime("%Y-%m-%d"),
        },
        "today_window": {
            "start": _serialize_dt(period_start),
            "end": _serialize_dt(now_cairo),
            "date": now_cairo.strftime("%Y-%m-%d"),
        },
        "summary": {
            "total_replies": human_replies_period,
            "total_replied_today": human_replies_period,
            "human_replies_period": human_replies_period,
            "ai_replies_period": ai_replies_period,
            "total_replies_period": total_replies_period,
            "human_replies_24h": human_replies_period,
            "ai_replies_24h": ai_replies_period,
            "total_replies_24h": total_replies_period,
            "human_share_pct": human_share_pct,
            "ai_share_pct": ai_share_pct,
        },
        "charts": {
            "today_hourly": period_timeline,
            "period_timeline": period_timeline,
            "timeline_24h": period_timeline,
            "comparison_period": [
                {"label": "Human", "value": human_replies_period},
                {"label": "AI", "value": ai_replies_period},
                {"label": "Total", "value": total_replies_period},
            ],
            "comparison_24h": [
                {"label": "Human", "value": human_replies_period},
                {"label": "AI", "value": ai_replies_period},
                {"label": "Total", "value": total_replies_period},
            ],
        },
        "reply_samples": reply_samples,
    }


def _resolve_session_day_window(target_date=None):
    now_cairo = _get_cairo_now()
    if isinstance(target_date, datetime):
        day_value = target_date.date()
    elif hasattr(target_date, "year") and hasattr(target_date, "month") and hasattr(target_date, "day"):
        try:
            day_value = date(int(target_date.year), int(target_date.month), int(target_date.day))
        except Exception:
            day_value = now_cairo.date()
    else:
        raw = str(target_date or "").strip()
        if raw:
            try:
                day_value = datetime.strptime(raw[:10], "%Y-%m-%d").date()
            except Exception:
                day_value = now_cairo.date()
        else:
            day_value = now_cairo.date()
    start_dt = datetime.combine(day_value, datetime.min.time())
    is_today = day_value == now_cairo.date()
    end_dt = now_cairo if is_today else datetime.combine(day_value, datetime.max.time())
    return {
        "date": day_value.isoformat(),
        "start": _assume_cairo_local(start_dt) or start_dt,
        "end": _assume_cairo_local(end_dt) or end_dt,
        "is_today": is_today,
        "label": day_value.strftime("%Y-%m-%d"),
    }


def _load_hr_audit_events_for_actor(actor_user_id, start=None, end=None):
    if not actor_user_id:
        return []
    rows = []
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        clauses = ["actor_user_id = ?"]
        params = [str(actor_user_id)]
        if start:
            clauses.append("created_at >= ?")
            params.append(str(start))
        if end:
            clauses.append("created_at <= ?")
            params.append(str(end))
        try:
            c.execute(
                f"""
                SELECT id, actor_user_id, actor_name, actor_role, event_type, meta_json, details_json, details_enc, created_at
                FROM hr_audit_activity
                WHERE {' AND '.join(clauses)}
                ORDER BY created_at ASC, id ASC
                """,
                params,
            )
            rows = [dict(r) for r in c.fetchall()]
        except sqlite3.OperationalError as e:
            if "no such table: hr_audit_activity" in str(e).lower():
                return []
            raise

    out = []
    for row in rows:
        meta_plain = None
        if row.get("meta_json"):
            try:
                import json
                meta_plain = json.loads(str(row.get("meta_json")))
            except Exception:
                meta_plain = None
        details_payload = None
        if row.get("details_json"):
            try:
                import json
                details_payload = json.loads(str(row.get("details_json")))
            except Exception:
                details_payload = None
        elif row.get("details_enc"):
            try:
                details_payload = _decrypt_hr_audit_details(row.get("details_enc"))
            except Exception:
                details_payload = None
        meta = None
        description = ""
        if isinstance(details_payload, dict):
            meta = details_payload.get("meta")
            description = str(details_payload.get("description") or "")
        if meta is None:
            meta = meta_plain
        created_at_cairo = _assume_utc_to_cairo(row.get("created_at"))
        out.append(
            {
                "id": row.get("id"),
                "actor_user_id": str(row.get("actor_user_id") or ""),
                "actor_name": str(row.get("actor_name") or ""),
                "actor_role": str(row.get("actor_role") or ""),
                "event_type": str(row.get("event_type") or ""),
                "created_at": row.get("created_at"),
                "created_at_cairo": created_at_cairo,
                "description": description,
                "meta": meta if isinstance(meta, dict) else {},
            }
        )
    return out


def _hr_activity_weight(event_type):
    event_key = str(event_type or "").strip().lower()
    if event_key in ("send_message", "send_template"):
        return 1.0
    if event_key == "open_chat":
        return 0.35
    if event_key in ("claim_lead", "release_lead", "assign_lead", "unassign_lead"):
        return 0.6
    if event_key in ("trash_chat", "restore_chat", "dismiss_chat"):
        return 0.4
    if event_key in ("tab_switch",):
        return 0.05
    if event_key in ("close_tab",):
        return 0.0
    if event_key in ("login", "logout", "auto_logout"):
        return 0.0
    return 0.25


def compute_employee_session_day_data(actor_user_id, actor_name=None, target_date=None):
    user_id = str(actor_user_id or "").strip()
    if not user_id:
        return None

    day_window = _resolve_session_day_window(target_date=target_date)
    day_start = day_window["start"]
    day_end = day_window["end"]
    is_today = bool(day_window.get("is_today"))

    history_start = day_start - timedelta(days=1)
    all_events = _load_hr_audit_events_for_actor(user_id, start=_serialize_dt(history_start), end=_serialize_dt(day_end))
    if not all_events:
        actor_label = str(actor_name or user_id).strip() or user_id
        return {
            "user": {"user_id": user_id, "display_name": actor_label},
            "generated_at_cairo": _serialize_dt(_get_cairo_now()),
            "scope": "employee_session_day",
            "target_date": day_window["date"],
            "day_state": "open" if is_today else "closed",
            "filter": {"date": day_window["date"], "range_label": day_window["label"]},
            "period_window": {"start": _serialize_dt(day_start), "end": _serialize_dt(day_end)},
            "sessions": [],
            "summary": {
                "sessions_count": 0,
                "total_session_minutes": 0,
                "activity_events_count": 0,
                "weighted_activity": 0.0,
                "human_replies_period": 0,
                "template_replies_period": 0,
                "ai_replies_period": 0,
                "total_replies_period": 0,
                "human_share_pct": 0.0,
                "ai_share_pct": 0.0,
                "auto_logout_count": 0,
                "forced_midnight_count": 0,
                "implicit_restart_count": 0,
                "close_tab_count": 0,
                "session_starts_count": 0,
                "is_open": is_today,
            },
            "charts": {"period_timeline": [], "activity_breakdown": []},
            "reply_samples": [],
        }

    resolved_name = str(actor_name or "").strip()
    pre_day_open = False
    for event in all_events:
        event_dt = _assume_cairo_local(event.get("created_at_cairo"))
        if not event_dt:
            continue
        if not resolved_name and str(event.get("actor_name") or "").strip():
            resolved_name = str(event.get("actor_name") or "").strip()
        if event_dt >= day_start:
            break
        event_type = str(event.get("event_type") or "").strip().lower()
        if event_type == "login":
            pre_day_open = True
        elif event_type in ("logout", "auto_logout"):
            pre_day_open = False

    day_events = []
    for event in all_events:
        event_dt = _assume_cairo_local(event.get("created_at_cairo"))
        if not event_dt:
            continue
        if day_start <= event_dt <= day_end:
            copied = dict(event)
            copied["_dt"] = event_dt
            day_events.append(copied)

    actor_label = resolved_name or user_id
    sessions = []
    active_start = day_start if pre_day_open else None
    carry_in = bool(pre_day_open)
    session_seq = 0
    close_types = {"logout", "auto_logout"}
    for event in day_events:
        event_type = str(event.get("event_type") or "").strip().lower()
        event_dt = event.get("_dt")
        if event_type == "login":
            if active_start is not None:
                session_seq += 1
                sessions.append(
                    {
                        "session_id": f"{day_window['date']}:{user_id}:{session_seq}",
                        "login_at_cairo": _serialize_dt(active_start),
                        "logout_at_cairo": _serialize_dt(event_dt),
                        "logout_type": "implicit_restart",
                        "is_open": False,
                        "carry_in": carry_in,
                    }
                )
            active_start = event_dt
            carry_in = False
        elif event_type in close_types:
            if active_start is None:
                continue
            session_seq += 1
            sessions.append(
                {
                    "session_id": f"{day_window['date']}:{user_id}:{session_seq}",
                    "login_at_cairo": _serialize_dt(active_start),
                    "logout_at_cairo": _serialize_dt(event_dt),
                    "logout_type": event_type,
                    "is_open": False,
                    "carry_in": carry_in,
                }
            )
            active_start = None
            carry_in = False

    if active_start is not None:
        session_seq += 1
        sessions.append(
            {
                "session_id": f"{day_window['date']}:{user_id}:{session_seq}",
                "login_at_cairo": _serialize_dt(active_start),
                "logout_at_cairo": _serialize_dt(day_end),
                "logout_type": "open" if is_today else "forced_midnight",
                "is_open": bool(is_today),
                "carry_in": carry_in,
            }
        )

    def _find_session_for_dt(dt_value):
        for idx, session in enumerate(sessions):
            start_dt = _assume_cairo_local(session.get("login_at_cairo"))
            end_dt = _assume_cairo_local(session.get("logout_at_cairo"))
            if start_dt and end_dt and start_dt <= dt_value <= end_dt:
                return idx
        return None

    session_details = []
    for session in sessions:
        start_dt = _assume_cairo_local(session.get("login_at_cairo"))
        end_dt = _assume_cairo_local(session.get("logout_at_cairo"))
        minutes = max(0, int(round(((end_dt - start_dt).total_seconds() / 60.0)))) if start_dt and end_dt else 0
        detail = dict(session)
        detail.update(
            {
                "duration_minutes": minutes,
                "activity_events_count": 0,
                "weighted_activity": 0.0,
                "human_replies": 0,
                "template_replies": 0,
                "open_chat_count": 0,
                "lead_actions_count": 0,
                "chat_actions_count": 0,
                "tab_switch_count": 0,
                "other_events_count": 0,
                "close_tab_count": 0,
                "ai_replies_period": 0,
                "_activity_events": [],
                "_send_events": [],
            }
        )
        session_details.append(detail)

    activity_events = []
    send_events = []
    for event in day_events:
        event_type = str(event.get("event_type") or "").strip().lower()
        if event_type in ("login", "logout", "auto_logout"):
            continue
        idx = _find_session_for_dt(event.get("_dt"))
        if idx is None:
            continue
        detail = session_details[idx]
        weight = _hr_activity_weight(event_type)
        detail["_activity_events"].append(event)
        detail["activity_events_count"] += 1
        detail["weighted_activity"] = round(float(detail.get("weighted_activity") or 0.0) + weight, 2)
        activity_events.append(event)
        if event_type in ("send_message", "send_template"):
            detail["human_replies"] += 1
            if event_type == "send_template":
                detail["template_replies"] += 1
            detail["_send_events"].append(event)
            send_events.append(event)
        elif event_type == "open_chat":
            detail["open_chat_count"] += 1
        elif event_type in ("claim_lead", "release_lead", "assign_lead", "unassign_lead"):
            detail["lead_actions_count"] += 1
        elif event_type in ("trash_chat", "restore_chat", "dismiss_chat"):
            detail["chat_actions_count"] += 1
        elif event_type == "tab_switch":
            detail["tab_switch_count"] += 1
        elif event_type == "close_tab":
            detail["close_tab_count"] += 1
        else:
            detail["other_events_count"] += 1

    ai_messages_period = _load_messages_by_sender_between("ai", day_start, day_end)
    timeline_index = {}
    for hour in range(24):
        key = f"{hour:02d}"
        timeline_index[key] = {"key": key, "label": f"{hour:02d}:00", "human": 0, "ai": 0, "total": 0}

    for event in send_events:
        event_dt = event.get("_dt")
        if not event_dt:
            continue
        bucket = event_dt.strftime("%H")
        timeline_index[bucket]["human"] += 1

    total_ai_in_sessions = 0
    for msg in ai_messages_period:
        msg_dt = _assume_cairo_local(msg.get("timestamp_cairo") or msg.get("timestamp"))
        if not msg_dt:
            continue
        idx = _find_session_for_dt(msg_dt)
        if idx is None:
            continue
        session_details[idx]["ai_replies_period"] += 1
        total_ai_in_sessions += 1
        bucket = msg_dt.strftime("%H")
        timeline_index[bucket]["ai"] += 1

    for item in timeline_index.values():
        item["total"] = int(item.get("human") or 0) + int(item.get("ai") or 0)
    period_timeline = [timeline_index[key] for key in sorted(timeline_index.keys())]

    chat_ids_period = sorted(
        {
            str(((event.get("meta") or {}).get("chat_id") or "")).strip()
            for event in send_events
            if str(((event.get("meta") or {}).get("chat_id") or "")).strip()
        }
    )
    context_start = day_start - timedelta(hours=8)
    messages_by_chat = _load_messages_for_chat_ids(chat_ids_period, start_cairo=context_start, end_cairo=day_end + timedelta(minutes=2))
    used_msg_ids = set()
    reply_samples = []
    for event in send_events:
        meta = event.get("meta") or {}
        chat_id = str(meta.get("chat_id") or "").strip()
        chat_messages = messages_by_chat.get(chat_id) or []
        matched_msg = _match_event_to_agent_message(event, chat_messages, used_msg_ids=used_msg_ids)
        if matched_msg and matched_msg.get("msg_id"):
            used_msg_ids.add(str(matched_msg.get("msg_id")))
        pivot_dt = _assume_cairo_local(
            (matched_msg or {}).get("timestamp_cairo")
            or (matched_msg or {}).get("timestamp")
            or event.get("_dt")
        ) or event.get("_dt")
        previous_customer = None
        next_customer = None
        for msg in chat_messages:
            msg_dt = _assume_cairo_local(msg.get("timestamp_cairo") or msg.get("timestamp"))
            if not msg_dt or str(msg.get("sender_type") or "") != "customer":
                continue
            if msg_dt <= pivot_dt:
                previous_customer = msg
            elif msg_dt > pivot_dt and next_customer is None and (msg_dt - pivot_dt).total_seconds() <= 21600:
                next_customer = msg
        reply_samples.append(
            {
                "reply_id": f"reply-{event.get('id')}",
                "event_id": event.get("id"),
                "chat_id": chat_id,
                "event_type": event.get("event_type"),
                "sent_at_cairo": _serialize_dt(event.get("_dt")),
                "matched": bool(matched_msg),
                "reply_text": _trim_preview((matched_msg or {}).get("text") or ""),
                "customer_message": _trim_preview((previous_customer or {}).get("text") or ""),
                "next_customer_message": _trim_preview((next_customer or {}).get("text") or "", limit=180),
                "source": str(meta.get("source") or ""),
                "contact_name": str(meta.get("contact_name") or ""),
                "sender_identifier": str(meta.get("sender_identifier") or ""),
                "booking_number": str(meta.get("booking_number") or ""),
            }
        )

    total_session_minutes = sum(int(item.get("duration_minutes") or 0) for item in session_details)
    total_activity_events = sum(int(item.get("activity_events_count") or 0) for item in session_details)
    weighted_activity = round(sum(float(item.get("weighted_activity") or 0.0) for item in session_details), 2)
    total_human_replies = sum(int(item.get("human_replies") or 0) for item in session_details)
    total_template_replies = sum(int(item.get("template_replies") or 0) for item in session_details)
    total_replies_period = total_human_replies + total_ai_in_sessions
    human_share_pct = round((total_human_replies / total_replies_period) * 100, 1) if total_replies_period else 0.0
    ai_share_pct = round((total_ai_in_sessions / total_replies_period) * 100, 1) if total_replies_period else 0.0

    auto_logout_count = sum(1 for item in session_details if str(item.get("logout_type") or "") == "auto_logout")
    forced_midnight_count = sum(1 for item in session_details if str(item.get("logout_type") or "") == "forced_midnight")
    implicit_restart_count = sum(1 for item in session_details if str(item.get("logout_type") or "") == "implicit_restart")
    close_tab_count = sum(int(item.get("close_tab_count") or 0) for item in session_details)

    activity_breakdown = [
        {"label": "Replies", "value": total_human_replies},
        {"label": "Open Chat", "value": sum(int(item.get("open_chat_count") or 0) for item in session_details)},
        {"label": "Lead Actions", "value": sum(int(item.get("lead_actions_count") or 0) for item in session_details)},
        {"label": "Navigation", "value": sum(int(item.get("tab_switch_count") or 0) for item in session_details)},
        {"label": "Chat Actions", "value": sum(int(item.get("chat_actions_count") or 0) for item in session_details)},
        {"label": "Other", "value": sum(int(item.get("other_events_count") or 0) for item in session_details)},
    ]
    activity_breakdown = [item for item in activity_breakdown if int(item.get("value") or 0) > 0]

    for detail in session_details:
        detail.pop("_activity_events", None)
        detail.pop("_send_events", None)

    return {
        "user": {"user_id": user_id, "display_name": actor_label},
        "generated_at_cairo": _serialize_dt(_get_cairo_now()),
        "scope": "employee_session_day",
        "target_date": day_window["date"],
        "day_state": "open" if any(item.get("is_open") for item in session_details) else "closed",
        "filter": {"date": day_window["date"], "range_label": day_window["label"]},
        "period_window": {"start": _serialize_dt(day_start), "end": _serialize_dt(day_end)},
        "sessions": session_details,
        "summary": {
            "sessions_count": len(session_details),
            "total_session_minutes": total_session_minutes,
            "activity_events_count": total_activity_events,
            "weighted_activity": weighted_activity,
            "human_replies_period": total_human_replies,
            "template_replies_period": total_template_replies,
            "ai_replies_period": total_ai_in_sessions,
            "total_replies_period": total_replies_period,
            "human_share_pct": human_share_pct,
            "ai_share_pct": ai_share_pct,
            "auto_logout_count": auto_logout_count,
            "forced_midnight_count": forced_midnight_count,
            "implicit_restart_count": implicit_restart_count,
            "close_tab_count": close_tab_count,
            "session_starts_count": len(session_details),
            "is_open": any(item.get("is_open") for item in session_details),
        },
        "charts": {
            "period_timeline": period_timeline,
            "activity_breakdown": activity_breakdown,
        },
        "reply_samples": reply_samples,
    }

def get_setting(key, default_value=None):
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM user_settings WHERE key = ?", (key,))
        row = c.fetchone()
        return row[0] if row else default_value

def get_user_arabic_name(user_id, fallback_name=None):
    if not user_id:
        return fallback_name
    try:
        import json
        users_raw = get_setting('dashboard_users')
        if users_raw:
            users = json.loads(users_raw)
            for u in users:
                if str(u.get('id')) == str(user_id) or str(u.get('username')) == str(user_id):
                    # Prefer the 'name' field which usually contains the Arabic name
                    name = str(u.get('name') or u.get('username') or '').strip()
                    if name:
                        return name
    except Exception as e:
        import logging
        logging.warning(f"Error fetching user arabic name for {user_id}: {e}")
    return fallback_name

def set_setting(key, value):
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO user_settings (key, value, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
        ''', (key, value))
        conn.commit()

def _resolve_conversation_company_id(company_id=None, receiving_phone_id="", email_account_id=None):
    resolved = str(company_id or "").strip()
    if resolved:
        return resolved
    try:
        import company_tenancy
        if receiving_phone_id:
            return company_tenancy.lookup_company_id_for_phone(receiving_phone_id)
        if email_account_id:
            return company_tenancy.lookup_company_id_for_email_account(email_account_id)
        return company_tenancy.DEFAULT_COMPANY_ID
    except Exception:
        return DEFAULT_COMPANY_ID


def _company_channel_thread_id(source, thread_id, receiving_phone_id, company_id):
    """Give each non-FTS WhatsApp channel its own thread.

    The conversations unique key is (source, sender, thread_id) and does not
    include company_id. Without a company thread, the same phone is forced
    onto the existing FTS chat.
    """
    if str(source or "").strip().lower() != "whatsapp":
        source_l = str(source or "").strip().lower()
        incoming = str(thread_id or "")
        if incoming.startswith("co:"):
            return incoming
        try:
            import company_tenancy
            non_default = bool(company_id) and not company_tenancy.is_default_company(company_id)
        except Exception:
            non_default = bool(company_id) and str(company_id).strip().lower() not in ("", "fts")
        if not non_default:
            return incoming
        if source_l == "email":
            return f"co:{company_id}:email:{incoming or 'email'}"
        if source_l == "facebook":
            page = str(receiving_phone_id or "").strip() or "page"
            return f"co:{company_id}:fb:{page}"
        return incoming
    phone = str(receiving_phone_id or "").strip()
    try:
        import company_tenancy
        non_default = bool(company_id) and not company_tenancy.is_default_company(company_id)
    except Exception:
        non_default = bool(company_id) and str(company_id).strip().lower() not in ("", "fts")
    if not non_default and not phone.startswith("evo:"):
        return str(thread_id or "")
    channel = phone or "whatsapp"
    return f"co:{company_id}:{channel}"


def _merge_staff_inbox_location(existing_location, incoming_location):
    try:
        from chat_location import resolve_inbox_location
        return resolve_inbox_location(existing_location, incoming_location)
    except Exception:
        incoming = str(incoming_location or "").strip()
        current = str(existing_location or "").strip()
        return incoming or current or "Unknown"


def _persist_merged_inbox_location(c, conn, chat_id, existing_location, incoming_location):
    merged = _merge_staff_inbox_location(existing_location, incoming_location)
    existing = str(existing_location or "").strip()
    if merged and merged != existing:
        c.execute("UPDATE conversations SET location = ? WHERE chat_id = ?", (merged, chat_id))
        conn.commit()
    return merged


def classify_staff_conversation(chat_id, location, contact_name=None, unlink_customer=True):
    """Pin a WhatsApp thread to Guides/Drivers and drop customer-lead assignment."""
    chat_id = str(chat_id or "").strip()
    loc = str(location or "").strip()
    if not chat_id or loc not in ("Guides", "Drivers"):
        return False
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("PRAGMA table_info(conversations)")
        columns = [col[1] for col in c.fetchall()]
        c.execute("SELECT * FROM conversations WHERE chat_id = ?", (chat_id,))
        row = c.fetchone()
        if not row:
            return False
        c.execute("UPDATE conversations SET location = ? WHERE chat_id = ?", (loc, chat_id))
        name = str(contact_name or "").strip()
        if name:
            c.execute("UPDATE conversations SET contact_name = ? WHERE chat_id = ?", (name, chat_id))
        if "lead_owner_user_id" in columns:
            c.execute(
                """
                UPDATE conversations
                SET lead_owner_user_id = NULL,
                    lead_owner_name = NULL,
                    lead_owner_assigned_at = NULL
                WHERE chat_id = ?
                """,
                (chat_id,),
            )
        if "assigned_to" in columns:
            c.execute("UPDATE conversations SET assigned_to = NULL WHERE chat_id = ?", (chat_id,))
        if "sales_inbox" in columns:
            c.execute("UPDATE conversations SET sales_inbox = 0 WHERE chat_id = ?", (chat_id,))
        if unlink_customer:
            c.execute(
                """
                UPDATE conversations
                SET airtable_record_id = NULL,
                    booking_number = NULL
                WHERE chat_id = ?
                """,
                (chat_id,),
            )
        conn.commit()
    return True


def repair_guide_conversations_by_phone(phone_name_map):
    """Move known guide WhatsApp chats into the Guides inbox and clear employee Assign."""
    mapping = {}
    for raw_phone, raw_name in (phone_name_map or {}).items():
        digits = re.sub(r"\D", "", str(raw_phone or ""))
        if not digits:
            continue
        mapping[digits] = str(raw_name or "").strip()
    if not mapping:
        return []
    repaired = []
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            """
            SELECT chat_id, sender_identifier, contact_name, location,
                   lead_owner_name, lead_owner_user_id, airtable_record_id, booking_number
            FROM conversations
            WHERE LOWER(COALESCE(source, '')) = 'whatsapp'
              AND sender_identifier IS NOT NULL
              AND TRIM(sender_identifier) <> ''
            """
        )
        rows = c.fetchall() or []
    for row in rows:
        digits = re.sub(r"\D", "", str(row["sender_identifier"] or ""))
        matched_name = ""
        for phone_digits, guide_name in mapping.items():
            if not digits:
                continue
            if digits == phone_digits or digits.endswith(phone_digits[-9:]) or phone_digits.endswith(digits[-9:] if len(digits) >= 9 else digits):
                matched_name = guide_name
                break
        if not matched_name:
            continue
        display = matched_name if matched_name.lower().startswith("guide") else f"Guide - {matched_name}"
        ok = classify_staff_conversation(
            row["chat_id"],
            "Guides",
            contact_name=display,
            unlink_customer=True,
        )
        if ok:
            repaired.append({
                "chat_id": row["chat_id"],
                "sender_identifier": row["sender_identifier"],
                "from_location": row["location"],
                "from_owner": row["lead_owner_name"],
                "contact_name": display,
            })
    return repaired


def get_or_create_conversation(source, sender_identifier, contact_name="", airtable_record_id="", location="Unknown", thread_id="", receiving_phone_id="", sales_inbox=None, email_account_id=None, company_id=None):
    resolved_company_id = _resolve_conversation_company_id(company_id, receiving_phone_id, email_account_id)
    thread_id = _company_channel_thread_id(source, thread_id, receiving_phone_id, resolved_company_id)
    try:
        import company_tenancy
        if resolved_company_id and not company_tenancy.is_default_company(resolved_company_id):
            location = company_tenancy.company_customer_inbox_location(resolved_company_id, "")
    except Exception:
        pass
    company_channel_thread = str(thread_id or "").startswith("co:")
    company_scoped_whatsapp = (
        str(source or "").strip().lower() == "whatsapp" and company_channel_thread
    )
    if company_channel_thread:
        try:
            ensure_conversations_channel_unique()
        except Exception as uniq_err:
            logging.warning("Conversation channel unique migration skipped: %s", uniq_err)
    with _connect(30.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Ensure schema is up to date
        c.execute("PRAGMA table_info(conversations)")
        columns = [col[1] for col in c.fetchall()]
        if 'thread_id' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN thread_id TEXT")
        if 'auto_reply_hold_until' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN auto_reply_hold_until TIMESTAMP")
            conn.commit()
        if 'receiving_phone_id' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN receiving_phone_id TEXT")
            conn.commit()
        if 'booking_number' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN booking_number TEXT")
            conn.commit()
        if 'sales_inbox' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN sales_inbox INTEGER DEFAULT 0")
            conn.commit()
        if 'email_account_id' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN email_account_id TEXT")
            conn.commit()
        if 'auto_reply_hold_until' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN auto_reply_hold_until TIMESTAMP")
            conn.commit()
        if 'company_id' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN company_id TEXT DEFAULT 'fts'")
            try:
                c.execute("UPDATE conversations SET company_id = 'fts' WHERE company_id IS NULL OR TRIM(company_id) = ''")
            except Exception:
                pass
            conn.commit()
        
        # Clean sender identifier if it's a phone number (remove +, spaces, dashes)
        clean_identifier = sender_identifier
        normalized_email_identifier = ""
        if str(source or "").strip().lower() == "email":
            normalized_email_identifier = _normalize_email_identifier(sender_identifier)
            if normalized_email_identifier:
                clean_identifier = normalized_email_identifier
        
        # If airtable_record_id is provided, try to find the existing chat by that FIRST
        # This prevents duplicate chats when a user switches from Email to WhatsApp
        if airtable_record_id and not company_scoped_whatsapp:
            c.execute(
                f"""
                SELECT *
                FROM conversations
                WHERE airtable_record_id = ?
                  AND {_COMPANY_ID_SQL} = ?
                ORDER BY
                  CASE WHEN lower(source) = lower(?) THEN 0 ELSE 1 END,
                  CASE lower(source)
                    WHEN 'whatsapp' THEN 0
                    WHEN 'email' THEN 1
                    WHEN 'facebook' THEN 2
                    ELSE 3
                  END,
                  last_message_time DESC
                LIMIT 1
                """,
                (airtable_record_id, resolved_company_id, str(source or "")),
            )
            row = c.fetchone()
            if row:
                # Update info if provided
                if contact_name or location != "Unknown" or receiving_phone_id or sales_inbox or email_account_id:
                    c.execute("""
                        UPDATE conversations 
                        SET contact_name = COALESCE(NULLIF(?, ''), contact_name),
                            location = COALESCE(NULLIF(location, 'Unknown'), NULLIF(?, 'Unknown'), 'Unknown'),
                            receiving_phone_id = COALESCE(NULLIF(?, ''), receiving_phone_id),
                            sales_inbox = CASE WHEN ? THEN 1 ELSE COALESCE(sales_inbox, 0) END,
                            email_account_id = COALESCE(NULLIF(?, ''), email_account_id)
                        WHERE chat_id = ?
                    """, (contact_name, location, receiving_phone_id, 1 if sales_inbox else 0, email_account_id, row['chat_id']))
                    conn.commit()
                
                # Because the same Airtable Record might now have a NEW email (like the OTA one),
                # we do NOT blindly update the sender_identifier if it breaks the logic.
                # Actually, updating sender_identifier here causes the bug where a new email from OTA
                # overwrites the customer's real email in the local DB. Let's just return the row.
                _persist_merged_inbox_location(c, conn, row["chat_id"], row["location"], location)
                c.execute("SELECT * FROM conversations WHERE chat_id = ?", (row["chat_id"],))
                row = c.fetchone()
                return dict(row)

        if source == "Email" and thread_id:
            c.execute(
                f"SELECT * FROM conversations WHERE source = ? AND thread_id = ? AND {_COMPANY_ID_SQL} = ?",
                (source, thread_id, resolved_company_id),
            )
            row = c.fetchone()
            if not row:
                # Try finding it by sender identifier as a secondary check before giving up
                c.execute(
                    f"SELECT * FROM conversations WHERE source = ? AND sender_identifier = ? AND {_COMPANY_ID_SQL} = ?",
                    (source, clean_identifier, resolved_company_id),
                )
                row = c.fetchone()
            if not row and normalized_email_identifier:
                row = _find_email_conversation_by_normalized_identifier(c, normalized_email_identifier, resolved_company_id)
        elif company_scoped_whatsapp and sender_identifier:
            clean_identifier = str(sender_identifier).replace('+', '').replace(' ', '').replace('-', '')
            normalized_sender_expr = "REPLACE(REPLACE(REPLACE(sender_identifier, '+', ''), ' ', ''), '-', '')"
            c.execute(
                f"""
                SELECT *
                FROM conversations
                WHERE source = ?
                  AND {normalized_sender_expr} = ?
                  AND COALESCE(thread_id, '') = ?
                  AND {_COMPANY_ID_SQL} = ?
                ORDER BY last_message_time DESC
                LIMIT 1
                """,
                (source, clean_identifier, str(thread_id), resolved_company_id),
            )
            row = c.fetchone()
        elif source == "WhatsApp" and sender_identifier:
            clean_identifier = str(sender_identifier).replace('+', '').replace(' ', '').replace('-', '')
            normalized_sender_expr = "REPLACE(REPLACE(REPLACE(sender_identifier, '+', ''), ' ', ''), '-', '')"
            if str(receiving_phone_id or "").strip():
                c.execute(
                    f"""
                    SELECT *
                    FROM conversations
                    WHERE source = ?
                      AND {normalized_sender_expr} = ?
                      AND COALESCE(receiving_phone_id, '') = ?
                      AND (thread_id IS NULL OR thread_id = '')
                      AND {_COMPANY_ID_SQL} = ?
                    ORDER BY last_message_time DESC
                    LIMIT 1
                    """,
                    (source, clean_identifier, str(receiving_phone_id).strip(), resolved_company_id),
                )
                row = c.fetchone()
                if not row:
                    # Legacy fallback: only reuse an older WhatsApp chat if it was never pinned to a dedicated inbox number.
                    c.execute(
                        f"""
                        SELECT *
                        FROM conversations
                        WHERE source = ?
                          AND {normalized_sender_expr} = ?
                          AND COALESCE(receiving_phone_id, '') = ''
                          AND (thread_id IS NULL OR thread_id = '')
                          AND {_COMPANY_ID_SQL} = ?
                        ORDER BY last_message_time DESC
                        LIMIT 1
                        """,
                        (source, clean_identifier, resolved_company_id),
                    )
                    row = c.fetchone()
                if not row:
                    c.execute(
                        f"""
                        SELECT *
                        FROM conversations
                        WHERE source = ?
                          AND {normalized_sender_expr} = ?
                          AND (thread_id IS NULL OR thread_id = '')
                          AND {_COMPANY_ID_SQL} = ?
                        ORDER BY
                          CASE WHEN COALESCE(receiving_phone_id, '') = ? THEN 0 ELSE 1 END,
                          last_message_time DESC
                        LIMIT 1
                        """,
                        (source, clean_identifier, resolved_company_id, str(receiving_phone_id).strip()),
                    )
                    row = c.fetchone()
            else:
                c.execute(
                    f"""
                    SELECT *
                    FROM conversations
                    WHERE source = ?
                      AND {normalized_sender_expr} = ?
                      AND (thread_id IS NULL OR thread_id = '')
                      AND {_COMPANY_ID_SQL} = ?
                    ORDER BY last_message_time DESC
                    LIMIT 1
                    """,
                    (source, clean_identifier, resolved_company_id),
                )
                row = c.fetchone()
        else:
            # Fallback: if no thread_id or WhatsApp, search by sender_identifier
            c.execute(
                f"SELECT * FROM conversations WHERE source = ? AND sender_identifier = ? AND {_COMPANY_ID_SQL} = ?",
                (source, clean_identifier, resolved_company_id),
            )
            row = c.fetchone()
            if not row and normalized_email_identifier:
                row = _find_email_conversation_by_normalized_identifier(c, normalized_email_identifier, resolved_company_id)
        
        if row:
            # Update info if provided
            should_refresh_identifier = bool(
                normalized_email_identifier
                and str(row["sender_identifier"] or "").strip() != str(clean_identifier or "").strip()
            )
            if airtable_record_id or contact_name or location != "Unknown" or receiving_phone_id or sales_inbox or email_account_id or should_refresh_identifier:
                c.execute("""
                    UPDATE conversations 
                    SET contact_name = COALESCE(NULLIF(?, ''), contact_name),
                        airtable_record_id = COALESCE(NULLIF(?, ''), airtable_record_id),
                        location = COALESCE(NULLIF(location, 'Unknown'), NULLIF(?, 'Unknown'), 'Unknown'),
                        thread_id = COALESCE(NULLIF(?, ''), thread_id),
                        sender_identifier = COALESCE(NULLIF(?, ''), sender_identifier),
                        receiving_phone_id = COALESCE(NULLIF(?, ''), receiving_phone_id),
                        sales_inbox = CASE WHEN ? THEN 1 ELSE COALESCE(sales_inbox, 0) END,
                        email_account_id = COALESCE(NULLIF(?, ''), email_account_id)
                    WHERE chat_id = ?
                """, (contact_name, airtable_record_id, location, thread_id, clean_identifier, receiving_phone_id, 1 if sales_inbox else 0, email_account_id, row['chat_id']))
                conn.commit()
            if (
                company_scoped_whatsapp
                and str(row["company_id"] or "").strip() == str(resolved_company_id or "").strip()
                and str(location or "").strip()
                and str(location).strip().lower() not in ("unknown", "needhelp", "all")
            ):
                merged_loc = _merge_staff_inbox_location(row["location"], location)
                c.execute(
                    """
                    UPDATE conversations
                    SET location = ?,
                        receiving_phone_id = COALESCE(NULLIF(?, ''), receiving_phone_id)
                    WHERE chat_id = ?
                      AND COALESCE(NULLIF(company_id, ''), 'fts') = ?
                    """,
                    (merged_loc, receiving_phone_id, row["chat_id"], resolved_company_id),
                )
                conn.commit()
            _persist_merged_inbox_location(c, conn, row["chat_id"], row["location"], location)
            c.execute("SELECT * FROM conversations WHERE chat_id = ?", (row["chat_id"],))
            row = c.fetchone()
            return dict(row)
        else:
            chat_id = str(uuid.uuid4())
            now = get_cairo_time()
            try:
                c.execute("""
                    INSERT INTO conversations (chat_id, source, sender_identifier, contact_name, airtable_record_id, last_message_time, location, thread_id, receiving_phone_id, sales_inbox, email_account_id, company_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (chat_id, source, clean_identifier, contact_name, airtable_record_id, now, location, thread_id, receiving_phone_id, 1 if sales_inbox else 0, email_account_id, resolved_company_id))
                conn.commit()
                
                c.execute("SELECT * FROM conversations WHERE chat_id = ?", (chat_id,))
                return dict(c.fetchone())
            except sqlite3.IntegrityError:
                row = None
                normalized_sender_expr = "REPLACE(REPLACE(REPLACE(sender_identifier, '+', ''), ' ', ''), '-', '')"
                c.execute(
                    f"""
                    SELECT *
                    FROM conversations
                    WHERE lower(source) = lower(?)
                      AND {normalized_sender_expr} = ?
                    ORDER BY
                      CASE WHEN COALESCE(thread_id, '') = ? THEN 0 ELSE 1 END,
                      last_message_time DESC
                    LIMIT 1
                    """,
                    (source, clean_identifier, str(thread_id or "")),
                )
                row = c.fetchone()
                if company_scoped_whatsapp:
                    scoped = None
                    if row and str(row["thread_id"] or "") == str(thread_id or "") and (
                        str(row["company_id"] or "").strip() or DEFAULT_COMPANY_ID
                    ) == str(resolved_company_id or "").strip():
                        scoped = row
                    if scoped:
                        return dict(scoped)
                    raise
                if row:
                    return dict(row)
                if source == "Email" and thread_id:
                    c.execute(
                        f"SELECT * FROM conversations WHERE source = ? AND thread_id = ? AND {_COMPANY_ID_SQL} = ? ORDER BY last_message_time DESC LIMIT 1",
                        (source, thread_id, resolved_company_id),
                    )
                    row = c.fetchone()
                    if not row:
                        c.execute(
                            f"SELECT * FROM conversations WHERE source = ? AND sender_identifier = ? AND {_COMPANY_ID_SQL} = ? ORDER BY last_message_time DESC LIMIT 1",
                            (source, clean_identifier, resolved_company_id),
                        )
                        row = c.fetchone()
                elif source == "WhatsApp" and clean_identifier:
                    normalized_sender_expr = "REPLACE(REPLACE(REPLACE(sender_identifier, '+', ''), ' ', ''), '-', '')"
                    c.execute(
                        f"""
                        SELECT *
                        FROM conversations
                        WHERE source = ?
                          AND {normalized_sender_expr} = ?
                          AND (thread_id IS NULL OR thread_id = '')
                          AND {_COMPANY_ID_SQL} = ?
                        ORDER BY
                          CASE WHEN COALESCE(receiving_phone_id, '') = ? THEN 0 ELSE 1 END,
                          last_message_time DESC
                        LIMIT 1
                        """,
                        (source, clean_identifier, resolved_company_id, str(receiving_phone_id or "").strip()),
                    )
                    row = c.fetchone()
                else:
                    c.execute(
                        f"SELECT * FROM conversations WHERE source = ? AND sender_identifier = ? AND {_COMPANY_ID_SQL} = ? ORDER BY last_message_time DESC LIMIT 1",
                        (source, clean_identifier, resolved_company_id),
                    )
                    row = c.fetchone()

                if row:
                    if airtable_record_id or contact_name or location != "Unknown" or receiving_phone_id or sales_inbox or email_account_id:
                        c.execute("""
                            UPDATE conversations
                            SET contact_name = COALESCE(NULLIF(?, ''), contact_name),
                                airtable_record_id = COALESCE(NULLIF(?, ''), airtable_record_id),
                                location = COALESCE(NULLIF(location, 'Unknown'), NULLIF(?, 'Unknown'), 'Unknown'),
                                thread_id = COALESCE(NULLIF(?, ''), thread_id),
                                sender_identifier = COALESCE(NULLIF(?, ''), sender_identifier),
                                receiving_phone_id = COALESCE(NULLIF(?, ''), receiving_phone_id),
                                sales_inbox = CASE WHEN ? THEN 1 ELSE COALESCE(sales_inbox, 0) END,
                                email_account_id = COALESCE(NULLIF(?, ''), email_account_id)
                            WHERE chat_id = ?
                        """, (contact_name, airtable_record_id, location, thread_id, clean_identifier, receiving_phone_id, 1 if sales_inbox else 0, email_account_id, row['chat_id']))
                        conn.commit()
                        c.execute("SELECT * FROM conversations WHERE chat_id = ?", (row['chat_id'],))
                        row = c.fetchone()
                    _persist_merged_inbox_location(c, conn, row["chat_id"], row["location"], location)
                    c.execute("SELECT * FROM conversations WHERE chat_id = ?", (row["chat_id"],))
                    row = c.fetchone()
                    return dict(row)
                raise

def get_chat_by_record_id(record_id):
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            """
            SELECT *
            FROM conversations
            WHERE airtable_record_id = ?
            ORDER BY
              CASE lower(source)
                WHEN 'whatsapp' THEN 0
                WHEN 'email' THEN 1
                WHEN 'facebook' THEN 2
                ELSE 3
              END,
              last_message_time DESC
            LIMIT 1
            """,
            (record_id,),
        )
        row = c.fetchone()
        return dict(row) if row else None

def sync_conversation_locations_from_des(airtable_record_id, des):
    """
    Update inbox location for every chat linked to this Airtable record when des is set.
    Returns the number of conversations updated.
    """
    from chat_location import derive_chat_location_from_des, extract_des_from_fields, is_staff_inbox_location

    record_id = str(airtable_record_id or "").strip()
    if not record_id:
        return 0
    des_value = str(des or "").strip() if not isinstance(des, dict) else extract_des_from_fields(des)
    if not des_value:
        return 0

    new_location = derive_chat_location_from_des(des_value)
    updated = 0
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT chat_id, location
            FROM conversations
            WHERE airtable_record_id = ?
            """,
            (record_id,),
        )
        rows = c.fetchall() or []
        for chat_id, current_loc in rows:
            if is_staff_inbox_location(current_loc):
                continue
            if str(current_loc or "").strip() == new_location:
                continue
            c.execute(
                "UPDATE conversations SET location = ? WHERE chat_id = ?",
                (new_location, chat_id),
            )
            updated += 1
            logging.info(
                "Synced chat %s location %s -> %s from Airtable des=%r (record %s)",
                chat_id,
                current_loc,
                new_location,
                des_value,
                record_id,
            )
        if updated:
            conn.commit()
    return updated

def sync_conversation_locations_from_list_records(records):
    """Batch helper for Airtable mirror / backfill scripts."""
    total = 0
    for item in records or []:
        if not item:
            continue
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            record_id, fields = item[0], item[1]
        elif isinstance(item, dict):
            record_id = item.get("id") or item.get("airtable_id")
            fields = item.get("fields") or {}
        else:
            continue
        from chat_location import extract_des_from_fields

        total += sync_conversation_locations_from_des(record_id, extract_des_from_fields(fields))
    return total

def find_whatsapp_conversation_by_phone(phone):
    clean_phone = re.sub(r'\D', '', str(phone or ''))
    if not clean_phone:
        return None
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            """
            SELECT *
            FROM conversations
            WHERE lower(source) = 'whatsapp'
              AND REPLACE(REPLACE(REPLACE(sender_identifier, '+', ''), ' ', ''), '-', '') = ?
            ORDER BY last_message_time DESC
            LIMIT 1
            """,
            (clean_phone,),
        )
        row = c.fetchone()
        return dict(row) if row else None


def find_conversation_for_customer(company_id, airtable_record_id="", booking_number="", phone=""):
    """Return the existing company conversation for this customer, if one already exists."""
    company_key = str(company_id or DEFAULT_COMPANY_ID).strip() or DEFAULT_COMPANY_ID
    record_id = str(airtable_record_id or "").strip()
    booking = str(booking_number or "").strip()
    phone_digits = re.sub(r"\D", "", str(phone or ""))
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        def _one(sql, params):
            c.execute(sql, params)
            row = c.fetchone()
            return dict(row) if row else None

        base = f"IFNULL(is_deleted, 0) = 0 AND {_COMPANY_ID_SQL} = ?"
        if record_id:
            found = _one(
                f"""
                SELECT * FROM conversations
                WHERE airtable_record_id = ? AND {base}
                ORDER BY last_message_time DESC
                LIMIT 1
                """,
                (record_id, company_key),
            )
            if found:
                return found
        if booking:
            found = _one(
                f"""
                SELECT * FROM conversations
                WHERE LOWER(TRIM(COALESCE(booking_number, ''))) = LOWER(?) AND {base}
                ORDER BY last_message_time DESC
                LIMIT 1
                """,
                (booking, company_key),
            )
            if found:
                return found
        if len(phone_digits) >= 8:
            found = _one(
                f"""
                SELECT * FROM conversations
                WHERE REPLACE(REPLACE(REPLACE(sender_identifier, '+', ''), ' ', ''), '-', '') = ?
                  AND {base}
                ORDER BY last_message_time DESC
                LIMIT 1
                """,
                (phone_digits, company_key),
            )
            if found:
                return found
    return None

def find_whatsapp_phone_by_record_id(record_id):
    if not record_id:
        return None
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            """
            SELECT sender_identifier
            FROM conversations
            WHERE airtable_record_id = ?
              AND (
                lower(source) = 'whatsapp'
                OR sender_identifier GLOB '+[0-9]*'
                OR sender_identifier GLOB '[0-9]*'
              )
            ORDER BY last_message_time DESC
            LIMIT 1
            """,
            (record_id,),
        )
        row = c.fetchone()
        if not row:
            return None
        return str(row["sender_identifier"] or "").strip() or None

def get_last_customer_whatsapp_message_time(record_id):
    if not record_id:
        return None
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            """
            SELECT m.timestamp
            FROM messages m
            JOIN conversations c2 ON c2.chat_id = m.chat_id
            WHERE c2.airtable_record_id = ?
              AND lower(c2.source) = 'whatsapp'
              AND m.sender_type = 'customer'
            ORDER BY m.timestamp DESC
            LIMIT 1
            """,
            (record_id,),
        )
        row = c.fetchone()
        if not row:
            return None
        return row["timestamp"]

def get_last_customer_message_time(chat_id):
    if not chat_id:
        return None
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            """
            SELECT timestamp
            FROM messages
            WHERE chat_id = ?
              AND sender_type = 'customer'
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (chat_id,),
        )
        row = c.fetchone()
        if not row:
            return None
        return row["timestamp"]

def get_last_customer_message(chat_id):
    if not chat_id:
        return None
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            """
            SELECT text, timestamp
            FROM messages
            WHERE chat_id = ?
              AND sender_type = 'customer'
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (chat_id,),
        )
        row = c.fetchone()
        if not row:
            return None
        return {"text": row["text"], "timestamp": row["timestamp"]}

def get_last_agent_message_time(chat_id):
    if not chat_id:
        return None
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            """
            SELECT timestamp
            FROM messages
            WHERE chat_id = ?
              AND sender_type IN ('agent', 'ai')
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (chat_id,),
        )
        row = c.fetchone()
        if not row:
            return None
        return row["timestamp"]

def touch_conversation_by_record_id(record_id):
    """Updates the last_message_time of a conversation without adding a new message."""
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        now = get_cairo_time()
        c.execute("""
            UPDATE conversations 
            SET last_message_time = ?
            WHERE airtable_record_id = ?
        """, (now, record_id))
        conn.commit()

def get_conversation_info(chat_id):
    if not chat_id:
        return None
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM conversations WHERE chat_id = ?", (chat_id,))
        row = c.fetchone()
        return dict(row) if row else None

def get_conversation(chat_id):
    return get_conversation_info(chat_id)

def find_conversations_by_booking_number(booking_number, limit=20):
    bn = str(booking_number or "").strip()
    if not bn:
        return []
    lim = int(limit or 20)
    if lim < 1:
        lim = 1
    if lim > 200:
        lim = 200
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute(
                """
                SELECT *
                FROM conversations
                WHERE booking_number = ?
                ORDER BY last_message_time DESC
                LIMIT ?
                """,
                (bn, lim),
            )
            return [dict(r) for r in c.fetchall()]
        except sqlite3.OperationalError:
            return []

def touch_conversation_last_message_time(chat_id):
    """Move a conversation to the top of the inbox after it is created from the dashboard."""
    chat_id = str(chat_id or "").strip()
    if not chat_id:
        return
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.execute(
            "UPDATE conversations SET last_message_time = ? WHERE chat_id = ?",
            (get_cairo_time(), chat_id),
        )
        conn.commit()


def update_conversation_info(
    chat_id,
    contact_name=None,
    airtable_record_id=None,
    location=None,
    needs_help=None,
    booking_number=None,
    sales_inbox=None,
    last_customer_channel=None,
    quality_from_location=None,
    email_account_id=None,
    facebook_ad_source=None,
    facebook_ad_type=None,
    facebook_ad_id=None,
    facebook_ad_ref=None,
    facebook_ad_title=None,
    facebook_post_id=None,
    facebook_ad_media_url=None,
    customer_phone=None,
):
    """Updates conversation info safely."""
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        
        # Ensure booking_number column exists
        c.execute("PRAGMA table_info(conversations)")
        columns = [col[1] for col in c.fetchall()]
        if 'booking_number' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN booking_number TEXT")
            conn.commit()
        if 'email_account_id' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN email_account_id TEXT")
            conn.commit()
        if 'facebook_ad_source' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN facebook_ad_source TEXT")
            conn.commit()
        if 'facebook_ad_type' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN facebook_ad_type TEXT")
            conn.commit()
        if 'facebook_ad_id' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN facebook_ad_id TEXT")
            conn.commit()
        if 'facebook_ad_ref' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN facebook_ad_ref TEXT")
            conn.commit()
        if 'facebook_ad_title' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN facebook_ad_title TEXT")
            conn.commit()
        if 'facebook_post_id' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN facebook_post_id TEXT")
            conn.commit()
        if 'facebook_ad_media_url' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN facebook_ad_media_url TEXT")
            conn.commit()
            
        if contact_name is not None:
            c.execute("UPDATE conversations SET contact_name = ? WHERE chat_id = ?", (contact_name, chat_id))
        if airtable_record_id is not None:
            c.execute("UPDATE conversations SET airtable_record_id = ? WHERE chat_id = ?", (airtable_record_id, chat_id))
        if location is not None:
            c.execute("UPDATE conversations SET location = ? WHERE chat_id = ?", (location, chat_id))
            # Religious chats must never linger in the Sales inbox via sales_inbox=1.
            # (Sales filter historically matched sales_inbox OR location=Sales.)
            if str(location).strip() == "Religious" and sales_inbox is None:
                c.execute("PRAGMA table_info(conversations)")
                _cols = [col[1] for col in c.fetchall()]
                if "sales_inbox" not in _cols:
                    c.execute("ALTER TABLE conversations ADD COLUMN sales_inbox INTEGER DEFAULT 0")
                c.execute("UPDATE conversations SET sales_inbox = 0 WHERE chat_id = ?", (chat_id,))
        if booking_number is not None:
            c.execute("UPDATE conversations SET booking_number = ? WHERE chat_id = ?", (booking_number, chat_id))
        if email_account_id is not None:
            c.execute("UPDATE conversations SET email_account_id = ? WHERE chat_id = ?", (str(email_account_id or "").strip() or None, chat_id))
        if facebook_ad_source is not None:
            c.execute("UPDATE conversations SET facebook_ad_source = ? WHERE chat_id = ?", (str(facebook_ad_source or "").strip() or None, chat_id))
        if facebook_ad_type is not None:
            c.execute("UPDATE conversations SET facebook_ad_type = ? WHERE chat_id = ?", (str(facebook_ad_type or "").strip() or None, chat_id))
        if facebook_ad_id is not None:
            c.execute("UPDATE conversations SET facebook_ad_id = ? WHERE chat_id = ?", (str(facebook_ad_id or "").strip() or None, chat_id))
        if facebook_ad_ref is not None:
            c.execute("UPDATE conversations SET facebook_ad_ref = ? WHERE chat_id = ?", (str(facebook_ad_ref or "").strip() or None, chat_id))
        if facebook_ad_title is not None:
            c.execute("UPDATE conversations SET facebook_ad_title = ? WHERE chat_id = ?", (str(facebook_ad_title or "").strip() or None, chat_id))
        if facebook_post_id is not None:
            c.execute("UPDATE conversations SET facebook_post_id = ? WHERE chat_id = ?", (str(facebook_post_id or "").strip() or None, chat_id))
        if facebook_ad_media_url is not None:
            c.execute("UPDATE conversations SET facebook_ad_media_url = ? WHERE chat_id = ?", (str(facebook_ad_media_url or "").strip() or None, chat_id))
        if customer_phone is not None:
            c.execute("UPDATE conversations SET customer_phone = ? WHERE chat_id = ?", (str(customer_phone or "").strip() or None, chat_id))
        if sales_inbox is not None:
            c.execute("PRAGMA table_info(conversations)")
            columns = [col[1] for col in c.fetchall()]
            if 'sales_inbox' not in columns:
                c.execute("ALTER TABLE conversations ADD COLUMN sales_inbox INTEGER DEFAULT 0")
            c.execute("UPDATE conversations SET sales_inbox = ? WHERE chat_id = ?", (1 if sales_inbox else 0, chat_id))
        if last_customer_channel is not None:
            c.execute("PRAGMA table_info(conversations)")
            columns = [col[1] for col in c.fetchall()]
            if 'last_customer_channel' not in columns:
                c.execute("ALTER TABLE conversations ADD COLUMN last_customer_channel TEXT")
            c.execute("UPDATE conversations SET last_customer_channel = ? WHERE chat_id = ?", (str(last_customer_channel), chat_id))
        if 'auto_reply_hold_until' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN auto_reply_hold_until TIMESTAMP")
        if quality_from_location is not None:
            c.execute("PRAGMA table_info(conversations)")
            columns = [col[1] for col in c.fetchall()]
            if 'quality_from_location' not in columns:
                c.execute("ALTER TABLE conversations ADD COLUMN quality_from_location TEXT")
            qfl = str(quality_from_location or "").strip()
            c.execute("UPDATE conversations SET quality_from_location = ? WHERE chat_id = ?", (qfl if qfl else None, chat_id))
        if needs_help is not None:
            # First check if the column exists
            c.execute("PRAGMA table_info(conversations)")
            columns = [col[1] for col in c.fetchall()]
            if 'needs_help' not in columns:
                c.execute("ALTER TABLE conversations ADD COLUMN needs_help INTEGER DEFAULT 0")
            c.execute("UPDATE conversations SET needs_help = ? WHERE chat_id = ?", (1 if needs_help else 0, chat_id))
        conn.commit()

def update_auto_reply_hold_until(chat_id, hold_until_iso):
    if not chat_id:
        return
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(conversations)")
        columns = [col[1] for col in c.fetchall()]
        if 'auto_reply_hold_until' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN auto_reply_hold_until TIMESTAMP")
            conn.commit()
        c.execute("UPDATE conversations SET auto_reply_hold_until = ? WHERE chat_id = ?", (hold_until_iso, chat_id))
        conn.commit()

def update_conversation_routing(chat_id, location=None, receiving_phone_id=None):
    if not chat_id:
        return
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(conversations)")
        columns = [col[1] for col in c.fetchall()]
        if 'receiving_phone_id' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN receiving_phone_id TEXT")
            conn.commit()
        if location is not None:
            c.execute("SELECT location FROM conversations WHERE chat_id = ?", (chat_id,))
            current_row = c.fetchone()
            current_loc = current_row[0] if current_row else ""
            merged_loc = _merge_staff_inbox_location(current_loc, location)
            c.execute("UPDATE conversations SET location = ? WHERE chat_id = ?", (merged_loc, chat_id))
        if receiving_phone_id is not None:
            c.execute("UPDATE conversations SET receiving_phone_id = ? WHERE chat_id = ?", (receiving_phone_id, chat_id))
        conn.commit()

def mark_conversation_read(chat_id, at_time=None):
    if not chat_id:
        return
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(conversations)")
        columns = [col[1] for col in c.fetchall()]
        if 'force_read_at' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN force_read_at TIMESTAMP")
            conn.commit()
        if at_time is None:
            at_time = get_cairo_time()
        c.execute("UPDATE conversations SET force_read_at = ?, unread_count = 0 WHERE chat_id = ?", (at_time, chat_id))
        conn.commit()

def _ensure_customer_note_columns(conn):
    c = conn.cursor()
    c.execute("PRAGMA table_info(conversations)")
    columns = [col[1] for col in c.fetchall()]
    if 'customer_note' not in columns:
        c.execute("ALTER TABLE conversations ADD COLUMN customer_note TEXT")
    if 'customer_note_updated_at' not in columns:
        c.execute("ALTER TABLE conversations ADD COLUMN customer_note_updated_at TIMESTAMP")
    if 'customer_note_updated_by' not in columns:
        c.execute("ALTER TABLE conversations ADD COLUMN customer_note_updated_by TEXT")
    if 'customer_note_owner_user_id' not in columns:
        c.execute("ALTER TABLE conversations ADD COLUMN customer_note_owner_user_id TEXT")
    conn.commit()

def get_customer_note(chat_id):
    chat_id = str(chat_id or "").strip()
    if not chat_id:
        return None
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_customer_note_columns(conn)
        c = conn.cursor()
        c.execute(
            """
            SELECT chat_id, customer_note, customer_note_updated_at, customer_note_updated_by, customer_note_owner_user_id
            FROM conversations
            WHERE chat_id = ?
            LIMIT 1
            """,
            (chat_id,),
        )
        row = c.fetchone()
        if not row:
            return None
        return dict(row)

def can_edit_customer_note(row, actor_user_id=None, is_admin=False):
    """Only the note owner or an Admin may edit/delete an existing note."""
    if is_admin:
        return True
    note_text = str((row or {}).get("customer_note") or "").strip()
    if not note_text:
        # Empty note: any viewer of the chat may create the first note.
        return True
    owner_id = str((row or {}).get("customer_note_owner_user_id") or "").strip().lower()
    actor_id = str(actor_user_id or "").strip().lower()
    if owner_id and actor_id and owner_id == actor_id:
        return True
    # Legacy fallback: older notes only stored display name in updated_by.
    if not owner_id:
        legacy = str((row or {}).get("customer_note_updated_by") or "").strip().lower()
        if legacy and actor_id and legacy == actor_id:
            return True
    return False

def set_customer_note(chat_id, note, updated_by=None, owner_user_id=None, is_admin=False, actor_user_id=None):
    """
    Shared customer note visible to all users who can see the conversation.
    Pass note="" to clear.
    Edit/clear is allowed only for the original owner or Admin.
    """
    chat_id = str(chat_id or "").strip()
    if not chat_id:
        return {"ok": False, "error": "missing_chat_id"}
    note_text = str(note or "").strip()
    display_name = str(updated_by or "").strip() or None
    owner_id = str(owner_user_id or actor_user_id or "").strip() or None
    actor_id = str(actor_user_id or owner_user_id or "").strip() or None
    now = get_cairo_time()
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_customer_note_columns(conn)
        c = conn.cursor()
        c.execute(
            """
            SELECT chat_id, customer_note, customer_note_updated_at, customer_note_updated_by, customer_note_owner_user_id
            FROM conversations
            WHERE chat_id = ?
            LIMIT 1
            """,
            (chat_id,),
        )
        row = c.fetchone()
        if not row:
            return {"ok": False, "error": "chat_not_found"}
        current = dict(row)
        if not can_edit_customer_note(current, actor_user_id=actor_id, is_admin=bool(is_admin)):
            return {"ok": False, "error": "forbidden_not_owner"}

        # Keep original owner when an Admin edits someone else's note.
        existing_owner = str(current.get("customer_note_owner_user_id") or "").strip() or None
        existing_note = str(current.get("customer_note") or "").strip()
        if note_text:
            final_owner = existing_owner if (existing_note and existing_owner) else owner_id
            final_display = display_name or final_owner
        else:
            final_owner = None
            final_display = None

        c.execute(
            """
            UPDATE conversations
            SET customer_note = ?,
                customer_note_updated_at = ?,
                customer_note_updated_by = ?,
                customer_note_owner_user_id = ?
            WHERE chat_id = ?
            """,
            (
                note_text or None,
                now if note_text else None,
                final_display if note_text else None,
                final_owner if note_text else None,
                chat_id,
            ),
        )
        conn.commit()
    return {
        "ok": True,
        "chat_id": chat_id,
        "customer_note": note_text or "",
        "customer_note_updated_at": now if note_text else None,
        "customer_note_updated_by": final_display if note_text else None,
        "customer_note_owner_user_id": final_owner if note_text else None,
    }

def get_message_id_by_external_id(chat_id, external_message_id):
    chat_id = str(chat_id or "").strip()
    ext = str(external_message_id or "").strip()
    if not chat_id or not ext:
        return None
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        try:
            c.execute("SELECT msg_id FROM messages WHERE chat_id = ? AND external_message_id = ? LIMIT 1", (chat_id, ext))
            row = c.fetchone()
            return row[0] if row else None
        except sqlite3.OperationalError:
            return None

def add_message(chat_id, sender_type, text, status='sent', increment_unread=True, source=None, external_message_id=None, reaction_to_external_message_id=None, reaction_emoji=None, error_message=None):
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        msg_id = str(uuid.uuid4())
        now = get_cairo_time()
        text_s = str(text or "")
        is_proposed_draft = text_s.startswith('[PROPOSED_DRAFT]')

        c.execute("PRAGMA table_info(messages)")
        msg_columns = [col[1] for col in c.fetchall()]
        if 'source' not in msg_columns:
            c.execute("ALTER TABLE messages ADD COLUMN source TEXT")
            conn.commit()
        if 'external_message_id' not in msg_columns:
            c.execute("ALTER TABLE messages ADD COLUMN external_message_id TEXT")
            conn.commit()
        if 'reaction_to_external_message_id' not in msg_columns:
            c.execute("ALTER TABLE messages ADD COLUMN reaction_to_external_message_id TEXT")
            conn.commit()
        if 'reaction_emoji' not in msg_columns:
            c.execute("ALTER TABLE messages ADD COLUMN reaction_emoji TEXT")
            conn.commit()
        if 'error_message' not in msg_columns:
            c.execute("ALTER TABLE messages ADD COLUMN error_message TEXT")
            conn.commit()
            msg_columns.append('error_message')
            
        if external_message_id:
            c.execute("SELECT msg_id FROM messages WHERE external_message_id = ?", (str(external_message_id),))
            if c.fetchone():
                # Message with this external_message_id already exists, don't duplicate
                return None

        # Safety net: never insert a PROPOSED_DRAFT after a live workflow/agent reply
        # already covers the latest real customer turn (prevents unread draft spam).
        # Ignore Facebook Ad Referral metadata rows — they are not customer turns.
        if is_proposed_draft:
            c.execute(
                """
                SELECT timestamp
                FROM messages
                WHERE chat_id = ?
                  AND sender_type = 'customer'
                  AND IFNULL(text, '') NOT LIKE '[Facebook Ad Referral]%'
                  AND IFNULL(text, '') NOT LIKE '[Facebook Referral]%'
                ORDER BY timestamp DESC, rowid DESC
                LIMIT 1
                """,
                (chat_id,),
            )
            last_customer = c.fetchone()
            if last_customer:
                c.execute(
                    """
                    SELECT 1
                    FROM messages
                    WHERE chat_id = ?
                      AND sender_type IN ('agent', 'ai', 'system')
                      AND IFNULL(text, '') NOT LIKE '[PROPOSED_DRAFT]%'
                      AND timestamp >= ?
                    LIMIT 1
                    """,
                    (chat_id, last_customer[0]),
                )
                if c.fetchone():
                    return None
        
        err_s = str(error_message).strip() if error_message is not None and str(error_message).strip() else None
        c.execute("""
            INSERT INTO messages (
                msg_id, chat_id, sender_type, text, timestamp, status, source,
                external_message_id, reaction_to_external_message_id, reaction_emoji, error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            msg_id, chat_id, sender_type, text_s, now, status, str(source) if source is not None else None,
            str(external_message_id) if external_message_id is not None else None,
            str(reaction_to_external_message_id) if reaction_to_external_message_id is not None else None,
            str(reaction_emoji) if reaction_emoji is not None else None,
            err_s,
        ))
        
        # Update conversation last message time
        # Proposed drafts must not reshuffle inbox ordering after a live workflow/agent reply.
        # Failed sends stay visible in-thread but should not look like a successful outbound.
        if (not is_proposed_draft) and str(status or '').strip().lower() != 'error':
            c.execute("""
                UPDATE conversations 
                SET last_message_time = ?
                WHERE chat_id = ?
            """, (now, chat_id))
        elif is_proposed_draft:
            # Keep draft timestamp for message ordering in-thread, but only bump
            # conversation last_message_time when no real agent reply covers this turn.
            c.execute(
                """
                SELECT timestamp
                FROM messages
                WHERE chat_id = ?
                  AND sender_type = 'customer'
                  AND IFNULL(text, '') NOT LIKE '[Facebook Ad Referral]%'
                  AND IFNULL(text, '') NOT LIKE '[Facebook Referral]%'
                ORDER BY timestamp DESC, rowid DESC
                LIMIT 1
                """,
                (chat_id,),
            )
            last_customer = c.fetchone()
            has_live_reply = False
            if last_customer:
                c.execute(
                    """
                    SELECT 1
                    FROM messages
                    WHERE chat_id = ?
                      AND sender_type IN ('agent', 'ai', 'system')
                      AND IFNULL(text, '') NOT LIKE '[PROPOSED_DRAFT]%'
                      AND timestamp >= ?
                    LIMIT 1
                    """,
                    (chat_id, last_customer[0]),
                )
                has_live_reply = c.fetchone() is not None
            if not has_live_reply:
                c.execute("""
                    UPDATE conversations 
                    SET last_message_time = ?
                    WHERE chat_id = ?
                """, (now, chat_id))
        
        # Increment unread if it's from a real customer message (not Ad Referral metadata)
        if (
            sender_type == 'customer'
            and increment_unread
            and not is_facebook_referral_metadata_text(text_s)
        ):
            c.execute("""
                UPDATE conversations 
                SET unread_count = unread_count + 1
                WHERE chat_id = ?
            """, (chat_id,))

        # Reset unread_count on real assistant/agent replies (all locations).
        # System logs and proposed drafts must not clear unread.
        if (
            sender_type in ('ai', 'agent', 'system')
            and not is_proposed_draft
            and not text_s.startswith('[System Log]')
        ):
            c.execute("""
                UPDATE conversations 
                SET unread_count = 0
                WHERE chat_id = ?
            """, (chat_id,))

        if sender_type == 'customer':
            try:
                _sales_update_on_inbound_message(conn, chat_id=chat_id, text=text_s, now=now)
            except Exception:
                pass
            
        conn.commit()
        return msg_id

def update_message_status_by_external_id(external_message_id, status):
    ext = str(external_message_id or "").strip()
    if not ext:
        return False
    st = str(status or "").strip()
    if not st:
        return False
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute("UPDATE messages SET status = ? WHERE external_message_id = ?", (st, ext))
        conn.commit()
        return c.rowcount > 0

def update_message_text(msg_id, text):
    mid = str(msg_id or "").strip()
    if not mid:
        return False
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute("UPDATE messages SET text = ? WHERE msg_id = ?", (str(text or ""), mid))
        conn.commit()
        return c.rowcount > 0

def _sales_update_on_inbound_message(conn, chat_id, text, now):
    if not chat_id:
        return
    score_delta, reasons = _sales_score_delta_from_text(text)
    try:
        c = conn.cursor()
        c.execute("SELECT lead_score FROM sales_customer_state WHERE chat_id = ?", (chat_id,))
        row = c.fetchone()
        current_score = None
        if row:
            try:
                current_score = int(row[0]) if row[0] is not None else None
            except Exception:
                current_score = None
        if current_score is None:
            current_score = 0
        new_score = current_score + int(score_delta or 0)
        if new_score < 0:
            new_score = 0
        if new_score > 100:
            new_score = 100

        c.execute(
            """
            INSERT INTO sales_customer_state (
                chat_id, lead_score, last_contact_date, needs_ai_review, updated_at, created_at
            )
            VALUES (?, ?, ?, 1, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                lead_score = COALESCE(excluded.lead_score, sales_customer_state.lead_score),
                last_contact_date = excluded.last_contact_date,
                needs_ai_review = 1,
                updated_at = excluded.updated_at
            """,
            (chat_id, int(new_score), str(now), str(now), str(now)),
        )
    except sqlite3.OperationalError:
        return

def _sales_score_delta_from_text(text):
    t = str(text or "").strip()
    if not t:
        return 0, []
    low = t.lower()
    import re
    delta = 0
    reasons = []

    def has_any(subs):
        return any(s in low for s in subs)

    if has_any(["price", "cost", "سعر", "كام", "كم السعر", "تكلفة", "بكام", "الاسعار", "الأسعار"]):
        delta += 20
        reasons.append("price_request")
    if has_any(["details", "itinerary", "تفاصيل", "برنامج", "schedule", "جدول", "route"]):
        delta += 20
        reasons.append("trip_details_request")
    if has_any(["quote", "quotation", "offer", "عرض", "سعر نهائي", "proposal"]):
        delta += 25
        reasons.append("offer_request")
    if has_any(["travel date", "تاريخ السفر", "تاريخ", "موعد", "date of travel"]):
        delta += 15
        reasons.append("travel_date_shared")
    if re.search(r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b", low):
        delta += 10
        reasons.append("date_pattern")
    if has_any(["hotel", "فندق", "location", "مكان", "sharm", "hurghada", "cairo", "الغردقة", "القاهرة", "شرم"]):
        delta += 10
        reasons.append("hotel_or_location")
    if has_any(["whatsapp", "واتساب", "call", "مكالمة", "اتصال", "phone", "رقمك", "كلم"]):
        delta += 20
        reasons.append("call_or_whatsapp")
    if has_any(["interested", "i want", "confirm", "ready", "book", "حجز", "عايز", "موافق", "أكيد", "تمام"]):
        delta += 25
        reasons.append("confirmed_interest")
    if has_any(["expensive", "too much", "غالي", "سعر عالي", "overpriced"]):
        delta -= 10
        reasons.append("price_objection")
    if has_any(["not interested", "no thanks", "مش مهتم", "مش عايز", "مش عاوز", "لا اريد", "cancel", "الغاء"]):
        delta -= 30
        reasons.append("not_interested")

    return delta, reasons

def linked_conversation_ids(chat_id):
    """This chat plus siblings that share the same booking record and company."""
    chat_id = str(chat_id or "").strip()
    if not chat_id:
        return []
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT airtable_record_id, company_id FROM conversations WHERE chat_id = ?",
            (chat_id,),
        )
        row = c.fetchone()
        if not row:
            return [chat_id]
        record_id = str(row[0] or "").strip()
        company_id = str(row[1] or "").strip() or "fts"
        if not record_id:
            return [chat_id]
        c.execute(
            """
            SELECT chat_id
            FROM conversations
            WHERE airtable_record_id = ?
              AND COALESCE(NULLIF(company_id, ''), 'fts') = ?
            """,
            (record_id, company_id),
        )
        ids = [str(item[0]) for item in c.fetchall() if item and item[0]]
        if chat_id not in ids:
            ids.append(chat_id)
        return ids or [chat_id]


def delete_proposed_drafts_for_conversation(chat_id):
    """Hide review drafts on this chat and on grouped chats of the same booking."""
    for linked_id in linked_conversation_ids(chat_id):
        delete_proposed_drafts(linked_id)


def delete_proposed_drafts(chat_id):
    """Deletes all [PROPOSED_DRAFT] messages for a specific chat to avoid UI clutter."""
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM messages WHERE chat_id = ? AND text LIKE '[PROPOSED_DRAFT]%'", (chat_id,))
        # Restore conversation ordering to the latest non-draft message after cleanup.
        c.execute(
            """
            SELECT MAX(timestamp)
            FROM messages
            WHERE chat_id = ?
              AND IFNULL(text, '') NOT LIKE '[PROPOSED_DRAFT]%'
            """,
            (chat_id,),
        )
        row = c.fetchone()
        latest_ts = row[0] if row else None
        if latest_ts:
            c.execute(
                "UPDATE conversations SET last_message_time = ? WHERE chat_id = ?",
                (latest_ts, chat_id),
            )
        conn.commit()

def is_facebook_referral_metadata_text(text):
    """True for system-only Facebook Ad/Referral notice rows (not real customer text)."""
    t = str(text or "").strip()
    if not t:
        return False
    return (
        t.startswith("[Facebook Ad Referral]")
        or t.startswith("[Facebook Referral]")
    )


def ensure_unread_for_pending_draft(chat_id):
    """
    Keep Religious/draft chats visible in Unread while a [PROPOSED_DRAFT] awaits human review.
    Clears force_read_at that would otherwise hide the customer's unanswered turn.
    """
    chat_id = str(chat_id or "").strip()
    if not chat_id:
        return False
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT 1
            FROM messages
            WHERE chat_id = ?
              AND IFNULL(text, '') LIKE '[PROPOSED_DRAFT]%'
            ORDER BY timestamp DESC, rowid DESC
            LIMIT 1
            """,
            (chat_id,),
        )
        if not c.fetchone():
            return False
        # Do not treat the draft insert time as "already read".
        c.execute(
            """
            UPDATE conversations
            SET force_read_at = NULL,
                unread_count = CASE WHEN IFNULL(unread_count, 0) < 1 THEN 1 ELSE unread_count END
            WHERE chat_id = ?
            """,
            (chat_id,),
        )
        conn.commit()
        return True


def has_pending_proposed_draft_for_review(chat_id):
    """
    True when a PROPOSED_DRAFT exists for the latest real customer turn
    and no live (non-draft) agent reply covers that turn yet.
    """
    chat_id = str(chat_id or "").strip()
    if not chat_id:
        return False
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT timestamp
            FROM messages
            WHERE chat_id = ?
              AND sender_type = 'customer'
              AND IFNULL(text, '') NOT LIKE '[Facebook Ad Referral]%'
              AND IFNULL(text, '') NOT LIKE '[Facebook Referral]%'
            ORDER BY timestamp DESC, rowid DESC
            LIMIT 1
            """,
            (chat_id,),
        )
        last_customer = c.fetchone()
        if not last_customer:
            return False
        last_customer_ts = last_customer[0]
        c.execute(
            """
            SELECT 1
            FROM messages
            WHERE chat_id = ?
              AND sender_type IN ('agent', 'ai', 'system')
              AND IFNULL(text, '') NOT LIKE '[PROPOSED_DRAFT]%'
              AND timestamp >= ?
            LIMIT 1
            """,
            (chat_id, last_customer_ts),
        )
        if c.fetchone():
            return False
        c.execute(
            """
            SELECT 1
            FROM messages
            WHERE chat_id = ?
              AND IFNULL(text, '') LIKE '[PROPOSED_DRAFT]%'
              AND timestamp >= ?
            LIMIT 1
            """,
            (chat_id, last_customer_ts),
        )
        return c.fetchone() is not None


def has_real_agent_reply_after_last_customer(chat_id):
    """
    True when a non-draft agent/ai/system message exists at or after the last
    real customer message. Used to suppress late [PROPOSED_DRAFT] inserts after a
    workflow/human/echo already replied to the current customer turn.

    Facebook Ad Referral notices are ignored — they are metadata cards, not turns
    that should reopen AI drafting / unread after a live workflow reply.
    """
    chat_id = str(chat_id or "").strip()
    if not chat_id:
        return False
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT timestamp, text
            FROM messages
            WHERE chat_id = ?
              AND sender_type = 'customer'
              AND IFNULL(text, '') NOT LIKE '[Facebook Ad Referral]%'
              AND IFNULL(text, '') NOT LIKE '[Facebook Referral]%'
            ORDER BY timestamp DESC, rowid DESC
            LIMIT 1
            """,
            (chat_id,),
        )
        last_customer = c.fetchone()
        if not last_customer:
            # No real customer message: fall back to "last message is real agent"
            c.execute(
                """
                SELECT sender_type, text
                FROM messages
                WHERE chat_id = ?
                ORDER BY timestamp DESC, rowid DESC
                LIMIT 1
                """,
                (chat_id,),
            )
            row = c.fetchone()
            if row:
                sender_type, text = row
                if sender_type in ('agent', 'ai', 'system') and '[PROPOSED_DRAFT]' not in str(text or ""):
                    return True
            return False

        last_customer_ts = last_customer[0]
        c.execute(
            """
            SELECT 1
            FROM messages
            WHERE chat_id = ?
              AND sender_type IN ('agent', 'ai', 'system')
              AND IFNULL(text, '') NOT LIKE '[PROPOSED_DRAFT]%'
              AND timestamp >= ?
            ORDER BY timestamp DESC, rowid DESC
            LIMIT 1
            """,
            (chat_id, last_customer_ts),
        )
        return c.fetchone() is not None

def check_if_system_replied_recently(chat_id):
    """
    True when a real (non-draft) agent/workflow reply already covers the latest
    customer turn. Prefer has_real_agent_reply_after_last_customer; keep the
    last-message check as a secondary signal for chats with no customer rows.
    """
    if has_real_agent_reply_after_last_customer(chat_id):
        return True
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT sender_type, text 
            FROM messages 
            WHERE chat_id = ? 
            ORDER BY timestamp DESC, rowid DESC
            LIMIT 1
        ''', (chat_id,))
        row = c.fetchone()
        if row:
            sender_type, text = row
            if sender_type in ('agent', 'ai', 'system') and '[PROPOSED_DRAFT]' not in str(text):
                return True
    return False

_IDENTITY_PHONE_RE = re.compile(r"\D+")
_IDENTITY_EMAIL_RE = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", re.I)
_IDENTITY_BLOCKED_EMAIL_DOMAINS = (
    "ftstravels.com",
    "fts.com",
    "headout.com",
    "viator.com",
    "tiqets.com",
    "booking.com",
    "expedia.com",
    "agoda.com",
    "system.local",
    "trip.com",
    "alibaba.com",
    "platinumlist.net",
)
_IDENTITY_BLOCKED_LOCAL_PREFIXES = (
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
    "mailer-daemon",
    "bookings",
    "notification",
    "system-notification",
)
_IDENTITY_IGNORED_NAMES = {
    "",
    "?",
    "guest",
    "unknown",
    "lead",
    "make",
    "new lead",
    "lead new",
}
_PROJECTION_LOCK = threading.Lock()
_PROJECTION_CACHE = {"mtime": None, "by_phone": {}, "by_record": {}}
_PHONE_SAFETY_CACHE = {"mtime": None, "unsafe": set()}
_CONV_IDENTITY_LOCK = threading.Lock()
_CONV_IDENTITY_CACHE = {"ts": 0.0, "company": "", "by_phone": {}, "by_email": {}, "by_record": {}}


def _identity_phone_key(raw):
    digits = _IDENTITY_PHONE_RE.sub("", str(raw or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) < 10 or len(digits) > 15:
        return ""
    return digits


def _identity_email_key(raw):
    text = str(raw or "").strip().lower()
    if "::" in text:
        text = text.split("::", 1)[0].strip()
    parsed = parseaddr(text)[1] or text
    match = _IDENTITY_EMAIL_RE.search(str(parsed or ""))
    if not match:
        return ""
    addr = match.group(0).strip().lower()
    local, _, domain = addr.partition("@")
    if len(local) < 3 or not domain:
        return ""
    if any(local.startswith(prefix) for prefix in _IDENTITY_BLOCKED_LOCAL_PREFIXES):
        return ""
    if domain == "reply.getyourguide.com" and local.startswith("customer-"):
        return addr
    if domain.endswith("getyourguide.com"):
        return ""
    if any(domain == blocked or domain.endswith("." + blocked) for blocked in _IDENTITY_BLOCKED_EMAIL_DOMAINS):
        return ""
    return addr


def _identity_location_bucket(location):
    return "religious" if str(location or "").strip().lower() == "religious" else "other"


def _identity_name_key(raw):
    text = re.sub(r"\s+", " ", str(raw or "").strip().lower())
    if text in _IDENTITY_IGNORED_NAMES:
        return ""
    return text


def _projection_phone_index():
    path = get_data_path("airtable_mirror.db")
    if not path or not os.path.exists(path):
        return {}, {}
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = None
    with _PROJECTION_LOCK:
        if _PROJECTION_CACHE.get("mtime") == mtime and _PROJECTION_CACHE.get("by_phone"):
            return _PROJECTION_CACHE["by_phone"], _PROJECTION_CACHE["by_record"]
        by_phone = {}
        by_record = {}
        conn = None
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
            for record_id, phone in conn.execute(
                "SELECT airtable_id, customer_phone FROM mirror_list_projection"
            ):
                key = _identity_phone_key(phone)
                record_key = str(record_id or "").strip()
                if not key or not record_key:
                    continue
                by_record[record_key] = key
                bucket = by_phone.setdefault(key, [])
                if record_key not in bucket:
                    bucket.append(record_key)
        except Exception as exc:
            logging.warning("Inbox identity phone index skipped: %s", exc)
            return {}, {}
        finally:
            try:
                if conn is not None:
                    conn.close()
            except Exception:
                pass
        _PROJECTION_CACHE["mtime"] = mtime
        _PROJECTION_CACHE["by_phone"] = by_phone
        _PROJECTION_CACHE["by_record"] = by_record
        _PHONE_SAFETY_CACHE["mtime"] = mtime
        _PHONE_SAFETY_CACHE["unsafe"] = set()
        return by_phone, by_record


def _mirror_customer_names(record_ids):
    ids = [str(x).strip() for x in (record_ids or []) if str(x or "").strip()]
    if not ids:
        return {}
    path = get_data_path("airtable_mirror.db")
    if not path or not os.path.exists(path):
        return {}
    names = {}
    conn = None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
        for start in range(0, len(ids), 300):
            chunk = ids[start:start + 300]
            marks = ",".join(["?"] * len(chunk))
            for record_id, raw in conn.execute(
                f"SELECT airtable_id, fields_json FROM mirror_records WHERE airtable_id IN ({marks})",
                chunk,
            ):
                try:
                    fields = json.loads(raw or "{}")
                except Exception:
                    fields = {}
                name = _identity_name_key(fields.get("Customer Name") or fields.get("Traveler Name") or "")
                if name:
                    names[str(record_id)] = name
    except Exception as exc:
        logging.warning("Inbox identity name lookup skipped: %s", exc)
        return {}
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
    return names


def _phone_is_unsafe(phone_key, by_phone):
    """A phone used by 4 or more different customer names is not an identity key."""
    if not phone_key:
        return True
    with _PROJECTION_LOCK:
        if phone_key in _PHONE_SAFETY_CACHE.get("unsafe", set()):
            return True
    record_ids = list(by_phone.get(phone_key) or [])
    if len(record_ids) > 25:
        with _PROJECTION_LOCK:
            _PHONE_SAFETY_CACHE.setdefault("unsafe", set()).add(phone_key)
        return True
    if len(record_ids) < 4:
        return False
    names = set(_mirror_customer_names(record_ids).values())
    if len(names) >= 4:
        with _PROJECTION_LOCK:
            _PHONE_SAFETY_CACHE.setdefault("unsafe", set()).add(phone_key)
        return True
    return False


def _chat_identity_keys(row, by_record, blocked_phones):
    phones = set()
    emails = set()
    sender = str((row or {}).get("sender_identifier") or "")
    source = str((row or {}).get("source") or "").strip().lower()
    sender_phone = _identity_phone_key(sender)
    if sender_phone and (source in ("", "whatsapp") or "@" not in sender):
        phones.add(sender_phone)
    stored_phone = _identity_phone_key((row or {}).get("customer_phone"))
    if stored_phone:
        phones.add(stored_phone)
    record_id = str((row or {}).get("airtable_record_id") or "").strip()
    record_phone = by_record.get(record_id) if record_id else ""
    if record_phone:
        phones.add(record_phone)
    email = _identity_email_key(sender)
    if email:
        emails.add(email)
    phones = {phone for phone in phones if phone not in blocked_phones}
    return phones, emails


def _conversation_identity_index(cursor, company_id):
    company_key = str(company_id or DEFAULT_COMPANY_ID).strip() or DEFAULT_COMPANY_ID
    now = time.time()
    with _CONV_IDENTITY_LOCK:
        cache = _CONV_IDENTITY_CACHE
        if (
            cache.get("company") == company_key
            and (now - float(cache.get("ts") or 0)) < 45
            and cache.get("by_record") is not None
            and cache.get("ts")
        ):
            return cache["by_phone"], cache["by_email"], cache["by_record"]
    cursor.execute(
        f"""
        SELECT chat_id, source, sender_identifier, customer_phone, contact_name,
               airtable_record_id, location, booking_number
        FROM conversations
        WHERE IFNULL(is_deleted, 0) = 0 AND {_COMPANY_ID_SQL} = ?
        """,
        (company_key,),
    )
    by_phone = {}
    by_email = {}
    by_record = {}
    for raw in cursor.fetchall():
        row = dict(raw)
        sender = str(row.get("sender_identifier") or "")
        if "@" not in sender:
            phone = _identity_phone_key(sender)
            if phone:
                by_phone.setdefault(phone, []).append(row)
        stored_phone = _identity_phone_key(row.get("customer_phone"))
        if stored_phone:
            bucket = by_phone.setdefault(stored_phone, [])
            if not bucket or bucket[-1].get("chat_id") != row.get("chat_id"):
                bucket.append(row)
        email = _identity_email_key(sender)
        if email:
            by_email.setdefault(email, []).append(row)
        record_id = str(row.get("airtable_record_id") or "").strip()
        if record_id:
            by_record.setdefault(record_id, []).append(row)
    with _CONV_IDENTITY_LOCK:
        _CONV_IDENTITY_CACHE.update(
            ts=time.time(),
            company=company_key,
            by_phone=by_phone,
            by_email=by_email,
            by_record=by_record,
        )
    return by_phone, by_email, by_record


def _attach_customer_identity_groups(cursor, conv_rows, company_id):
    """
    Collapse inbox rows for the same phone or the same private email.
    Booking records stay on their own conversations and are never rewritten here.
    """
    if not conv_rows:
        return
    by_phone, by_record = _projection_phone_index()
    company_key = str(company_id or DEFAULT_COMPANY_ID).strip() or DEFAULT_COMPANY_ID

    seed_phones = set()
    seed_emails = set()
    seed_records = set()
    for row in conv_rows:
        record_id = str(row.get("airtable_record_id") or "").strip()
        if record_id:
            seed_records.add(record_id)
            record_phone = by_record.get(record_id)
            if record_phone:
                seed_phones.add(record_phone)
        sender_phone = _identity_phone_key(row.get("sender_identifier"))
        if sender_phone and "@" not in str(row.get("sender_identifier") or ""):
            seed_phones.add(sender_phone)
        stored_phone = _identity_phone_key(row.get("customer_phone"))
        if stored_phone:
            seed_phones.add(stored_phone)
        email = _identity_email_key(row.get("sender_identifier"))
        if email:
            seed_emails.add(email)

    blocked_phones = {phone for phone in seed_phones if _phone_is_unsafe(phone, by_phone)}
    safe_phones = seed_phones - blocked_phones
    for phone in safe_phones:
        seed_records.update(by_phone.get(phone) or [])

    if not safe_phones and not seed_emails and not seed_records:
        return

    by_chat_phone, by_chat_email, by_chat_record = _conversation_identity_index(cursor, company_key)
    candidates = []
    seen_chats = set()

    def _take(bucket):
        for row in bucket or []:
            chat_id = str(row.get("chat_id") or "")
            if not chat_id or chat_id in seen_chats:
                continue
            seen_chats.add(chat_id)
            candidates.append(row)

    for phone in safe_phones:
        _take(by_chat_phone.get(phone))
    for email in seed_emails:
        _take(by_chat_email.get(email))
    for record_id in seed_records:
        _take(by_chat_record.get(record_id))

    email_names = {}
    for row in candidates:
        email = _identity_email_key(row.get("sender_identifier"))
        name = _identity_name_key(row.get("contact_name"))
        if email and name:
            email_names.setdefault(email, set()).add(name)
    blocked_emails = {email for email, names in email_names.items() if len(names) >= 4}

    parent = {}

    def find(chat_id):
        parent.setdefault(chat_id, chat_id)
        while parent[chat_id] != chat_id:
            parent[chat_id] = parent[parent[chat_id]]
            chat_id = parent[chat_id]
        return chat_id

    def union(left, right):
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    keyed = {}
    phone_to_chats = {}
    email_to_chats = {}
    for row in candidates:
        chat_id = str(row.get("chat_id") or "").strip()
        if not chat_id:
            continue
        phones, emails = _chat_identity_keys(row, by_record, blocked_phones)
        emails = {email for email in emails if email not in blocked_emails}
        if not phones and not emails:
            continue
        bucket = _identity_location_bucket(row.get("location"))
        keyed[chat_id] = row
        parent.setdefault(chat_id, chat_id)
        for phone in phones:
            phone_to_chats.setdefault((bucket, phone), []).append(chat_id)
        for email in emails:
            email_to_chats.setdefault((bucket, email), []).append(chat_id)

    for ids in list(phone_to_chats.values()) + list(email_to_chats.values()):
        if len(ids) < 2:
            continue
        head = ids[0]
        for other in ids[1:]:
            union(head, other)

    components = {}
    for chat_id in list(keyed.keys()):
        components.setdefault(find(chat_id), []).append(chat_id)

    page_ids = {str(row.get("chat_id") or "") for row in conv_rows}
    component_by_chat = {}
    for ids in components.values():
        unique_ids = []
        seen = set()
        for chat_id in ids:
            if chat_id in seen:
                continue
            seen.add(chat_id)
            unique_ids.append(chat_id)
        if len(unique_ids) < 2 or not (page_ids & set(unique_ids)):
            continue
        record_ids = sorted({
            str((keyed.get(chat_id) or {}).get("airtable_record_id") or "").strip()
            for chat_id in unique_ids
            if str((keyed.get(chat_id) or {}).get("airtable_record_id") or "").strip()
        })
        booking_numbers = []
        for chat_id in unique_ids:
            booking_number = str((keyed.get(chat_id) or {}).get("booking_number") or "").strip()
            if booking_number and booking_number not in booking_numbers:
                booking_numbers.append(booking_number)
        group_key = _identity_location_bucket((keyed.get(unique_ids[0]) or {}).get("location")) + ":" + min(unique_ids)
        for chat_id in unique_ids:
            component_by_chat[chat_id] = (group_key, unique_ids, booking_numbers, record_ids)

    if not component_by_chat:
        return

    for row in conv_rows:
        chat_id = str(row.get("chat_id") or "")
        found = component_by_chat.get(chat_id)
        if not found:
            continue
        group_key, ids, booking_numbers, record_ids = found
        current_ids = [str(x) for x in (row.get("grouped_chat_ids") or []) if str(x)]
        merged_ids = []
        for item in current_ids + ids:
            if item not in merged_ids:
                merged_ids.append(item)
        row["grouped_chat_ids"] = merged_ids
        row["inbox_group_key"] = group_key
        row["identity_booking_numbers"] = booking_numbers
        row["identity_record_ids"] = record_ids
        sources = [str(x) for x in (row.get("sources") or []) if str(x)]
        for item in ids:
            source = str((keyed.get(item) or {}).get("source") or "").strip()
            if source and source not in sources:
                sources.append(source)
        if sources:
            row["sources"] = sources


def _collapse_identity_page_rows(rows):
    """Keep one inbox row per phone/email group. Each booking record stays on its own chat."""
    newest = {}
    for row in rows or []:
        key = str(row.get("inbox_group_key") or "").strip()
        if not key:
            continue
        current = newest.get(key)
        if current is None or str(row.get("last_message_time") or "") > str(current.get("last_message_time") or ""):
            newest[key] = row
    seen = set()
    kept = []
    for row in rows or []:
        key = str(row.get("inbox_group_key") or "").strip()
        if not key:
            kept.append(row)
            continue
        if key in seen:
            continue
        seen.add(key)
        kept.append(newest.get(key) or row)
    return kept


def get_conversations():
    page = get_conversations_page(limit=1000000, offset=0)
    return page.get("items") or []

def get_active_ads(company_id=None):
    resolved_company_id = str(company_id or DEFAULT_COMPANY_ID).strip() or DEFAULT_COMPANY_ID
    with _get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT DISTINCT facebook_ad_id, facebook_ad_title
            FROM conversations
            WHERE facebook_ad_id IS NOT NULL
              AND facebook_ad_id != ''
              AND COALESCE(NULLIF(company_id, ''), ?) = ?
            """,
            (DEFAULT_COMPANY_ID, resolved_company_id),
        )
        rows = c.fetchall()
        res = []
        for r in rows:
            res.append({
                "ad_id": r[0],
                "ad_title": r[1] or "New Sales Ad"
            })
        
        # Deduplicate by ad_id
        unique_ads = {}
        for item in res:
            aid = item["ad_id"]
            if aid not in unique_ads or item["ad_title"] != "New Sales Ad":
                unique_ads[aid] = item
                
        return list(unique_ads.values())

def get_conversations_page(
    limit=200,
    offset=0,
    location=None,
    locations=None,
    include_unknown=0,
    needs_help=None,
    sales_only=0,
    source=None,
    exclude_source=None,
    chat_id=None,
    include_deleted=0,
    trash=0,
    assigned_to=None,
    dedicated_whatsapp=None,
    ad_id=None,
    company_id=None,
    airtable_record_ids=None,
    booking_numbers=None,
    view_scope_active=0,
):
    purge_trashed_conversations(retention_days=7)
    try:
        limit_i = int(limit or 0)
    except Exception:
        limit_i = 200
    limit_i = max(1, min(limit_i, 500))
    try:
        offset_i = int(offset or 0)
    except Exception:
        offset_i = 0
    offset_i = max(0, offset_i)

    where = []
    params = []

    try:
        trash_i = 1 if str(trash or "0").strip().lower() in ("1", "true", "yes") else 0
    except Exception:
        trash_i = 0
    try:
        include_deleted_i = 1 if str(include_deleted or "0").strip().lower() in ("1", "true", "yes") else 0
    except Exception:
        include_deleted_i = 0

    if trash_i == 1:
        where.append("COALESCE(is_deleted, 0) = 1")
    elif include_deleted_i == 1:
        pass
    else:
        where.append("COALESCE(is_deleted, 0) = 0")

    if chat_id:
        where.append("chat_id = ?")
        params.append(str(chat_id))

    if source:
        where.append("LOWER(source) = LOWER(?)")
        params.append(str(source))
    if exclude_source:
        where.append("LOWER(COALESCE(source, '')) <> LOWER(?)")
        params.append(str(exclude_source))

    if needs_help is not None and str(needs_help) != "":
        try:
            nh = int(needs_help)
        except Exception:
            nh = None
        if nh in (0, 1):
            where.append("needs_help = ?")
            params.append(nh)

    if int(sales_only or 0) == 1:
        # Never pull Religious chats into Sales via a leftover sales_inbox flag.
        where.append("((sales_inbox = 1 OR location = 'Sales') AND IFNULL(location, '') != 'Religious')")
    else:
        if locations and isinstance(locations, (list, tuple)) and len(locations) > 0:
            locs = [str(x) for x in locations if str(x).strip() != ""]
            if locs:
                where.append("location IN (" + ",".join(["?"] * len(locs)) + ")")
                params.extend(locs)
        elif location:
            loc = str(location)
            if loc == "Quality":
                where.append("location = ?")
                params.append(loc)
            elif int(include_unknown or 0) == 1 and loc == "Hurghada/Cairo":
                # Keep legitimate Unknown chats visible in the external inbox, but hide
                # synthetic Email placeholders created from Airtable record IDs or PSIDs.
                # Sales-inbox chats stay in Sales only (avoid Cairo/Sales filter overlap).
                where.append(
                    "((location = ? OR "
                    "(((location = 'Unknown' OR location = '') "
                    "AND NOT (LOWER(COALESCE(source, '')) = 'email' AND ("
                    "LOWER(COALESCE(sender_identifier, '')) LIKE 'record-%' OR "
                    "(COALESCE(sender_identifier, '') <> '' "
                    "AND COALESCE(sender_identifier, '') GLOB '[0-9]*' "
                    "AND COALESCE(sender_identifier, '') NOT GLOB '*[^0-9]*')))))"
                    ") OR (location = 'Quality' AND quality_from_location = ?)) "
                    "AND IFNULL(sales_inbox, 0) = 0"
                )
                params.extend([loc, loc])
            else:
                where.append("(location = ? OR (location = 'Quality' AND quality_from_location = ?))")
                params.extend([loc, loc])

    if assigned_to:
        if isinstance(assigned_to, (list, tuple)) and assigned_to:
            placeholders = ",".join(["?"] * len(assigned_to))
            where.append(f"(COALESCE(lead_owner_user_id, '') IN ({placeholders}) OR COALESCE(assigned_to, '') IN ({placeholders}))")
            params.extend([str(x) for x in assigned_to])
            params.extend([str(x) for x in assigned_to])
        else:
            where.append("(COALESCE(lead_owner_user_id, '') = ? OR COALESCE(assigned_to, '') = ?)")
            params.extend([str(assigned_to), str(assigned_to)])
        
    if dedicated_whatsapp:
        where.append("receiving_phone_id = ?")
        params.append(str(dedicated_whatsapp))

    if ad_id:
        if ad_id == "normal":
            where.append("(facebook_ad_id IS NULL OR facebook_ad_id = '')")
        else:
            where.append("facebook_ad_id = ?")
            params.append(str(ad_id))

    # Team View ID scope: only conversations linked to records/bookings in the assigned view.
    try:
        view_scope_i = 1 if str(view_scope_active or "0").strip().lower() in ("1", "true", "yes") else 0
    except Exception:
        view_scope_i = 0
    if view_scope_i == 1:
        rids = [str(x).strip() for x in (airtable_record_ids or []) if str(x).strip()]
        bns = [str(x).strip() for x in (booking_numbers or []) if str(x).strip()]
        if not rids and not bns:
            where.append("1 = 0")
        else:
            scope_parts = []

            def _append_in_chunks(column, values, parts_list, params_list, chunk_size=400):
                for i in range(0, len(values), chunk_size):
                    chunk = values[i:i + chunk_size]
                    parts_list.append(f"{column} IN (" + ",".join(["?"] * len(chunk)) + ")")
                    params_list.extend(chunk)

            if rids:
                _append_in_chunks("airtable_record_id", rids, scope_parts, params)
            if bns:
                _append_in_chunks("booking_number", bns, scope_parts, params)
            if scope_parts:
                where.append("(" + " OR ".join(scope_parts) + ")")

    resolved_company_id = str(company_id or DEFAULT_COMPANY_ID).strip() or DEFAULT_COMPANY_ID
    where.append(f"{_COMPANY_ID_SQL} = ?")
    params.append(resolved_company_id)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()

        c.execute(f"SELECT COUNT(1) as cnt FROM (SELECT 1 FROM conversations {where_sql} GROUP BY CASE WHEN COALESCE(airtable_record_id, '') != '' THEN airtable_record_id ELSE chat_id END)", params)
        _row = c.fetchone()
        try:
            total = int(_row["cnt"] if _row is not None else 0)
        except Exception:
            try:
                total = int(dict(_row).get("cnt") if _row is not None else 0)
            except Exception:
                total = 0

        c.execute(
            f"""
            SELECT *
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY CASE WHEN COALESCE(airtable_record_id, '') != '' THEN airtable_record_id ELSE chat_id END
                           ORDER BY last_message_time DESC
                       ) as rn
                FROM conversations
                {where_sql}
            )
            WHERE rn = 1
            ORDER BY last_message_time DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit_i, offset_i],
        )
        conv_rows = [dict(r) for r in c.fetchall()]
        if not conv_rows:
            return {"items": [], "total": total, "limit": limit_i, "offset": offset_i}

        chat_ids = [str(r.get("chat_id")) for r in conv_rows if r.get("chat_id")]
        placeholders = ",".join(["?"] * len(chat_ids))

        derived = {}
        c.execute(
            f"""
            WITH conv AS (
              SELECT chat_id, force_read_at, location
              FROM conversations
              WHERE chat_id IN ({placeholders})
            ),
            last_msg AS (
              SELECT
                m.chat_id,
                m.text AS last_message_text,
                m.sender_type AS last_sender_type,
                ROW_NUMBER() OVER (PARTITION BY m.chat_id ORDER BY m.timestamp DESC) AS rn
              FROM messages m
              WHERE m.chat_id IN ({placeholders})
                AND m.text NOT LIKE '[PROPOSED_DRAFT]%'
            ),
            last_msg_one AS (
              SELECT chat_id, last_message_text, last_sender_type
              FROM last_msg
              WHERE rn = 1
            ),
            unread_msg AS (
              SELECT
                m2.chat_id,
                CASE
                  WHEN m2.sender_type = 'customer' AND m2.text LIKE '%[Customer reacted%' THEN 0
                  WHEN m2.sender_type = 'customer' AND m2.text LIKE '[Facebook Ad Referral]%' THEN 0
                  WHEN m2.sender_type = 'customer' AND m2.text LIKE '[Facebook Referral]%' THEN 0
                  WHEN m2.sender_type = 'customer' THEN 1
                  WHEN m2.text LIKE '%تم سحب المحادثة%' THEN 1
                  ELSE 0
                END AS is_unread_computed,
                ROW_NUMBER() OVER (PARTITION BY m2.chat_id ORDER BY m2.timestamp DESC) AS rn
              FROM messages m2
              JOIN conv c2 ON c2.chat_id = m2.chat_id
              WHERE (c2.force_read_at IS NULL OR m2.timestamp > c2.force_read_at)
                AND IFNULL(m2.text, '') NOT LIKE '[PROPOSED_DRAFT]%'
                AND NOT (
                  IFNULL(m2.text, '') LIKE '[System Log]%'
                  AND IFNULL(m2.text, '') NOT LIKE '%Conversation dismissed%'
                  AND IFNULL(m2.text, '') NOT LIKE '%تم سحب المحادثة%'
                )
            ),
            unread_one AS (
              SELECT chat_id, is_unread_computed
              FROM unread_msg
              WHERE rn = 1
            )
            SELECT
              conv.chat_id,
              lm.last_message_text,
              lm.last_sender_type,
              COALESCE(uo.is_unread_computed, 0) AS is_unread_computed
            FROM conv
            LEFT JOIN last_msg_one lm ON lm.chat_id = conv.chat_id
            LEFT JOIN unread_one uo ON uo.chat_id = conv.chat_id
            """,
            chat_ids + chat_ids,
        )
        for r in c.fetchall():
            rr = dict(r)
            derived[str(rr.get("chat_id"))] = rr

        referral_meta = {}
        c.execute(
            f"""
            SELECT chat_id, text
            FROM messages
            WHERE chat_id IN ({placeholders})
              AND text LIKE '[Facebook%Referral]%'
            ORDER BY timestamp DESC
            """,
            chat_ids,
        )
        for row in c.fetchall():
            chat_id = str(row["chat_id"] or "").strip()
            if not chat_id or chat_id in referral_meta:
                continue
            parsed = _parse_facebook_referral_notice(row["text"])
            if parsed:
                referral_meta[chat_id] = parsed

        record_ids = []
        for r in conv_rows:
            rid = str(r.get("airtable_record_id") or "").strip()
            if rid:
                record_ids.append(rid)
        record_ids = sorted(set(record_ids))

        # إضافة الـ tags من sales_customer_state لكل محادثة (لعرض التصنيف في الواجهة)
        if chat_ids:
            rp2 = ",".join(["?"] * len(chat_ids))
            c.execute(
                f"SELECT chat_id, tags FROM sales_customer_state WHERE chat_id IN ({rp2})",
                chat_ids,
            )
            for rr in c.fetchall():
                for r in conv_rows:
                    if str(r.get("chat_id")) == str(rr["chat_id"]):
                        r["tags"] = rr["tags"]

        grouped_by_record = {}
        if record_ids:
            rp = ",".join(["?"] * len(record_ids))
            c.execute(
                f"""
                SELECT airtable_record_id, GROUP_CONCAT(chat_id) AS ids, GROUP_CONCAT(source) AS sources
                FROM conversations
                WHERE airtable_record_id IN ({rp})
                GROUP BY airtable_record_id
                """,
                record_ids,
            )
            for r in c.fetchall():
                rid = str(r["airtable_record_id"] or "").strip()
                ids = str(r["ids"] or "").strip()
                sources = str(r["sources"] or "").strip()
                if rid and ids:
                    grouped_by_record[rid] = {
                        "ids": [x for x in ids.split(",") if x],
                        "sources": list(set([x for x in sources.split(",") if x]))
                    }

        # Safety net: pending [PROPOSED_DRAFT] awaiting human review must stay Unread
        # even if an older bug set force_read_at right after the draft insert.
        pending_draft_unread = set()
        if chat_ids:
            c.execute(
                f"""
                WITH last_customer AS (
                  SELECT chat_id, MAX(timestamp) AS ts
                  FROM messages
                  WHERE chat_id IN ({placeholders})
                    AND sender_type = 'customer'
                    AND IFNULL(text, '') NOT LIKE '[Facebook Ad Referral]%'
                    AND IFNULL(text, '') NOT LIKE '[Facebook Referral]%'
                  GROUP BY chat_id
                ),
                live_after AS (
                  SELECT DISTINCT m.chat_id
                  FROM messages m
                  JOIN last_customer lc ON lc.chat_id = m.chat_id
                  WHERE m.sender_type IN ('agent', 'ai', 'system')
                    AND IFNULL(m.text, '') NOT LIKE '[PROPOSED_DRAFT]%'
                    AND m.timestamp >= lc.ts
                ),
                draft_after AS (
                  SELECT DISTINCT m.chat_id
                  FROM messages m
                  JOIN last_customer lc ON lc.chat_id = m.chat_id
                  WHERE IFNULL(m.text, '') LIKE '[PROPOSED_DRAFT]%'
                    AND m.timestamp >= lc.ts
                )
                SELECT d.chat_id
                FROM draft_after d
                LEFT JOIN live_after a ON a.chat_id = d.chat_id
                WHERE a.chat_id IS NULL
                """,
                chat_ids,
            )
            pending_draft_unread = {str(row[0]) for row in c.fetchall() if row and row[0]}

        out = []
        for r in conv_rows:
            cid = str(r.get("chat_id") or "")
            d = derived.get(cid) or {}
            r["last_message_text"] = d.get("last_message_text")
            r["last_sender_type"] = d.get("last_sender_type")
            r["is_unread_computed"] = int(d.get("is_unread_computed") or 0)
            if not r["is_unread_computed"] and cid in pending_draft_unread:
                r["is_unread_computed"] = 1
            r["is_deleted"] = int(r.get("is_deleted") or 0)
            r["deleted_at"] = r.get("deleted_at")
            referral = referral_meta.get(cid) or {}
            backfill_updates = {}
            referral_field_map = {
                "facebook_ad_source": "source",
                "facebook_ad_type": "type",
                "facebook_ad_id": "ad_id",
                "facebook_ad_ref": "ref",
                "facebook_ad_title": "ad_title",
                "facebook_post_id": "post_id",
            }
            for field, referral_key in referral_field_map.items():
                current_value = str(r.get(field) or "").strip()
                fallback_value = str(referral.get(referral_key) or "").strip()
                if not current_value and fallback_value:
                    r[field] = fallback_value
                    backfill_updates[field] = fallback_value
            if backfill_updates:
                set_sql = ", ".join([f"{col} = ?" for col in backfill_updates.keys()])
                c.execute(
                    f"UPDATE conversations SET {set_sql} WHERE chat_id = ?",
                    list(backfill_updates.values()) + [cid],
                )
            rid = str(r.get("airtable_record_id") or "").strip()
            if rid and rid in grouped_by_record:
                r["grouped_chat_ids"] = grouped_by_record[rid]["ids"]
                r["sources"] = grouped_by_record[rid]["sources"]
            else:
                r["grouped_chat_ids"] = [cid] if cid else []
                r["sources"] = [r.get("source")] if r.get("source") else []
            out.append(r)

        try:
            _attach_customer_identity_groups(c, out, resolved_company_id)
            out = _collapse_identity_page_rows(out)
        except Exception as identity_exc:
            logging.warning("Inbox identity grouping skipped: %s", identity_exc)

        if referral_meta:
            conn.commit()

        return {"items": out, "total": total, "limit": limit_i, "offset": offset_i}

def get_orphan_conversations():
    """Get conversations that have no associated airtable_record_id."""
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM conversations WHERE airtable_record_id IS NULL OR airtable_record_id = '' ORDER BY last_message_time DESC")
        return [dict(row) for row in c.fetchall()]

def chat_has_facebook_ad_referral_notice(chat_id, ad_id=None, referral_notice=None):
    """
    True if this chat already has a stored [Facebook Ad Referral] notice for the given ad_id
    (or an exact notice text when ad_id is missing). Used to avoid duplicate ad cards while
    still allowing a NEW Ad ID to appear chronologically for the same customer/PSID.
    """
    chat_id = str(chat_id or "").strip()
    if not chat_id:
        return False
    ad_id = str(ad_id or "").strip()
    notice = str(referral_notice or "").strip()
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        if ad_id:
            like = f"%ad_id={ad_id}%"
            c.execute(
                """
                SELECT 1 FROM messages
                WHERE chat_id = ?
                  AND text LIKE '%[Facebook%Referral]%'
                  AND text LIKE ?
                LIMIT 1
                """,
                (chat_id, like),
            )
            if c.fetchone():
                return True
            # Also check merged sibling chats for the same Airtable record
            c.execute("SELECT airtable_record_id FROM conversations WHERE chat_id = ?", (chat_id,))
            row = c.fetchone()
            record_id = str((row[0] if row else "") or "").strip()
            if record_id:
                c.execute(
                    """
                    SELECT 1 FROM messages m
                    JOIN conversations c2 ON c2.chat_id = m.chat_id
                    WHERE c2.airtable_record_id = ?
                      AND m.text LIKE '%[Facebook%Referral]%'
                      AND m.text LIKE ?
                    LIMIT 1
                    """,
                    (record_id, like),
                )
                return bool(c.fetchone())
            return False
        if notice:
            c.execute(
                """
                SELECT 1 FROM messages
                WHERE chat_id = ? AND text = ?
                LIMIT 1
                """,
                (chat_id, notice),
            )
            return bool(c.fetchone())
        return False


def get_messages(chat_id, merge_by_record=True):
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        
        c.execute("SELECT airtable_record_id, company_id FROM conversations WHERE chat_id = ?", (chat_id,))
        row = c.fetchone()
        record_id = row["airtable_record_id"] if row else None
        company_key = str((row["company_id"] if row else "") or "").strip() or "fts"

        if record_id and merge_by_record:
            try:
                c.execute(
                    """
                    UPDATE conversations
                    SET unread_count = 0
                    WHERE airtable_record_id = ?
                      AND unread_count > 0
                      AND COALESCE(NULLIF(company_id, ''), 'fts') = ?
                    """,
                    (record_id, company_key),
                )
                if c.rowcount > 0:
                    conn.commit()
            except sqlite3.OperationalError:
                pass

            c.execute("""
                SELECT m.*, COALESCE(m.source, c.source) as _source, c.sender_identifier as _identifier      
                FROM messages m
                JOIN conversations c ON m.chat_id = c.chat_id
                WHERE c.airtable_record_id = ?
                  AND COALESCE(NULLIF(c.company_id, ''), 'fts') = ?
                ORDER BY m.timestamp ASC
            """, (record_id, company_key))
        else:
            try:
                c.execute("UPDATE conversations SET unread_count = 0 WHERE chat_id = ? AND unread_count > 0", (chat_id,))
                if c.rowcount > 0:
                    conn.commit()
            except sqlite3.OperationalError:
                pass

            c.execute("""
                SELECT m.*, COALESCE(m.source, c.source) as _source, c.sender_identifier as _identifier      
                FROM messages m
                JOIN conversations c ON m.chat_id = c.chat_id
                WHERE m.chat_id = ?
                ORDER BY m.timestamp ASC
            """, (chat_id,))
            
        return [dict(row) for row in c.fetchall()]

def was_message_sent_recently(record_id: str, label_prefix: str, hours: int = 1) -> bool:
    """Checks if a message starting with label_prefix was sent in the last N hours for this record."""
    return count_recent_messages(record_id, label_prefix, hours) > 0

def count_recent_messages(record_id: str, label_prefix: str, hours: int = 1) -> int:
    """Counts how many messages starting with label_prefix were sent in the last N hours for this record."""
    if not record_id or not label_prefix:
        return 0
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        c = conn.cursor()
        try:
            # First find the chat_id(s) for this record_id
            c.execute("SELECT chat_id FROM conversations WHERE airtable_record_id = ?", (record_id,))
            chat_ids = [row[0] for row in c.fetchall()]
            if not chat_ids:
                return 0
                
            placeholders = ','.join(['?'] * len(chat_ids))
            query = f"""
                SELECT COUNT(*) FROM messages 
                WHERE chat_id IN ({placeholders}) 
                AND text LIKE ? 
                AND sender_type = 'agent' 
                AND timestamp >= datetime('now', '-{hours} hours')
            """
            params = [*chat_ids, f"{label_prefix}%"]
            c.execute(query, params)
            return c.fetchone()[0]
        except Exception as e:
            import logging
            logging.error(f"Error counting recent messages: {e}")
            return 0

def claim_sales_lead(chat_id, owner_user_id, owner_name):
    if not chat_id or not owner_user_id:
        return {"ok": False, "error": "missing_params"}
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        now = get_cairo_time()
        c.execute(
            """
            UPDATE conversations
            SET lead_owner_user_id = ?,
                lead_owner_name = COALESCE(NULLIF(?, ''), lead_owner_name),
                lead_owner_assigned_at = ?
            WHERE chat_id = ?
              AND (lead_owner_user_id IS NULL OR lead_owner_user_id = '' OR lead_owner_user_id = ?)
            """,
            (owner_user_id, owner_name or owner_user_id, now, chat_id, owner_user_id),
        )
        conn.commit()
        if c.rowcount == 0:
            conn.row_factory = sqlite3.Row
            c2 = conn.cursor()
            c2.execute(
                "SELECT lead_owner_user_id, lead_owner_name, lead_owner_assigned_at FROM conversations WHERE chat_id = ?",
                (chat_id,),
            )
            row = c2.fetchone()
            if not row:
                return {"ok": False, "error": "not_found"}
            return {"ok": False, "error": "already_owned", "owner": dict(row)}
        return {"ok": True}

def assign_sales_lead(chat_id, owner_user_id, owner_name):
    if not chat_id or not owner_user_id:
        return {"ok": False, "error": "missing_params"}
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            "SELECT lead_owner_user_id, lead_owner_name, lead_owner_assigned_at FROM conversations WHERE chat_id = ?",
            (chat_id,),
        )
        row = c.fetchone()
        if not row:
            return {"ok": False, "error": "not_found"}
        previous_owner = dict(row)
        now = get_cairo_time()
        c2 = conn.cursor()
        c2.execute(
            """
            UPDATE conversations
            SET lead_owner_user_id = ?,
                lead_owner_name = ?,
                lead_owner_assigned_at = ?
            WHERE chat_id = ?
            """,
            (owner_user_id, (owner_name or owner_user_id), now, chat_id),
        )
        conn.commit()
        return {
            "ok": True,
            "previous_owner": previous_owner,
            "new_owner": {
                "lead_owner_user_id": owner_user_id,
                "lead_owner_name": (owner_name or owner_user_id),
                "lead_owner_assigned_at": now,
            },
        }

def release_sales_lead(chat_id, actor_user_id, allow_any=False):
    if not chat_id:
        return {"ok": False, "error": "missing_params"}
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        if allow_any:
            c.execute(
                """
                UPDATE conversations
                SET lead_owner_user_id = NULL,
                    lead_owner_name = NULL,
                    lead_owner_assigned_at = NULL
                WHERE chat_id = ?
                """,
                (chat_id,),
            )
        else:
            c.execute(
                """
                UPDATE conversations
                SET lead_owner_user_id = NULL,
                    lead_owner_name = NULL,
                    lead_owner_assigned_at = NULL
                WHERE chat_id = ?
                  AND lead_owner_user_id = ?
                """,
                (chat_id, actor_user_id),
            )
        conn.commit()
        if c.rowcount == 0:
            return {"ok": False, "error": "not_allowed_or_not_found"}
        return {"ok": True}

def get_sales_leads_by_owner(owner_user_id):
    if not owner_user_id:
        return []
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            """
            SELECT c.*,
                   (SELECT text FROM messages m WHERE m.chat_id = c.chat_id ORDER BY timestamp DESC LIMIT 1) as last_message_text,
                   (SELECT sender_type FROM messages m WHERE m.chat_id = c.chat_id ORDER BY timestamp DESC LIMIT 1) as last_sender_type
            FROM conversations c
            WHERE c.lead_owner_user_id = ?
            ORDER BY c.last_message_time DESC
            """,
            (owner_user_id,),
        )
        return [dict(row) for row in c.fetchall()]

def log_sales_activity(chat_id, event_type, actor_user_id=None, actor_name=None, meta=None, dedupe_seconds=None):
    if not chat_id or not event_type:
        return False
    import json
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        if dedupe_seconds is not None:
            try:
                c.execute(
                    """
                    SELECT created_at
                    FROM sales_activity
                    WHERE chat_id = ?
                      AND event_type = ?
                      AND COALESCE(actor_user_id, '') = COALESCE(?, '')
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (chat_id, event_type, actor_user_id),
                )
                row = c.fetchone()
                if row and row.get("created_at"):
                    from datetime import datetime, timedelta
                    try:
                        last_dt = datetime.fromisoformat(str(row["created_at"]))
                    except Exception:
                        last_dt = None
                    if last_dt and (datetime.utcnow() - last_dt) < timedelta(seconds=int(dedupe_seconds)):
                        return True
            except Exception:
                pass
        meta_json = None
        try:
            meta_json = json.dumps(meta or {}, ensure_ascii=False)
        except Exception:
            meta_json = None
        c.execute(
            """
            INSERT INTO sales_activity (chat_id, event_type, actor_user_id, actor_name, meta_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chat_id, event_type, actor_user_id, actor_name, meta_json, get_cairo_time()),
        )
        conn.commit()
        return True

def get_sales_activity(chat_id, limit=50):
    if not chat_id:
        return []
    import json
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            """
            SELECT id, chat_id, event_type, actor_user_id, actor_name, meta_json, created_at
            FROM sales_activity
            WHERE chat_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (chat_id, int(limit)),
        )
        out = []
        for row in c.fetchall():
            d = dict(row)
            meta_json = d.get("meta_json")
            if meta_json:
                try:
                    d["meta"] = json.loads(meta_json)
                except Exception:
                    d["meta"] = None
            else:
                d["meta"] = None
            out.append(d)
        return out

def split_check24_email_conversations_by_booking(domain="check24.de", booking_pattern=r"\bBR-\d{6,20}\b"):
    domain = str(domain or "").strip().lower()
    if not domain:
        return {"status": "error", "message": "missing domain"}
    pattern = re.compile(str(booking_pattern), re.IGNORECASE)
    mirror_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "airtable_mirror.db")
    mirror_conn = None
    try:
        if os.path.exists(mirror_db):
            mirror_conn = sqlite3.connect(mirror_db, timeout=15.0)
            mirror_conn.row_factory = sqlite3.Row
    except Exception:
        mirror_conn = None

    def lookup_airtable_id(booking_nr):
        if not mirror_conn or not booking_nr:
            return None
        try:
            cur = mirror_conn.cursor()
            cur.execute("SELECT airtable_id FROM mirror_list_projection WHERE booking_nr = ? LIMIT 1", (str(booking_nr).strip(),))
            row = cur.fetchone()
            return row["airtable_id"] if row else None
        except Exception:
            return None

    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("PRAGMA table_info(conversations)")
        conv_cols = [col[1] for col in c.fetchall()]
        c.execute(
            "SELECT * FROM conversations WHERE source = 'Email' AND LOWER(sender_identifier) LIKE ? AND thread_id IS NOT NULL",
            (f"%{domain}%",),
        )
        conversations = [dict(r) for r in (c.fetchall() or [])]

        total_conversations_scanned = 0
        total_conversations_split = 0
        total_messages_moved = 0
        affected_chat_ids = set()

        for conv in conversations:
            total_conversations_scanned += 1
            chat_id = conv.get("chat_id")
            thread_id = conv.get("thread_id")
            if not chat_id or not thread_id:
                continue

            c.execute(
                "SELECT msg_id, text, timestamp, sender_type, source FROM messages WHERE chat_id = ? ORDER BY timestamp ASC",
                (chat_id,),
            )
            msgs = [dict(r) for r in (c.fetchall() or [])]
            if not msgs:
                continue

            groups = {}
            unknown_ids = []
            for m in msgs:
                txt = str(m.get("text") or "")
                m_found = pattern.findall(txt)
                if m_found:
                    booking = str(m_found[0]).strip()
                    groups.setdefault(booking, []).append(m.get("msg_id"))
                else:
                    unknown_ids.append(m.get("msg_id"))

            bookings = [b for b in groups.keys() if b]
            if len(bookings) == 0:
                continue

            primary = None
            current_booking = str(conv.get("booking_number") or "").strip()
            if current_booking and current_booking in groups:
                primary = current_booking
            if not primary:
                primary = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)[0][0]

            if unknown_ids:
                groups.setdefault(primary, []).extend(unknown_ids)
                unknown_ids = []

            if len(groups.keys()) == 1:
                target_thread = f"{thread_id}:{primary}"
                if str(conv.get("thread_id") or "") != target_thread:
                    airtable_id = lookup_airtable_id(primary)
                    scoped_sender_identifier = f"{str(conv.get('sender_identifier') or '').strip()}::{primary}"
                    c.execute(
                        "UPDATE conversations SET thread_id = ?, sender_identifier = ?, booking_number = COALESCE(booking_number, ?), airtable_record_id = COALESCE(airtable_record_id, ?) WHERE chat_id = ?",
                        (target_thread, scoped_sender_identifier, primary, airtable_id, chat_id),
                    )
                    affected_chat_ids.add(chat_id)
                continue

            total_conversations_split += 1

            for booking, msg_ids in list(groups.items()):
                if not booking or not msg_ids:
                    continue
                target_thread = f"{thread_id}:{booking}"
                scoped_sender_identifier = f"{str(conv.get('sender_identifier') or '').strip()}::{booking}"
                airtable_id = lookup_airtable_id(booking)
                if booking == primary:
                    c.execute(
                        "UPDATE conversations SET thread_id = ?, sender_identifier = ?, booking_number = ?, airtable_record_id = COALESCE(?, airtable_record_id) WHERE chat_id = ?",
                        (target_thread, scoped_sender_identifier, booking, airtable_id, chat_id),
                    )
                    affected_chat_ids.add(chat_id)
                    continue

                c.execute(
                    "SELECT chat_id FROM conversations WHERE source = ? AND sender_identifier = ? AND thread_id = ? LIMIT 1",
                    (conv.get("source"), scoped_sender_identifier, target_thread),
                )
                row = c.fetchone()
                target_chat_id = row[0] if row else None
                if not target_chat_id:
                    target_chat_id = str(uuid.uuid4())
                    new_conv = dict(conv)
                    new_conv["chat_id"] = target_chat_id
                    new_conv["thread_id"] = target_thread
                    new_conv["sender_identifier"] = scoped_sender_identifier
                    if "booking_number" in conv_cols:
                        new_conv["booking_number"] = booking
                    if "airtable_record_id" in conv_cols and airtable_id:
                        new_conv["airtable_record_id"] = airtable_id
                    cols = [x for x in conv_cols if x in new_conv]
                    vals = [new_conv.get(x) for x in cols]
                    c.execute(
                        f"INSERT INTO conversations ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})",
                        vals,
                    )
                affected_chat_ids.add(target_chat_id)

                msg_ids_clean = [x for x in msg_ids if x]
                for i in range(0, len(msg_ids_clean), 900):
                    chunk = msg_ids_clean[i:i+900]
                    placeholders = ",".join(["?"] * len(chunk))
                    c.execute(
                        f"UPDATE messages SET chat_id = ? WHERE msg_id IN ({placeholders})",
                        [target_chat_id] + chunk,
                    )
                    total_messages_moved += len(chunk)

            affected_chat_ids.add(chat_id)

        for cid in affected_chat_ids:
            c.execute("SELECT MAX(timestamp) FROM messages WHERE chat_id = ?", (cid,))
            last_ts = c.fetchone()[0]
            if last_ts:
                c.execute("UPDATE conversations SET last_message_time = ? WHERE chat_id = ?", (last_ts, cid))
            c.execute("SELECT force_read_at FROM conversations WHERE chat_id = ?", (cid,))
            fr = None
            r = c.fetchone()
            if r:
                fr = r[0]
            if fr:
                c.execute(
                    "SELECT COUNT(*) FROM messages WHERE chat_id = ? AND sender_type = 'customer' AND timestamp > ?",
                    (cid, fr),
                )
            else:
                c.execute(
                    "SELECT COUNT(*) FROM messages WHERE chat_id = ? AND sender_type = 'customer'",
                    (cid,),
                )
            unread = int(c.fetchone()[0] or 0)
            c.execute("UPDATE conversations SET unread_count = ? WHERE chat_id = ?", (unread, cid))

        conn.commit()

    try:
        if mirror_conn:
            mirror_conn.close()
    except Exception:
        pass

    return {
        "status": "success",
        "domain": domain,
        "conversations_scanned": int(total_conversations_scanned),
        "conversations_split": int(total_conversations_split),
        "messages_moved": int(total_messages_moved),
        "affected_conversations": int(len(affected_chat_ids)),
    }

def upsert_sales_state(chat_id, updates):
    if not chat_id:
        return {"ok": False, "error": "missing_chat_id"}
    if updates is None:
        updates = {}
    allowed = {
        "lead_status",
        "priority",
        "ai_priority",
        "tags",
        "ai_tags",
        "lead_score",
        "follow_up_date",
        "last_contact_date",
        "next_action",
        "ai_next_action",
        "sales_notes",
        "ai_sales_summary",
        "is_starred",
        "reason_for_marking",
        "assigned_sales_user",
        "needs_ai_review",
        "overdue_followup",
        "ready_to_close",
    }

    data = {}
    for k, v in (updates or {}).items():
        if k in allowed:
            data[k] = v

    now = get_cairo_time()
    cols = ["chat_id"] + sorted(list(data.keys())) + ["updated_at", "created_at"]
    placeholders = ",".join(["?"] * len(cols))
    values = [chat_id] + [data.get(k) for k in sorted(list(data.keys()))] + [now, now]
    update_cols = sorted(list(data.keys())) + ["updated_at"]
    update_sql = ", ".join([f"{k} = excluded.{k}" for k in update_cols])

    try:
        with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
            c = conn.cursor()
            c.execute(
                f"""
                INSERT INTO sales_customer_state ({",".join(cols)})
                VALUES ({placeholders})
                ON CONFLICT(chat_id) DO UPDATE SET
                {update_sql}
                """,
                values,
            )
            conn.commit()
            return {"ok": True}
    except sqlite3.OperationalError as e:
        return {"ok": False, "error": str(e)}

def get_sales_state(chat_id):
    if not chat_id:
        return None
    try:
        with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM sales_customer_state WHERE chat_id = ?", (chat_id,))
            row = c.fetchone()
            return dict(row) if row else None
    except sqlite3.OperationalError:
        return None

def list_sales_customers(
    actor_user_id=None,
    is_admin=False,
    locations=None,
    company_id=None,
    airtable_record_ids=None,
    booking_numbers=None,
    view_scope_active=0,
):
    try:
        with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            try:
                c.execute("PRAGMA table_info(conversations)")
                cols = [col[1] for col in c.fetchall()]
                if 'sales_inbox' not in cols:
                    c.execute("ALTER TABLE conversations ADD COLUMN sales_inbox INTEGER DEFAULT 0")
                    conn.commit()
            except Exception:
                pass

            where = []
            params = []
            resolved_company_id = str(company_id or DEFAULT_COMPANY_ID).strip() or DEFAULT_COMPANY_ID
            where.append("COALESCE(NULLIF(c.company_id, ''), 'fts') = ?")
            params.append(resolved_company_id)
            if not is_admin:
                where.append("(c.lead_owner_user_id IS NULL OR c.lead_owner_user_id = '' OR c.lead_owner_user_id = ?)")
                params.append(str(actor_user_id or ""))

            if locations:
                locs = [str(x or "").strip() for x in locations if str(x or "").strip()]
                if locs:
                    placeholders = ",".join(["?"] * len(locs))
                    if any(x.lower() == "sales" for x in locs):
                        where.append(
                            f"((LOWER(COALESCE(c.location, '')) IN ({placeholders}) OR COALESCE(c.sales_inbox, 0) = 1) "
                            f"AND LOWER(COALESCE(c.location, '')) != 'religious')"
                        )
                    else:
                        where.append(f"LOWER(COALESCE(c.location, '')) IN ({placeholders})")
                    params.extend([x.lower() for x in locs])

            try:
                view_scope_i = 1 if str(view_scope_active or "0").strip().lower() in ("1", "true", "yes") else 0
            except Exception:
                view_scope_i = 0
            if view_scope_i == 1:
                rids = [str(x).strip() for x in (airtable_record_ids or []) if str(x).strip()]
                bns = [str(x).strip() for x in (booking_numbers or []) if str(x).strip()]
                if not rids and not bns:
                    where.append("1 = 0")
                else:
                    scope_parts = []

                    def _append_in_chunks(column, values, parts_list, params_list, chunk_size=400):
                        for i in range(0, len(values), chunk_size):
                            chunk = values[i:i + chunk_size]
                            parts_list.append(f"{column} IN (" + ",".join(["?"] * len(chunk)) + ")")
                            params_list.extend(chunk)

                    if rids:
                        _append_in_chunks("c.airtable_record_id", rids, scope_parts, params)
                    if bns:
                        _append_in_chunks("c.booking_number", bns, scope_parts, params)
                    if scope_parts:
                        where.append("(" + " OR ".join(scope_parts) + ")")

            where_sql = ("WHERE " + " AND ".join(where)) if where else ""
            c.execute(
                f"""
                SELECT
                    c.*,
                    (SELECT text FROM messages m WHERE m.chat_id = c.chat_id ORDER BY timestamp DESC LIMIT 1) as last_message_text,
                    (SELECT sender_type FROM messages m WHERE m.chat_id = c.chat_id ORDER BY timestamp DESC LIMIT 1) as last_sender_type,
                    s.lead_status,
                    s.priority,
                    s.ai_priority,
                    s.tags,
                    s.ai_tags,
                    s.lead_score,
                    s.follow_up_date,
                    s.last_contact_date,
                    s.next_action,
                    s.ai_next_action,
                    s.sales_notes,
                    s.ai_sales_summary,
                    COALESCE(s.is_starred, 0) as is_starred,
                    s.reason_for_marking,
                    COALESCE(s.assigned_sales_user, c.lead_owner_user_id) as assigned_sales_user,
                    COALESCE(s.needs_ai_review, 0) as needs_ai_review,
                    COALESCE(s.overdue_followup, 0) as overdue_followup,
                    COALESCE(s.ready_to_close, 0) as ready_to_close,
                    s.updated_at as sales_updated_at
                FROM conversations c
                LEFT JOIN sales_customer_state s ON s.chat_id = c.chat_id
                {where_sql}
                ORDER BY COALESCE(s.lead_score, 0) DESC, c.last_message_time DESC
                """,
                params,
            )
            return [dict(row) for row in c.fetchall()]
    except sqlite3.OperationalError:
        return []

def compute_sales_daily_tasks(
    actor_user_id=None,
    is_admin=False,
    locations=None,
    company_id=None,
    airtable_record_ids=None,
    booking_numbers=None,
    view_scope_active=0,
):
    from datetime import datetime, date

    chats = list_sales_customers(
        actor_user_id=actor_user_id,
        is_admin=is_admin,
        locations=locations,
        company_id=company_id,
        airtable_record_ids=airtable_record_ids,
        booking_numbers=booking_numbers,
        view_scope_active=view_scope_active,
    )
    today = date.today().isoformat()
    out = {
        "followups_today": [],
        "overdue": [],
        "high_score": [],
        "ready_to_close": [],
        "needs_ai_review": [],
        "starred": [],
        "no_answer": [],
        "inactive": [],
    }

    now_dt = datetime.utcnow()

    for ch in chats:
        try:
            lead_score = int(ch.get("lead_score") or 0)
        except Exception:
            lead_score = 0
        follow_up_date = str(ch.get("follow_up_date") or "").strip()
        last_contact_date = str(ch.get("last_contact_date") or "").strip()
        is_starred = int(ch.get("is_starred") or 0) == 1
        needs_ai_review = int(ch.get("needs_ai_review") or 0) == 1
        ready_to_close = int(ch.get("ready_to_close") or 0) == 1

        if follow_up_date == today:
            out["followups_today"].append(ch)
        if follow_up_date and follow_up_date < today:
            out["overdue"].append(ch)
        if lead_score >= 70:
            out["high_score"].append(ch)
        if ready_to_close:
            out["ready_to_close"].append(ch)
        if needs_ai_review:
            out["needs_ai_review"].append(ch)
        if is_starred:
            out["starred"].append(ch)

        try:
            if last_contact_date:
                last_dt = datetime.fromisoformat(last_contact_date)
            else:
                last_dt = None
            if last_dt and (now_dt - last_dt).total_seconds() > (3 * 24 * 3600):
                out["inactive"].append(ch)
        except Exception:
            pass

        try:
            if str(ch.get("last_sender_type") or "").lower() == "customer":
                last_time = str(ch.get("last_message_time") or "")
                if last_time:
                    last_msg_dt = datetime.fromisoformat(last_time)
                    if (now_dt - last_msg_dt).total_seconds() > (24 * 3600):
                        out["no_answer"].append(ch)
        except Exception:
            pass

    def top_n(items, n=20, key="lead_score"):
        try:
            return sorted(items, key=lambda x: int(x.get(key) or 0), reverse=True)[:n]
        except Exception:
            return items[:n]

    out["followups_today"] = top_n(out["followups_today"], 30)
    out["overdue"] = top_n(out["overdue"], 30)
    out["high_score"] = top_n(out["high_score"], 30)
    out["ready_to_close"] = top_n(out["ready_to_close"], 30)
    out["needs_ai_review"] = top_n(out["needs_ai_review"], 30)
    out["starred"] = top_n(out["starred"], 30)
    out["no_answer"] = top_n(out["no_answer"], 30)
    out["inactive"] = top_n(out["inactive"], 30)
    out["counts"] = {k: len(v) for k, v in out.items() if isinstance(v, list)}
    return out


AI_USAGE_SOURCE_LABELS = {
    "booking_extraction": {"en": "Booking data extraction", "ar": "استخراج بيانات الحجز من الرسائل/الإيميل"},
    "operations_booking_draft": {"en": "Operations booking draft parser", "ar": "تحليل مسودة حجز (Operations)"},
    "operations_filter_parse": {"en": "Operations filter builder (AI)", "ar": "بناء فلاتر العمليات بالذكاء الاصطناعي"},
    "contact_extraction": {"en": "Contact extraction", "ar": "استخراج إيميل/هاتف"},
    "booking_from_history": {"en": "Booking number from history", "ar": "استخراج رقم الحجز من السجل"},
    "message_classification": {"en": "Customer message intent classification", "ar": "تصنيف نية رسالة العميل (Intent)"},
    "supplier_email_classify": {"en": "Supplier email classification", "ar": "تصنيف إيميلات الموردين (OTA)"},
    "supplier_email_inquiry": {"en": "Supplier email inquiry detection", "ar": "كشف استفسار داخل إيميل المورد"},
    "supplier_email_relevance": {"en": "Email spam/relevance filter", "ar": "فلترة الإيميلات (Spam / Process)"},
    "supplier_booking_extract": {"en": "Supplier booking extraction", "ar": "استخراج حجز من إيميل المورد"},
    "quality_reply_assessment": {"en": "Quality — reply assessment", "ar": "تقييم جودة ردود الموظفين"},
    "team_performance_analysis": {"en": "Team performance AI summary", "ar": "تحليل أداء الفريق"},
    "sales_chat_analysis": {"en": "Sales chat scoring & tags", "ar": "تحليل محادثات المبيعات (Lead score)"},
    "conversation_summary": {"en": "Conversation summarization", "ar": "تلخيص المحادثات"},
    "internal_assistant_mediator": {"en": "Internal assistant mediator", "ar": "وسيط المساعد الداخلي (PI)"},
    "automation_workflow": {"en": "Automation workflow (generic)", "ar": "أتمتة Workflow"},
    "analysis": {"en": "General analysis (legacy / unspecified)", "ar": "تحليل عام (قديم / غير محدد)"},
    "translation": {"en": "Translation", "ar": "ترجمة"},
    "optimizer": {"en": "Text optimizer", "ar": "تحسين النص"},
    "customer_auto_reply": {"en": "Customer auto-reply", "ar": "رد تلقائي للعميل"},
    "internal_assistant": {"en": "Internal assistant reply", "ar": "رد المساعد الداخلي"},
}


def _usage_source_label(source_key, lang="en"):
    key = str(source_key or "").strip()
    if key.startswith("automation:"):
        wf = key.split(":", 1)[1].strip() or "workflow"
        if lang == "ar":
            return f"أتمتة: {wf}"
        return f"Automation: {wf}"
    meta = AI_USAGE_SOURCE_LABELS.get(key) or {}
    if lang == "ar":
        return meta.get("ar") or key or "unknown"
    return meta.get("en") or key or "unknown"


DEFAULT_AI_USAGE_RATES = {
    "currency": "USD",
    "pricing_version": 2,
    "pricing_reference": "https://api-docs.deepseek.com/quick_start/pricing/",
    "peak_hours_utc": "Mon–Fri 01:00–04:00 and 06:00–10:00 UTC (off-peak = half price)",
    "default": {
        "input_cache_hit_off_peak": 0.22,
        "input_cache_hit_peak": 0.44,
        "input_cache_miss_off_peak": 0.22,
        "input_cache_miss_peak": 0.44,
        "output_off_peak": 0.66,
        "output_peak": 1.32,
    },
    "models": {
        "deepseek-v4-flash": {
            "input_cache_hit_off_peak": 0.007,
            "input_cache_hit_peak": 0.014,
            "input_cache_miss_off_peak": 0.22,
            "input_cache_miss_peak": 0.44,
            "output_off_peak": 0.66,
            "output_peak": 1.32,
        },
        "deepseek-v4-flash-vision-exp": {
            "input_cache_hit_off_peak": 0.007,
            "input_cache_hit_peak": 0.014,
            "input_cache_miss_off_peak": 0.22,
            "input_cache_miss_peak": 0.44,
            "output_off_peak": 0.66,
            "output_peak": 1.32,
        },
        "deepseek-chat": {
            "input_cache_hit_off_peak": 0.007,
            "input_cache_hit_peak": 0.014,
            "input_cache_miss_off_peak": 0.22,
            "input_cache_miss_peak": 0.44,
            "output_off_peak": 0.66,
            "output_peak": 1.32,
        },
        "deepseek-v4-pro": {
            "input_cache_hit_off_peak": 0.022,
            "input_cache_hit_peak": 0.044,
            "input_cache_miss_off_peak": 0.66,
            "input_cache_miss_peak": 1.32,
            "output_off_peak": 1.98,
            "output_peak": 3.96,
        },
        "deepseek-reasoner": {
            "input_cache_hit_off_peak": 0.022,
            "input_cache_hit_peak": 0.044,
            "input_cache_miss_off_peak": 0.66,
            "input_cache_miss_peak": 1.32,
            "output_off_peak": 1.98,
            "output_peak": 3.96,
        },
        "gpt-4o-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60},
        "gpt-4o": {"input_per_1m": 2.50, "output_per_1m": 10.00},
        "gpt-5.6-terra": {"input_per_1m": 1.25, "output_per_1m": 10.00},
        "gpt-5.6-luna": {"input_per_1m": 2.50, "output_per_1m": 15.00},
        "gpt-5.6-sol": {"input_per_1m": 5.00, "output_per_1m": 20.00},
        "gpt-5.6": {"input_per_1m": 2.50, "output_per_1m": 15.00},
        # Local / Ollama — free (self-hosted); keep separate from DeepSeek cloud pricing
        "qwen2.5:3b": {"input_per_1m": 0.0, "output_per_1m": 0.0},
        "qwen2.5:7b": {"input_per_1m": 0.0, "output_per_1m": 0.0},
        "qwen2.5": {"input_per_1m": 0.0, "output_per_1m": 0.0},
        "qwen": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    },
}


def _coerce_rate_value(raw, fallback=0.0):
    try:
        return max(0.0, float(raw))
    except Exception:
        return max(0.0, float(fallback))


def _upgrade_legacy_model_rates(model_rates, template=None):
    src = dict(model_rates or {})
    tpl = dict(template or {})
    if src.get("input_cache_miss_off_peak") is not None or src.get("output_off_peak") is not None:
        out = {
            "input_cache_hit_off_peak": _coerce_rate_value(
                src.get("input_cache_hit_off_peak"), tpl.get("input_cache_hit_off_peak", 0)
            ),
            "input_cache_hit_peak": _coerce_rate_value(
                src.get("input_cache_hit_peak"),
                src.get("input_cache_hit_off_peak", tpl.get("input_cache_hit_peak", 0)) * 2
                if src.get("input_cache_hit_off_peak") is not None
                else tpl.get("input_cache_hit_peak", 0),
            ),
            "input_cache_miss_off_peak": _coerce_rate_value(
                src.get("input_cache_miss_off_peak"), tpl.get("input_cache_miss_off_peak", 0)
            ),
            "input_cache_miss_peak": _coerce_rate_value(
                src.get("input_cache_miss_peak"),
                src.get("input_cache_miss_off_peak", tpl.get("input_cache_miss_peak", 0)) * 2
                if src.get("input_cache_miss_off_peak") is not None
                else tpl.get("input_cache_miss_peak", 0),
            ),
            "output_off_peak": _coerce_rate_value(src.get("output_off_peak"), tpl.get("output_off_peak", 0)),
            "output_peak": _coerce_rate_value(
                src.get("output_peak"),
                src.get("output_off_peak", tpl.get("output_peak", 0)) * 2
                if src.get("output_off_peak") is not None
                else tpl.get("output_peak", 0),
            ),
        }
        return out
    legacy_in = src.get("input_per_1m", tpl.get("input_per_1m"))
    legacy_out = src.get("output_per_1m", tpl.get("output_per_1m"))
    if legacy_in is not None or legacy_out is not None:
        return {
            "input_per_1m": _coerce_rate_value(legacy_in, tpl.get("input_per_1m", 0)),
            "output_per_1m": _coerce_rate_value(legacy_out, tpl.get("output_per_1m", 0)),
        }
    if tpl:
        return _upgrade_legacy_model_rates(tpl, {})
    return src


def _normalize_ai_usage_rates(raw):
    base = {
        "currency": "USD",
        "pricing_version": DEFAULT_AI_USAGE_RATES["pricing_version"],
        "pricing_reference": DEFAULT_AI_USAGE_RATES["pricing_reference"],
        "peak_hours_utc": DEFAULT_AI_USAGE_RATES["peak_hours_utc"],
        "default": _upgrade_legacy_model_rates(
            DEFAULT_AI_USAGE_RATES["default"],
            DEFAULT_AI_USAGE_RATES["default"],
        ),
        "models": {
            k: _upgrade_legacy_model_rates(v, DEFAULT_AI_USAGE_RATES["models"].get(k))
            for k, v in DEFAULT_AI_USAGE_RATES["models"].items()
        },
    }
    if not isinstance(raw, dict):
        return base
    try:
        version = int(raw.get("pricing_version") or 0)
    except Exception:
        version = 0
    if version < DEFAULT_AI_USAGE_RATES["pricing_version"]:
        # Stored rates used old flat input/output — prefer official DeepSeek defaults.
        pass
    else:
        currency = str(raw.get("currency") or "USD").strip().upper() or "USD"
        base["currency"] = currency
        base["default"] = _upgrade_legacy_model_rates(
            raw.get("default") if isinstance(raw.get("default"), dict) else {},
            DEFAULT_AI_USAGE_RATES["default"],
        )
        models = raw.get("models") if isinstance(raw.get("models"), dict) else {}
        for model_name, rates in models.items():
            name = str(model_name or "").strip()
            if not name or not isinstance(rates, dict):
                continue
            base["models"][name] = _upgrade_legacy_model_rates(
                rates,
                DEFAULT_AI_USAGE_RATES["models"].get(name) or DEFAULT_AI_USAGE_RATES["default"],
            )
    return base


def get_ai_usage_rates():
    raw = None
    try:
        stored = get_setting("ai_usage_rates")
        if stored:
            raw = json.loads(stored)
    except Exception:
        raw = None
    return _normalize_ai_usage_rates(raw)


def save_ai_usage_rates(raw):
    rates = _normalize_ai_usage_rates(raw)
    rates["pricing_version"] = DEFAULT_AI_USAGE_RATES["pricing_version"]
    try:
        set_setting("ai_usage_rates", json.dumps(rates, ensure_ascii=False))
    except Exception:
        pass
    return rates


def _ai_provider_family(provider="", model=""):
    """Group providers for usage reports (DeepSeek cloud vs local Ollama vs OpenAI)."""
    p = str(provider or "").strip().lower()
    m = str(model or "").strip().lower()
    if (
        "ollama" in p
        or p.endswith("_local")
        or p == "local"
        or m.startswith("qwen")
        or "qwen2" in m
    ):
        return "ollama_local"
    if "deepseek" in p or m.startswith("deepseek"):
        return "deepseek"
    if "openai" in p or m.startswith("gpt-") or m.startswith("o1") or m.startswith("o3"):
        return "openai"
    return "other"


def _is_local_free_model(model_name="", provider=""):
    return _ai_provider_family(provider, model_name) == "ollama_local"


def _ai_usage_rate_for_model(model_name, rates=None, provider=""):
    rates = rates or get_ai_usage_rates()
    default = rates.get("default") or DEFAULT_AI_USAGE_RATES["default"]
    model = str(model_name or "").strip().lower()
    models = rates.get("models") or {}
    best_key = ""
    best_rates = None
    for key, val in models.items():
        k = str(key or "").strip().lower()
        if not k:
            continue
        if model == k or model.startswith(k) or k.startswith(model):
            if len(k) >= len(best_key):
                best_key = k
                best_rates = val
    if isinstance(best_rates, dict):
        # Prefer flat local template when matching local models so DeepSeek cache
        # defaults are not mixed into free self-hosted pricing.
        tpl = (
            {"input_per_1m": 0.0, "output_per_1m": 0.0}
            if _is_local_free_model(model_name, provider)
            else default
        )
        return _upgrade_legacy_model_rates(best_rates, tpl)
    if _is_local_free_model(model_name, provider):
        return {"input_per_1m": 0.0, "output_per_1m": 0.0}
    return _upgrade_legacy_model_rates(default, DEFAULT_AI_USAGE_RATES["default"])


def _parse_usage_timestamp(created_at):
    s = str(created_at or "").strip()
    if not s:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            # Stored timestamps are Cairo-local wall time without tz suffix.
            dt = (dt - CAIRO_OFFSET).replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def _deepseek_is_peak_utc(dt):
    """DeepSeek peak: Mon–Fri 01:00–04:00 and 06:00–10:00 UTC."""
    if not dt:
        return False
    if dt.weekday() >= 5:
        return False
    hour = dt.hour
    return (1 <= hour < 4) or (6 <= hour < 10)


def _resolve_cache_token_split(prompt_tokens, prompt_cache_hit_tokens=None, prompt_cache_miss_tokens=None):
    pt = max(0, int(prompt_tokens or 0))
    hit = prompt_cache_hit_tokens
    miss = prompt_cache_miss_tokens
    if hit is None and miss is None:
        return 0, pt
    hit = max(0, int(hit or 0))
    miss = max(0, int(miss or 0))
    if hit + miss == 0 and pt > 0:
        return 0, pt
    if pt > 0 and hit + miss != pt:
        miss = max(0, pt - hit)
    return hit, miss


def estimate_ai_cost_usd(
    model_name,
    prompt_tokens,
    completion_tokens,
    prompt_cache_hit_tokens=None,
    prompt_cache_miss_tokens=None,
    created_at=None,
    rates=None,
    provider="",
):
    if _is_local_free_model(model_name, provider):
        return 0.0
    rates = rates or get_ai_usage_rates()
    per = _ai_usage_rate_for_model(model_name, rates, provider=provider)
    pt = max(0, int(prompt_tokens or 0))
    ct = max(0, int(completion_tokens or 0))
    hit, miss = _resolve_cache_token_split(pt, prompt_cache_hit_tokens, prompt_cache_miss_tokens)
    dt = _parse_usage_timestamp(created_at)
    is_peak = _deepseek_is_peak_utc(dt)

    if per.get("input_cache_miss_off_peak") is not None or per.get("output_off_peak") is not None:
        if is_peak:
            in_hit_rate = _coerce_rate_value(per.get("input_cache_hit_peak"), per.get("input_cache_hit_off_peak", 0) * 2)
            in_miss_rate = _coerce_rate_value(per.get("input_cache_miss_peak"), per.get("input_cache_miss_off_peak", 0) * 2)
            out_rate = _coerce_rate_value(per.get("output_peak"), per.get("output_off_peak", 0) * 2)
        else:
            in_hit_rate = _coerce_rate_value(per.get("input_cache_hit_off_peak"))
            in_miss_rate = _coerce_rate_value(per.get("input_cache_miss_off_peak"))
            out_rate = _coerce_rate_value(per.get("output_off_peak"))
        cost = (hit / 1_000_000.0) * in_hit_rate + (miss / 1_000_000.0) * in_miss_rate + (ct / 1_000_000.0) * out_rate
        return round(max(0.0, cost), 6)

    inp = _coerce_rate_value(per.get("input_per_1m"))
    outp = _coerce_rate_value(per.get("output_per_1m"))
    cost = (pt / 1_000_000.0) * inp + (ct / 1_000_000.0) * outp
    return round(max(0.0, cost), 6)


def _ai_usage_pricing_tier(created_at=None):
    return "peak" if _deepseek_is_peak_utc(_parse_usage_timestamp(created_at)) else "off_peak"


def record_ai_usage_event(
    department="",
    source="",
    system_role="",
    provider="",
    model="",
    location="",
    chat_id="",
    prompt_tokens=0,
    completion_tokens=0,
    total_tokens=0,
    prompt_cache_hit_tokens=0,
    prompt_cache_miss_tokens=0,
    cost_usd=0.0,
    estimated=0,
    created_at=None,
):
    try:
        prompt_tokens = max(0, int(prompt_tokens or 0))
        completion_tokens = max(0, int(completion_tokens or 0))
        total_tokens = max(0, int(total_tokens or (prompt_tokens + completion_tokens)))
        hit, miss = _resolve_cache_token_split(
            prompt_tokens, prompt_cache_hit_tokens, prompt_cache_miss_tokens
        )
        created_at = str(created_at or get_cairo_time())
        if cost_usd is None or cost_usd == 0:
            cost_usd = estimate_ai_cost_usd(
                model,
                prompt_tokens,
                completion_tokens,
                prompt_cache_hit_tokens=hit,
                prompt_cache_miss_tokens=miss,
                created_at=created_at,
                provider=provider,
            )
        else:
            cost_usd = float(cost_usd or 0)
            if _is_local_free_model(model, provider):
                cost_usd = 0.0
        pricing_tier = _ai_usage_pricing_tier(created_at)
    except Exception:
        return False
    attempts = 3
    for attempt in range(attempts):
        try:
            with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
                try:
                    conn.execute("PRAGMA busy_timeout = 15000;")
                except Exception:
                    pass
                conn.execute(
                    """
                    INSERT INTO ai_usage_events (
                        created_at, department, source, system_role, provider, model,
                        location, chat_id, prompt_tokens, completion_tokens, total_tokens,
                        prompt_cache_hit_tokens, prompt_cache_miss_tokens, pricing_tier,
                        cost_usd, estimated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        created_at,
                        str(department or "Unassigned")[:80],
                        str(source or "")[:80],
                        str(system_role or "")[:80],
                        str(provider or "")[:80],
                        str(model or "")[:120],
                        str(location or "")[:80],
                        str(chat_id or "")[:160],
                        prompt_tokens,
                        completion_tokens,
                        total_tokens,
                        hit,
                        miss,
                        pricing_tier,
                        cost_usd,
                        1 if estimated else 0,
                    ),
                )
                conn.commit()
                return True
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < (attempts - 1):
                time.sleep(0.15 * (attempt + 1))
                continue
            logging.error(f"AI usage sqlite write failed: {e}")
            return False
        except Exception as e:
            logging.error(f"AI usage write failed: {e}")
            return False
    return False


def _ai_usage_date_bounds(from_date, to_date):
    today = get_cairo_time()[:10]
    start = str(from_date or "").strip()[:10] or today
    end = str(to_date or "").strip()[:10] or today
    if len(start) < 10:
        start = today
    if len(end) < 10:
        end = today
    if start > end:
        start, end = end, start
    return f"{start}T00:00:00", f"{end}T23:59:59.999999"


def get_ai_usage_report(from_date=None, to_date=None, company_id=None):
    start, end = _ai_usage_date_bounds(from_date, to_date)
    rates = get_ai_usage_rates()
    resolved_company_id = str(company_id or DEFAULT_COMPANY_ID).strip() or DEFAULT_COMPANY_ID
    empty = {
        "from": start[:10],
        "to": end[:10],
        "currency": rates.get("currency") or "USD",
        "pricing_reference": rates.get("pricing_reference") or DEFAULT_AI_USAGE_RATES["pricing_reference"],
        "peak_hours_utc": rates.get("peak_hours_utc") or DEFAULT_AI_USAGE_RATES["peak_hours_utc"],
        "totals": {
            "requests": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "prompt_cache_hit_tokens": 0,
            "prompt_cache_miss_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "estimated_requests": 0,
        },
        "by_department": [],
        "by_provider": [],
        "by_provider_model": [],
        "by_family": [],
        "by_source": [],
        "internal_tools_breakdown": [],
        "source_labels": AI_USAGE_SOURCE_LABELS,
    }
    try:
        with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute(
                """
                SELECT
                    e.created_at, e.department, e.source, e.system_role, e.provider, e.model,
                    e.prompt_tokens, e.completion_tokens, e.total_tokens,
                    e.prompt_cache_hit_tokens, e.prompt_cache_miss_tokens,
                    e.pricing_tier, e.cost_usd, e.estimated
                FROM ai_usage_events e
                LEFT JOIN conversations conv ON conv.chat_id = e.chat_id
                WHERE e.created_at >= ? AND e.created_at <= ?
                  AND COALESCE(NULLIF(conv.company_id, ''), 'fts') = ?
                """,
                (start, end, resolved_company_id),
            )
            rows = [dict(r) for r in c.fetchall()]

            def _event_cost(row):
                return estimate_ai_cost_usd(
                    row.get("model"),
                    row.get("prompt_tokens"),
                    row.get("completion_tokens"),
                    prompt_cache_hit_tokens=row.get("prompt_cache_hit_tokens"),
                    prompt_cache_miss_tokens=row.get("prompt_cache_miss_tokens"),
                    created_at=row.get("created_at"),
                    rates=rates,
                    provider=row.get("provider"),
                )

            def _bucket_key(row, field):
                val = str(row.get(field) or "").strip()
                return val or ("Unassigned" if field == "department" else "unknown")

            buckets_dept = {}
            buckets_provider = {}
            buckets_source = {}
            buckets_provider_model = {}
            buckets_family = {}
            buckets_internal_tools = {}
            family_labels = {
                "deepseek": "DeepSeek (cloud)",
                "ollama_local": "Ollama / Local (Qwen)",
                "openai": "OpenAI",
                "other": "Other",
            }
            totals = {
                "requests": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "prompt_cache_hit_tokens": 0,
                "prompt_cache_miss_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
                "estimated_requests": 0,
            }

            for row in rows:
                pt = int(row.get("prompt_tokens") or 0)
                ct = int(row.get("completion_tokens") or 0)
                tt = int(row.get("total_tokens") or (pt + ct))
                hit, miss = _resolve_cache_token_split(
                    pt,
                    row.get("prompt_cache_hit_tokens"),
                    row.get("prompt_cache_miss_tokens"),
                )
                cost = _event_cost(row)
                estimated = int(row.get("estimated") or 0) == 1

                totals["requests"] += 1
                totals["prompt_tokens"] += pt
                totals["completion_tokens"] += ct
                totals["prompt_cache_hit_tokens"] += hit
                totals["prompt_cache_miss_tokens"] += miss
                totals["total_tokens"] += tt
                totals["cost_usd"] += cost
                if estimated:
                    totals["estimated_requests"] += 1

                for field, store in (
                    ("department", buckets_dept),
                    ("provider", buckets_provider),
                    ("source", buckets_source),
                ):
                    key = _bucket_key(row, field)
                    bucket = store.setdefault(
                        key,
                        {
                            "label": key,
                            "requests": 0,
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "prompt_cache_hit_tokens": 0,
                            "prompt_cache_miss_tokens": 0,
                            "total_tokens": 0,
                            "cost_usd": 0.0,
                            "estimated_requests": 0,
                        },
                    )
                    bucket["requests"] += 1
                    bucket["prompt_tokens"] += pt
                    bucket["completion_tokens"] += ct
                    bucket["prompt_cache_hit_tokens"] += hit
                    bucket["prompt_cache_miss_tokens"] += miss
                    bucket["total_tokens"] += tt
                    bucket["cost_usd"] += cost
                    if estimated:
                        bucket["estimated_requests"] += 1

                provider = _bucket_key(row, "provider")
                model = _bucket_key(row, "model")
                pm_key = f"{provider}::{model}"
                pm = buckets_provider_model.setdefault(
                    pm_key,
                    {
                        "provider": provider,
                        "model": model,
                        "label": f"{provider} / {model}",
                        "requests": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "prompt_cache_hit_tokens": 0,
                        "prompt_cache_miss_tokens": 0,
                        "total_tokens": 0,
                        "cost_usd": 0.0,
                    },
                )
                pm["requests"] += 1
                pm["prompt_tokens"] += pt
                pm["completion_tokens"] += ct
                pm["prompt_cache_hit_tokens"] += hit
                pm["prompt_cache_miss_tokens"] += miss
                pm["total_tokens"] += tt
                pm["cost_usd"] += cost

                family = _ai_provider_family(provider, model)
                fam = buckets_family.setdefault(
                    family,
                    {
                        "family": family,
                        "label": family_labels.get(family, family),
                        "label_ar": {
                            "deepseek": "DeepSeek (سحابة)",
                            "ollama_local": "Ollama / محلي (Qwen)",
                            "openai": "OpenAI",
                            "other": "أخرى",
                        }.get(family, family),
                        "requests": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "prompt_cache_hit_tokens": 0,
                        "prompt_cache_miss_tokens": 0,
                        "total_tokens": 0,
                        "cost_usd": 0.0,
                        "estimated_requests": 0,
                    },
                )
                fam["requests"] += 1
                fam["prompt_tokens"] += pt
                fam["completion_tokens"] += ct
                fam["prompt_cache_hit_tokens"] += hit
                fam["prompt_cache_miss_tokens"] += miss
                fam["total_tokens"] += tt
                fam["cost_usd"] += cost
                if estimated:
                    fam["estimated_requests"] += 1

                dept_key = _bucket_key(row, "department")
                if dept_key == "Internal Tools":
                    src_key = str(row.get("source") or "analysis").strip() or "analysis"
                    it = buckets_internal_tools.setdefault(
                        src_key,
                        {
                            "source": src_key,
                            "label_en": _usage_source_label(src_key, "en"),
                            "label_ar": _usage_source_label(src_key, "ar"),
                            "system_role": str(row.get("system_role") or "").strip() or "analyzer",
                            "requests": 0,
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "prompt_cache_hit_tokens": 0,
                            "prompt_cache_miss_tokens": 0,
                            "total_tokens": 0,
                            "cost_usd": 0.0,
                            "estimated_requests": 0,
                        },
                    )
                    it["requests"] += 1
                    it["prompt_tokens"] += pt
                    it["completion_tokens"] += ct
                    it["prompt_cache_hit_tokens"] += hit
                    it["prompt_cache_miss_tokens"] += miss
                    it["total_tokens"] += tt
                    it["cost_usd"] += cost
                    if estimated:
                        it["estimated_requests"] += 1

            def _finalize(items):
                out = []
                for item in items:
                    item = dict(item)
                    item["cost_usd"] = round(float(item.get("cost_usd") or 0), 6)
                    out.append(item)
                out.sort(key=lambda x: x.get("total_tokens") or 0, reverse=True)
                return out

            totals["cost_usd"] = round(float(totals["cost_usd"] or 0), 6)
            return {
                "from": start[:10],
                "to": end[:10],
                "currency": rates.get("currency") or "USD",
                "pricing_reference": rates.get("pricing_reference") or DEFAULT_AI_USAGE_RATES["pricing_reference"],
                "peak_hours_utc": rates.get("peak_hours_utc") or DEFAULT_AI_USAGE_RATES["peak_hours_utc"],
                "totals": totals,
                "by_department": _finalize(buckets_dept.values()),
                "by_provider": _finalize(buckets_provider.values()),
                "by_provider_model": _finalize(buckets_provider_model.values()),
                "by_family": _finalize(buckets_family.values()),
                "by_source": _finalize(buckets_source.values()),
                "internal_tools_breakdown": _finalize(buckets_internal_tools.values()),
                "source_labels": AI_USAGE_SOURCE_LABELS,
            }
    except Exception as e:
        logging.error(f"AI usage report failed: {e}")
        return empty

