import sqlite3
import json
from datetime import datetime, timezone

DB_FILE = 'operations_audit.db'

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS booking_field_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT NOT NULL,
                user_id TEXT,
                user_name TEXT,
                field_name TEXT NOT NULL,
                field_type TEXT,
                old_value TEXT,
                new_value TEXT,
                changed_at TEXT NOT NULL
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_booking_field_changes_record_time ON booking_field_changes(record_id, changed_at)')
        conn.commit()

def _json_dump(v):
    try:
        return json.dumps(v, ensure_ascii=False)
    except Exception:
        return json.dumps(str(v), ensure_ascii=False)

def log_change(record_id, field_name, field_type, old_value, new_value, user_id=None, user_name=None, changed_at=None):
    ts = changed_at or datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(
            '''
            INSERT INTO booking_field_changes
            (record_id, user_id, user_name, field_name, field_type, old_value, new_value, changed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                record_id,
                str(user_id) if user_id is not None else None,
                user_name,
                field_name,
                field_type,
                _json_dump(old_value),
                _json_dump(new_value),
                ts
            )
        )
        conn.commit()

def _json_load(s):
    if s is None:
        return None
    try:
        return json.loads(s)
    except Exception:
        return s

def get_changes(record_id, limit=50):
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            '''
            SELECT record_id, user_id, user_name, field_name, field_type, old_value, new_value, changed_at
            FROM booking_field_changes
            WHERE record_id = ?
            ORDER BY changed_at DESC, id DESC
            LIMIT ?
            ''',
            (record_id, int(limit))
        )
        rows = [dict(r) for r in c.fetchall()]
    for r in rows:
        r['old_value'] = _json_load(r.get('old_value'))
        r['new_value'] = _json_load(r.get('new_value'))
    return rows

def get_last_changes(record_ids):
    record_ids = [r for r in record_ids if r]
    if not record_ids:
        return {}
    placeholders = ",".join(["?"] * len(record_ids))
    q = f'''
        SELECT t.record_id, t.user_id, t.user_name, t.field_name, t.field_type, t.changed_at
        FROM booking_field_changes t
        INNER JOIN (
            SELECT record_id, MAX(changed_at) AS max_changed_at
            FROM booking_field_changes
            WHERE record_id IN ({placeholders})
            GROUP BY record_id
        ) x
        ON t.record_id = x.record_id AND t.changed_at = x.max_changed_at
    '''
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(q, record_ids)
        rows = [dict(r) for r in c.fetchall()]
    out = {}
    for r in rows:
        out[r['record_id']] = {
            "user_id": r.get("user_id"),
            "user_name": r.get("user_name"),
            "field_name": r.get("field_name"),
            "field_type": r.get("field_type"),
            "changed_at": r.get("changed_at")
        }
    return out

