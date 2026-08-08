import sqlite3
import json
import uuid
from datetime import datetime

from fts_paths import get_data_path
DB_FILE = get_data_path('chat_history.db')


def _utc_now():
    return datetime.utcnow().isoformat()


def _normalize_category(value):
    raw = str(value or "").strip().lower()
    if raw == "internal":
        return "internal"
    return "customer"


def init_db():
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                enabled INTEGER NOT NULL DEFAULT 0,
                category TEXT NOT NULL DEFAULT 'customer',
                trigger_type TEXT NOT NULL,
                trigger_config_json TEXT NOT NULL DEFAULT '{}',
                steps_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT,
                updated_at TEXT,
                last_run_at TEXT,
                last_error TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_runs (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                status TEXT NOT NULL,
                event_type TEXT,
                started_at TEXT,
                finished_at TEXT,
                event_payload_json TEXT,
                error TEXT
            )
            """
        )
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_automation_runs_workflow_id ON automation_runs(workflow_id)")
        except Exception:
            pass
        try:
            cols = [str(r[1]) for r in c.execute("PRAGMA table_info(automation_workflows)").fetchall()]
            if "category" not in cols:
                c.execute("ALTER TABLE automation_workflows ADD COLUMN category TEXT NOT NULL DEFAULT 'customer'")
        except Exception:
            pass
        conn.commit()


def list_workflows():
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            """
            SELECT id, name, description, enabled, category, trigger_type, trigger_config_json, steps_json,
                   created_at, updated_at, last_run_at, last_error
            FROM automation_workflows
            ORDER BY updated_at DESC, created_at DESC
            """
        )
        rows = c.fetchall() or []
    return [dict(r) for r in rows]


def get_workflow(workflow_id: str):
    if not workflow_id:
        return None
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            """
            SELECT id, name, description, enabled, category, trigger_type, trigger_config_json, steps_json,
                   created_at, updated_at, last_run_at, last_error
            FROM automation_workflows
            WHERE id = ?
            LIMIT 1
            """,
            (str(workflow_id),),
        )
        row = c.fetchone()
    return dict(row) if row else None


def upsert_workflow(payload: dict):
    payload = payload or {}
    wid = str(payload.get("id") or "").strip() or str(uuid.uuid4())
    name = str(payload.get("name") or "").strip() or "Untitled"
    description = str(payload.get("description") or "").strip()
    enabled = 1 if bool(payload.get("enabled")) else 0
    existing = get_workflow(wid)
    category = _normalize_category(payload.get("category") or ((existing or {}).get("category")) or "customer")
    trigger_type = str(payload.get("trigger_type") or "manual").strip()
    trigger_config = payload.get("trigger_config") or {}
    steps = payload.get("steps") or []
    if not isinstance(trigger_config, dict):
        trigger_config = {}
    if not isinstance(steps, list):
        steps = []

    now = _utc_now()
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        created_at = (existing.get("created_at") if existing else None) or now
        c.execute(
            """
            INSERT OR REPLACE INTO automation_workflows (
                id, name, description, enabled, category, trigger_type, trigger_config_json, steps_json,
                created_at, updated_at, last_run_at, last_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT last_run_at FROM automation_workflows WHERE id = ?), NULL),
                    COALESCE((SELECT last_error FROM automation_workflows WHERE id = ?), NULL))
            """,
            (
                wid,
                name,
                description,
                enabled,
                category,
                trigger_type,
                json.dumps(trigger_config, ensure_ascii=False),
                json.dumps(steps, ensure_ascii=False),
                created_at,
                now,
                wid,
                wid,
            ),
        )
        conn.commit()
    return get_workflow(wid)


def delete_workflow(workflow_id: str):
    if not workflow_id:
        return False
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute("DELETE FROM automation_runs WHERE workflow_id = ?", (str(workflow_id),))
        c.execute("DELETE FROM automation_workflows WHERE id = ?", (str(workflow_id),))
        conn.commit()
    return True


def set_enabled(workflow_id: str, enabled: bool):
    if not workflow_id:
        return None
    now = _utc_now()
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute(
            "UPDATE automation_workflows SET enabled = ?, updated_at = ? WHERE id = ?",
            (1 if enabled else 0, now, str(workflow_id)),
        )
        conn.commit()
    return get_workflow(workflow_id)


def touch_run_success(workflow_id: str):
    if not workflow_id:
        return
    now = _utc_now()
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute(
            "UPDATE automation_workflows SET last_run_at = ?, last_error = NULL, updated_at = ? WHERE id = ?",
            (now, now, str(workflow_id)),
        )
        conn.commit()


def touch_run_error(workflow_id: str, error: str):
    if not workflow_id:
        return
    now = _utc_now()
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute(
            "UPDATE automation_workflows SET last_run_at = ?, last_error = ?, updated_at = ? WHERE id = ?",
            (now, str(error or "")[:4000], now, str(workflow_id)),
        )
        conn.commit()


def create_run(workflow_id: str, event_type: str, payload: dict):
    run_id = str(uuid.uuid4())
    started_at = _utc_now()
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO automation_runs (id, workflow_id, status, event_type, started_at, finished_at, event_payload_json, error)
            VALUES (?, ?, ?, ?, ?, NULL, ?, NULL)
            """,
            (
                run_id,
                str(workflow_id),
                "running",
                str(event_type or ""),
                started_at,
                json.dumps(payload or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
    return run_id


def finish_run(run_id: str, status: str, error: str = None, payload: dict = None):
    if not run_id:
        return
    finished_at = _utc_now()
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        try:
            conn.execute("PRAGMA busy_timeout = 30000;")
        except Exception:
            pass
        c = conn.cursor()
        if payload is not None:
            c.execute(
                "UPDATE automation_runs SET status = ?, finished_at = ?, error = ?, event_payload_json = ? WHERE id = ?",
                (str(status or "success"), finished_at, str(error or "")[:4000] if error else None, json.dumps(payload, ensure_ascii=False), str(run_id)),
            )
        else:
            c.execute(
                "UPDATE automation_runs SET status = ?, finished_at = ?, error = ? WHERE id = ?",
                (str(status or "success"), finished_at, str(error or "")[:4000] if error else None, str(run_id)),
            )
        conn.commit()


def list_runs(workflow_id: str, limit: int = 50):
    try:
        limit_i = int(limit or 50)
    except Exception:
        limit_i = 50
    limit_i = max(1, min(limit_i, 200))
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            """
            SELECT id, workflow_id, status, event_type, started_at, finished_at, event_payload_json, error
            FROM automation_runs
            WHERE workflow_id = ?
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (str(workflow_id), limit_i),
        )
        rows = c.fetchall() or []
    return [dict(r) for r in rows]
