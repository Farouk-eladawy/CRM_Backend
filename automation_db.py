import sqlite3
import json
import re
import secrets
import uuid
from datetime import datetime

from fts_paths import get_data_path
DB_FILE = get_data_path('chat_history.db')

# Keep in sync with company_tenancy.DEFAULT_COMPANY_ID (avoid hard import cycles at module load)
_DEFAULT_COMPANY_ID = "fts"

_WORKFLOW_SELECT_COLS = (
    "id, name, description, enabled, category, company_id, trigger_type, trigger_config_json, steps_json, "
    "created_at, updated_at, last_run_at, last_error"
)


def _utc_now():
    return datetime.utcnow().isoformat()


def _normalize_category(value):
    raw = str(value or "").strip().lower()
    if raw == "internal":
        return "internal"
    return "customer"


def normalize_workflow_company_id(value) -> str:
    cid = str(value or "").strip().lower()
    return cid or _DEFAULT_COMPANY_ID


def _parse_trigger_config(wf: dict) -> dict:
    raw = (wf or {}).get("trigger_config_json") or (wf or {}).get("trigger_config") or "{}"
    try:
        cfg = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        cfg = {}
    return cfg if isinstance(cfg, dict) else {}


def workflow_company_id(wf: dict) -> str:
    """Resolve company ownership for a workflow row (column → trigger_config → FTS default)."""
    if not isinstance(wf, dict):
        return _DEFAULT_COMPANY_ID
    cid = str(wf.get("company_id") or wf.get("companyId") or "").strip()
    if cid:
        return normalize_workflow_company_id(cid)
    cfg = _parse_trigger_config(wf)
    cid = str(cfg.get("webhook_company_id") or cfg.get("company_id") or "").strip()
    return normalize_workflow_company_id(cid)


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
                company_id TEXT NOT NULL DEFAULT 'fts',
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
            if "company_id" not in cols:
                c.execute(
                    "ALTER TABLE automation_workflows ADD COLUMN company_id TEXT NOT NULL DEFAULT 'fts'"
                )
                cols.append("company_id")
            # Backfill company_id from webhook_company_id when present
            if "company_id" in cols:
                rows = c.execute(
                    "SELECT id, company_id, trigger_config_json FROM automation_workflows"
                ).fetchall() or []
                for rid, cur_cid, tcfg_raw in rows:
                    want = normalize_workflow_company_id(cur_cid)
                    try:
                        cfg = json.loads(tcfg_raw) if isinstance(tcfg_raw, str) else (tcfg_raw or {})
                    except Exception:
                        cfg = {}
                    if isinstance(cfg, dict):
                        from_cfg = str(cfg.get("webhook_company_id") or cfg.get("company_id") or "").strip()
                        if from_cfg:
                            want = normalize_workflow_company_id(from_cfg)
                    if normalize_workflow_company_id(cur_cid) != want:
                        c.execute(
                            "UPDATE automation_workflows SET company_id = ? WHERE id = ?",
                            (want, rid),
                        )
            try:
                c.execute(
                    "CREATE INDEX IF NOT EXISTS idx_automation_workflows_company_id ON automation_workflows(company_id)"
                )
            except Exception:
                pass
        except Exception:
            pass
        conn.commit()


def list_workflows(company_id=None):
    """
    List workflows. When company_id is set, return only that tenant's rows.
    When None, return all (scheduler / internal engine use).
    """
    with sqlite3.connect(DB_FILE, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        cid = str(company_id or "").strip()
        if cid:
            cid_n = normalize_workflow_company_id(cid)
            c.execute(
                f"""
                SELECT {_WORKFLOW_SELECT_COLS}
                FROM automation_workflows
                WHERE lower(coalesce(nullif(trim(company_id), ''), 'fts')) = ?
                ORDER BY updated_at DESC, created_at DESC
                """,
                (cid_n,),
            )
        else:
            c.execute(
                f"""
                SELECT {_WORKFLOW_SELECT_COLS}
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
            f"""
            SELECT {_WORKFLOW_SELECT_COLS}
            FROM automation_workflows
            WHERE id = ?
            LIMIT 1
            """,
            (str(workflow_id),),
        )
        row = c.fetchone()
    return dict(row) if row else None


def normalize_webhook_owner(owner: str) -> str:
    s = re.sub(r"[^a-z0-9_-]+", "-", str(owner or "user").strip().lower())
    s = re.sub(r"-{2,}", "-", s).strip("-_")
    return (s or "user")[:64]


def normalize_webhook_slug(slug: str) -> str:
    s = re.sub(r"[^a-z0-9_-]+", "-", str(slug or "").strip().lower())
    s = re.sub(r"-{2,}", "-", s).strip("-_")
    return s[:80]


def new_webhook_public_token() -> str:
    """Opaque public token — never expose internal API host/path structure to end users."""
    return secrets.token_urlsafe(24)


def normalize_webhook_public_token(token: str) -> str:
    t = str(token or "").strip()
    # urlsafe base64 alphabet
    if not re.fullmatch(r"[A-Za-z0-9_\-]{16,128}", t):
        return ""
    return t


def find_workflow_by_webhook_token(token: str, enabled_only: bool = True):
    tok = normalize_webhook_public_token(token)
    if not tok:
        return None
    candidates = []
    for wf in list_workflows():
        if str(wf.get("trigger_type") or "").strip().lower() not in ("manual",):
            continue
        if enabled_only and not int(wf.get("enabled") or 0):
            continue
        cfg = _parse_trigger_config(wf)
        if normalize_webhook_public_token(str(cfg.get("webhook_public_token") or "")) == tok:
            candidates.append(wf)
    if not candidates:
        return None
    candidates.sort(key=lambda w: str(w.get("updated_at") or ""), reverse=True)
    return candidates[0]


def find_workflow_by_webhook(owner: str, slug: str, enabled_only: bool = True):
    """
    Resolve a canvas/manual workflow by per-user webhook path.
    Matching keys in trigger_config_json:
      - webhook_owner + webhook_slug
      - or webhook_path == "{owner}/{slug}"
    """
    owner_n = normalize_webhook_owner(owner)
    slug_n = normalize_webhook_slug(slug)
    if not owner_n or not slug_n:
        return None
    path = f"{owner_n}/{slug_n}"
    candidates = []
    for wf in list_workflows():
        if str(wf.get("trigger_type") or "").strip().lower() not in ("manual",):
            continue
        if enabled_only and not int(wf.get("enabled") or 0):
            continue
        cfg = _parse_trigger_config(wf)
        cfg_owner = normalize_webhook_owner(str(cfg.get("webhook_owner") or ""))
        cfg_slug = normalize_webhook_slug(str(cfg.get("webhook_slug") or ""))
        cfg_path = str(cfg.get("webhook_path") or "").strip().lower()
        if cfg_path == path or (cfg_owner == owner_n and cfg_slug == slug_n):
            candidates.append(wf)
    if not candidates:
        return None

    def _score(wf):
        cfg = _parse_trigger_config(wf)
        exact = 1 if str(cfg.get("webhook_path") or "").strip().lower() == path else 0
        return (exact, str(wf.get("updated_at") or ""))

    candidates.sort(key=_score, reverse=True)
    return candidates[0]


def list_webhooks_for_owner(owner: str):
    """List webhook endpoints owned by a user (from workflows + for picker reuse)."""
    owner_n = normalize_webhook_owner(owner)
    out = []
    seen = set()
    for wf in list_workflows():
        if str(wf.get("trigger_type") or "").strip().lower() != "manual":
            continue
        cfg = _parse_trigger_config(wf)
        cfg_owner = normalize_webhook_owner(str(cfg.get("webhook_owner") or ""))
        cfg_slug = normalize_webhook_slug(str(cfg.get("webhook_slug") or ""))
        if not cfg_slug:
            continue
        if cfg_owner and cfg_owner != owner_n:
            continue
        # Legacy rows without owner: skip (avoid leaking across users)
        if not cfg_owner:
            continue
        path = str(cfg.get("webhook_path") or f"{cfg_owner}/{cfg_slug}").strip().lower()
        if path in seen:
            continue
        seen.add(path)
        out.append(
            {
                "id": f"wfhook_{wf.get('id')}",
                "type": "webhook",
                "label": f"{wf.get('name') or cfg_slug} · {cfg_slug}",
                "status": "connected" if int(wf.get("enabled") or 0) else "ready",
                "source": "workflow",
                "workflow_id": wf.get("id"),
                "hints": {
                    "slug": cfg_slug,
                    "owner": cfg_owner,
                    "path": path,
                    "company_id": str(cfg.get("webhook_company_id") or ""),
                    "company_slug": str(cfg.get("webhook_company_slug") or ""),
                    "token": str(cfg.get("webhook_public_token") or ""),
                    "url_path": (
                        f"/h/{cfg.get('webhook_public_token')}"
                        if cfg.get("webhook_public_token")
                        else (
                            f"/api/hooks/{cfg.get('webhook_company_slug')}/{cfg_owner}/{cfg_slug}"
                            if cfg.get("webhook_company_slug")
                            else f"/api/automation/webhook/{cfg_owner}/{cfg_slug}"
                        )
                    ),
                },
            }
        )
    return out


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

    # Tenant ownership — never migrate an existing workflow to another company via upsert
    company_id = normalize_workflow_company_id(
        payload.get("company_id")
        or payload.get("companyId")
        or trigger_config.get("webhook_company_id")
        or (existing.get("company_id") if existing else None)
        or _DEFAULT_COMPANY_ID
    )
    if existing:
        existing_cid = workflow_company_id(existing)
        if existing_cid != company_id:
            raise ValueError(f"workflow_company_mismatch:{existing_cid}")
        company_id = existing_cid
    trigger_config = dict(trigger_config)
    trigger_config["webhook_company_id"] = company_id

    # Normalize per-user webhook path so URLs never collide across users
    if str(trigger_type).lower() == "manual":
        owner = normalize_webhook_owner(str(trigger_config.get("webhook_owner") or ""))
        slug = normalize_webhook_slug(str(trigger_config.get("webhook_slug") or ""))
        if slug:
            if not owner:
                owner = "user"
            trigger_config["webhook_owner"] = owner
            trigger_config["webhook_slug"] = slug
            trigger_config["webhook_path"] = f"{owner}/{slug}"
            # Stable opaque public token (gateway URL) — do not recycle across workflows
            existing_tok = normalize_webhook_public_token(str(trigger_config.get("webhook_public_token") or ""))
            if not existing_tok and existing:
                prev_cfg = _parse_trigger_config(existing)
                existing_tok = normalize_webhook_public_token(str(prev_cfg.get("webhook_public_token") or ""))
            if not existing_tok:
                # Ensure uniqueness across workflows
                for _ in range(8):
                    cand = new_webhook_public_token()
                    clash = find_workflow_by_webhook_token(cand, enabled_only=False)
                    if not clash or str(clash.get("id") or "") == wid:
                        existing_tok = cand
                        break
                existing_tok = existing_tok or new_webhook_public_token()
            trigger_config["webhook_public_token"] = existing_tok
            # Block another workflow of same owner from stealing the slug (unless same id)
            existing_hook = find_workflow_by_webhook(owner, slug, enabled_only=False)
            if existing_hook and str(existing_hook.get("id") or "") != wid:
                raise ValueError(f"webhook_slug_in_use:{owner}/{slug}")
        else:
            trigger_config.pop("webhook_slug", None)
            trigger_config.pop("webhook_path", None)

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
                id, name, description, enabled, category, company_id, trigger_type, trigger_config_json, steps_json,
                created_at, updated_at, last_run_at, last_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT last_run_at FROM automation_workflows WHERE id = ?), NULL),
                    COALESCE((SELECT last_error FROM automation_workflows WHERE id = ?), NULL))
            """,
            (
                wid,
                name,
                description,
                enabled,
                category,
                company_id,
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
