"""
Airtable → Baserow continuous sync (transition until Airtable is retired).

- Auto-discovers tables that exist in BOTH Baserow and Airtable (by exact name).
- Only syncs tables already present in Baserow (never creates missing tables).
- Upserts via Baserow field `Record ID` (preferred) or `airtable_record_id`.
- Airtable is source of truth.

Config (config.json → baserow.sync):
  "enabled": true,
  "interval_sec": 90,
  "auto_discover": true,
  "id_field": "Record ID",
  "targets": [
    {"name": "main", "database_id": 5, "airtable_base_id": "appTp5YgSp9DV2HYc", "tables": "auto"}
  ]
"""
from __future__ import annotations

import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.migrate_airtable_to_baserow import (  # noqa: E402
    AUTO_COMPUTED_TYPES,
    BaserowApi,
    AirtableSource,
    format_for_baserow,
    load_config,
)

logger = logging.getLogger(__name__)

SYNC_STATE_PATH = ROOT / "baserow_sync_state.json"
BATCH_SIZE = 15
DELETE_BATCH = 100
SKIP_TABLE_SUBSTRINGS = ("import report", "airtable import")

# First matching Airtable/Baserow field used to link existing imported rows
NATURAL_KEY_CANDIDATES = [
    "Booking Nr.",
    "booking nr.",
    "Booking Number",
    "رقم التليفون",
    "Phone",
    "Customer Phone",
    "Product ID",
    "الاسم",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def load_sync_state() -> dict:
    if SYNC_STATE_PATH.is_file():
        try:
            return json.loads(SYNC_STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"tables": {}}


def save_sync_state(state: dict) -> None:
    SYNC_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _airtable_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def airtable_table_names(api_key: str, base_id: str) -> List[str]:
    import requests

    r = requests.get(
        f"https://api.airtable.com/v0/meta/bases/{base_id}/tables",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=120,
    )
    r.raise_for_status()
    return [str(t.get("name") or "") for t in (r.json().get("tables") or []) if t.get("name")]


def fetch_modified_records(
    at: AirtableSource, table_name: str, since_iso: Optional[str], max_records: int = 0
) -> List[dict]:
    table = at.api.table(at.base_id, table_name)
    kwargs: dict = {}
    if max_records and max_records > 0:
        kwargs["max_records"] = max_records
    if since_iso:
        formula = f"IS_AFTER(LAST_MODIFIED_TIME(), DATETIME_PARSE('{_airtable_escape(since_iso)}'))"
        kwargs["formula"] = formula
    return list(table.all(**kwargs))


def normalize_phone(value: Any) -> Optional[str]:
    """Return E.164-ish phone for Baserow phone_number fields, or None to skip."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in {"n/a", "na", "none", "-", "—"}:
        return None
    digits = re.sub(r"\D", "", s)
    if len(digits) < 7:
        return None
    if s.startswith("+"):
        return "+" + digits
    if len(digits) >= 10:
        return "+" + digits
    return None


def _decimal_places(field_def: dict, br_type: str) -> Optional[int]:
    if not field_def:
        return 0 if br_type in ("rating",) else None
    if "number_decimal_places" in field_def:
        try:
            return int(field_def["number_decimal_places"])
        except (TypeError, ValueError):
            pass
    if br_type == "rating":
        return 0
    return None


def normalize_email(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip().strip(",;").lower()
    if not s or s in {"n/a", "na", "none", "-", "—", "null", "undefined"}:
        return None
    # Take first address if multiple were pasted
    if "," in s or ";" in s or " " in s:
        for part in re.split(r"[,;\s]+", s):
            part = part.strip()
            if part and "@" in part:
                s = part
                break
    if "@" not in s or s.startswith("@") or s.endswith("@"):
        return None
    local, _, domain = s.partition("@")
    if not local or "." not in domain or " " in s:
        return None
    return s


def look_like_email_field(name: str, br_type: str) -> bool:
    if br_type == "email":
        return True
    n = (name or "").strip().lower()
    return any(x in n for x in ("email", "e-mail", "ايميل", "الإيميل", "الايميل"))


def look_like_phone_field(name: str, br_type: str) -> bool:
    if br_type == "phone_number":
        return True
    n = (name or "").strip().lower()
    return any(x in n for x in ("phone", "mobile", "whatsapp", "تليفون", "هاتف", "موبايل"))


def coerce_for_baserow_field(
    val: Any,
    br_type: str,
    field_def: Optional[dict] = None,
    field_name: str = "",
) -> Any:
    if val is None or val == "":
        return None
    if br_type == "phone_number" or look_like_phone_field(field_name, br_type):
        # Only coerce strictly when Baserow field is phone_number
        if br_type == "phone_number":
            return normalize_phone(val)
    if br_type in ("number", "rating"):
        dec = _decimal_places(field_def or {}, br_type)
        try:
            num = float(val)
        except (TypeError, ValueError):
            m = re.search(r"-?\d+(?:\.\d+)?", str(val))
            if not m:
                return None
            num = float(m.group(0))
        if dec == 0:
            return int(round(num))
        if dec is not None and dec > 0:
            return round(num, dec)
        return num
    if br_type == "email" or look_like_email_field(field_name, br_type):
        if br_type == "email":
            return normalize_email(val)
    if br_type == "url":
        s = str(val).strip()
        if not s.startswith(("http://", "https://")):
            if "." in s and " " not in s:
                s = "https://" + s
            else:
                return None
        return s
    return val


def build_row_payload(
    rec: dict,
    fields_meta: List[dict],
    br_field_names: set[str],
    br_field_types: Optional[Dict[str, str]] = None,
    br_field_defs: Optional[Dict[str, dict]] = None,
    br: Optional[BaserowApi] = None,
    file_cache: Optional[dict] = None,
    include_airtable_id: bool = True,
    id_field: Optional[str] = None,
) -> dict:
    type_by_name = {str(f.get("name") or ""): str(f.get("type") or "") for f in fields_meta}
    br_types = br_field_types or {}
    br_defs = br_field_defs or {}
    row: dict = {}
    id_col = id_field or resolve_id_field_name(br_field_names)
    if include_airtable_id and id_col and id_col in br_field_names:
        row[id_col] = rec.get("id")
    skip_write_names = set()
    if id_col:
        skip_write_names.add(id_col)
    # Don't overwrite Record ID from Airtable formula value if we already set from rec.id
    skip_write_names.update(ID_FIELD_CANDIDATES)
    for k, v in (rec.get("fields") or {}).items():
        if k in skip_write_names:
            continue
        at_type = type_by_name.get(k, "singleLineText")
        if at_type in AUTO_COMPUTED_TYPES or at_type == "multipleRecordLinks":
            continue
        if k not in br_field_names:
            continue
        br_type = br_types.get(k, "")
        use_file = at_type == "multipleAttachments"
        val = format_for_baserow(
            v,
            at_type,
            br=br if use_file else None,
            file_cache=file_cache if use_file else None,
        )
        if val is not None and val != "":
            val = coerce_for_baserow_field(val, br_type, br_defs.get(k), field_name=k)
        if val is not None and val != "":
            row[k] = val
    return row


def dedupe_updates(items: List[dict]) -> List[dict]:
    """Merge PATCH items by row id (last wins) — avoids ERROR_ROW_IDS_NOT_UNIQUE."""
    by_id: Dict[int, dict] = {}
    for item in items:
        rid = item.get("id")
        if rid is None:
            continue
        try:
            rid = int(rid)
        except (TypeError, ValueError):
            continue
        if rid in by_id:
            merged = {**by_id[rid], **item}
            merged["id"] = rid
            by_id[rid] = merged
        else:
            clean = dict(item)
            clean["id"] = rid
            by_id[rid] = clean
    return list(by_id.values())


def batch_create_rows_safe(br: BaserowApi, table_id: int, rows: List[dict]) -> Tuple[int, int]:
    if not rows:
        return 0, 0
    try:
        br.batch_create_rows(table_id, rows)
        return len(rows), 0
    except RuntimeError as exc:
        msg = str(exc)
        if "ERROR_REQUEST_BODY_VALIDATION" not in msg and "HTTP 400" not in msg:
            raise
        ok, skipped = 0, 0
        for row in rows:
            try:
                br.batch_create_rows(table_id, [row])
                ok += 1
            except RuntimeError as row_exc:
                skipped += 1
                logger.warning(
                    "Baserow sync skip create row (table=%s): %s",
                    table_id,
                    str(row_exc)[:240],
                )
        return ok, skipped


def batch_update_rows_safe(br: BaserowApi, table_id: int, items: List[dict]) -> Tuple[int, int]:
    items = dedupe_updates(items)
    if not items:
        return 0, 0
    try:
        batch_update_rows(br, table_id, items)
        return len(items), 0
    except RuntimeError as exc:
        msg = str(exc)
        # Always fall back to per-row for uniqueness / validation issues
        if (
            "ERROR_ROW_IDS_NOT_UNIQUE" in msg
            or "ERROR_REQUEST_BODY_VALIDATION" in msg
            or "HTTP 400" in msg
        ):
            ok, skipped = 0, 0
            for item in dedupe_updates(items):
                try:
                    batch_update_rows(br, table_id, [item])
                    ok += 1
                except RuntimeError as row_exc:
                    skipped += 1
                    logger.warning(
                        "Baserow sync skip update row id=%s (table=%s): %s",
                        item.get("id"),
                        table_id,
                        str(row_exc)[:240],
                    )
            return ok, skipped
        raise


SKIP_TABLE_SUBSTRINGS = ("import report", "airtable import")
# Preferred Baserow column holding Airtable record id (recXXXXXXXX)
ID_FIELD_CANDIDATES = ("Record ID", "airtable_record_id", "Airtable Record ID")


def resolve_id_field_name(br_field_names: set[str], preferred: Optional[str] = None) -> Optional[str]:
    if preferred and preferred in br_field_names:
        return preferred
    for name in ID_FIELD_CANDIDATES:
        if name in br_field_names:
            return name
    return None


def airtable_id_to_baserow_row_id(
    br: BaserowApi, table_id: int, id_field: str = "Record ID"
) -> Dict[str, int]:
    out: Dict[str, int] = {}
    page = 1
    while True:
        data = br._req(
            "GET",
            f"/api/database/rows/table/{table_id}/",
            params={"user_field_names": "true", "size": 200, "page": page},
        )
        for row in data.get("results") or []:
            aid = row.get(id_field)
            if not aid:
                # fallback legacy names on same row
                aid = row.get("airtable_record_id") or row.get("Record ID")
            rid = row.get("id")
            if aid and rid:
                out[str(aid).strip()] = int(rid)
        if not data.get("next"):
            break
        page += 1
    return out


def batch_update_rows(br: BaserowApi, table_id: int, items: List[dict]) -> Any:
    path = f"/api/database/rows/table/{table_id}/batch/?user_field_names=true"
    return br._req("PATCH", path, json={"items": items})


def ensure_id_field(
    br: BaserowApi,
    table_id: int,
    existing_names: set[str],
    preferred: str = "Record ID",
) -> Tuple[set[str], Optional[str]]:
    """Require an existing Record ID column — never invent empty ids (avoids duplicate rows)."""
    found = resolve_id_field_name(existing_names, preferred)
    if found:
        return existing_names, found
    logger.warning(
        "Baserow table id=%s missing '%s' (and legacy id fields) — skip until field is added",
        table_id,
        preferred,
    )
    return existing_names, None


def pick_natural_key(br_names: set[str], at_fields: List[dict]) -> Optional[str]:
    at_names = {str(f.get("name") or "") for f in at_fields}
    for cand in NATURAL_KEY_CANDIDATES:
        if cand in br_names and cand in at_names:
            return cand
    return None


def natural_key_index(br: BaserowApi, table_id: int, key_field: str) -> Dict[str, int]:
    """Map natural key value -> baserow row id (first wins)."""
    out: Dict[str, int] = {}
    page = 1
    while True:
        data = br._req(
            "GET",
            f"/api/database/rows/table/{table_id}/",
            params={"user_field_names": "true", "size": 200, "page": page},
        )
        for row in data.get("results") or []:
            val = row.get(key_field)
            if val is None or val == "":
                continue
            key = str(val).strip()
            if key and key not in out and row.get("id"):
                out[key] = int(row["id"])
        if not data.get("next"):
            break
        page += 1
    return out


def at_natural_value(rec: dict, key_field: str) -> str:
    v = (rec.get("fields") or {}).get(key_field)
    if v is None:
        return ""
    if isinstance(v, list):
        if not v:
            return ""
        v = v[0]
    return str(v).strip()


def list_all_row_ids(br: BaserowApi, table_id: int) -> List[int]:
    ids: List[int] = []
    page = 1
    while True:
        data = br._req(
            "GET",
            f"/api/database/rows/table/{table_id}/",
            params={"size": 200, "page": page},
        )
        for row in data.get("results") or []:
            rid = row.get("id")
            if rid is not None:
                ids.append(int(rid))
        total = data.get("count")
        if page == 1 or page % 10 == 0:
            logger.info(
                "  listing row ids table=%s page=%s collected=%s count=%s",
                table_id,
                page,
                len(ids),
                total,
            )
        if not data.get("next"):
            break
        page += 1
        time.sleep(0.05)
    return ids


def clear_baserow_table_rows(br: BaserowApi, table_id: int) -> int:
    """Delete all rows; keep columns/schema. Returns deleted count."""
    logger.info("  clearing rows for Baserow table id=%s ...", table_id)
    ids = list_all_row_ids(br, table_id)
    if not ids:
        logger.info("  table id=%s already empty", table_id)
        return 0
    deleted = 0
    total = len(ids)
    for i in range(0, total, DELETE_BATCH):
        chunk = ids[i : i + DELETE_BATCH]
        br._req(
            "POST",
            f"/api/database/rows/table/{table_id}/batch-delete/",
            json={"items": chunk},
        )
        deleted += len(chunk)
        if deleted == len(chunk) or deleted % 500 == 0 or deleted >= total:
            logger.info("  deleted %s/%s rows (table=%s)", deleted, total, table_id)
        time.sleep(0.25)
    return deleted


def set_sync_paused(paused: bool, reason: str = "") -> None:
    state = load_sync_state()
    state["paused"] = bool(paused)
    state["pause_reason"] = reason if paused else ""
    state["pause_updated_at"] = _utc_now_iso()
    save_sync_state(state)


def reset_table_cursors(state_keys: Optional[List[str]] = None) -> int:
    state = load_sync_state()
    tables = state.setdefault("tables", {})
    n = 0
    keys = list(tables.keys()) if state_keys is None else state_keys
    for key in keys:
        info = tables.get(key)
        if not isinstance(info, dict):
            continue
        info.pop("last_modified_cursor", None)
        info["last_result"] = "reset_for_full_sync"
        tables[key] = info
        n += 1
    save_sync_state(state)
    return n


class AirtableBaserowSync:
    def __init__(self, agent_or_cfg=None):
        if agent_or_cfg is None:
            self.cfg = load_config()
        elif isinstance(agent_or_cfg, dict):
            self.cfg = agent_or_cfg
        else:
            self.cfg = getattr(agent_or_cfg, "config", None) or load_config()
        self.br_cfg = dict(self.cfg.get("baserow") or {})
        self.sync_cfg = dict(self.br_cfg.get("sync") or {})
        self.at_cfg = dict(self.cfg.get("airtable") or {})
        self._br: Optional[BaserowApi] = None
        self._at_by_base: Dict[str, AirtableSource] = {}
        self._id_maps: Dict[str, Dict[str, int]] = {}
        self._nk_maps: Dict[str, Dict[str, int]] = {}
        self._field_cache: Dict[str, tuple] = {}
        self._at_names_cache: Dict[str, List[str]] = {}

    def enabled(self) -> bool:
        return bool(self.br_cfg.get("enabled")) and bool(self.sync_cfg.get("enabled"))

    def interval_sec(self) -> int:
        try:
            return max(30, int(self.sync_cfg.get("interval_sec") or 90))
        except Exception:
            return 90

    def _br_client(self) -> BaserowApi:
        if self._br is None:
            self._br = BaserowApi.from_config(self.br_cfg)
        return self._br

    def _at_client(self, base_id: str) -> AirtableSource:
        base_id = str(base_id or "").strip()
        if base_id not in self._at_by_base:
            cfg = dict(self.cfg)
            at = dict(self.at_cfg)
            at["base_id"] = base_id
            cfg["airtable"] = at
            self._at_by_base[base_id] = AirtableSource(cfg)
        return self._at_by_base[base_id]

    def targets(self) -> List[dict]:
        raw = self.sync_cfg.get("targets")
        if isinstance(raw, list) and raw:
            return [t for t in raw if isinstance(t, dict)]
        # Legacy single-target fallback
        db = int(self.br_cfg.get("database_id") or 0)
        base = str(self.at_cfg.get("base_id") or "")
        tables = self.sync_cfg.get("tables")
        return [
            {
                "name": "main",
                "database_id": db,
                "airtable_base_id": base,
                "tables": tables if tables else "auto",
            }
        ]

    def _airtable_names(self, base_id: str) -> List[str]:
        if base_id not in self._at_names_cache:
            self._at_names_cache[base_id] = airtable_table_names(
                str(self.at_cfg.get("api_key") or ""), base_id
            )
        return self._at_names_cache[base_id]

    def discover_tables(self, br: BaserowApi, database_id: int, airtable_base_id: str) -> List[Tuple[str, int]]:
        at_set = set(self._airtable_names(airtable_base_id))
        found: List[Tuple[str, int]] = []
        for t in br.list_tables(database_id):
            name = str(t.get("name") or "").strip()
            tid = int(t.get("id") or 0)
            if not name or not tid:
                continue
            low = name.lower()
            if any(s in low for s in SKIP_TABLE_SUBSTRINGS):
                continue
            if name in at_set:
                found.append((name, tid))
        return found

    def resolve_target_tables(self, target: dict) -> List[Tuple[str, int]]:
        br = self._br_client()
        db_id = int(target.get("database_id") or 0)
        base_id = str(target.get("airtable_base_id") or "").strip()
        if not db_id or not base_id:
            return []
        tables_cfg = target.get("tables", "auto")
        live = {str(t.get("name") or ""): int(t.get("id") or 0) for t in br.list_tables(db_id)}
        if tables_cfg == "auto" or tables_cfg is None or self.sync_cfg.get("auto_discover"):
            return self.discover_tables(br, db_id, base_id)
        names = [str(n).strip() for n in (tables_cfg or []) if str(n).strip()]
        out: List[Tuple[str, int]] = []
        for n in names:
            tid = live.get(n)
            if tid:
                out.append((n, tid))
            else:
                logger.warning("Sync target %s: table '%s' not in Baserow db %s", target.get("name"), n, db_id)
        return out

    def _cache_key(self, target_name: str, table_name: str) -> str:
        return f"{target_name}::{table_name}"

    def preferred_id_field(self) -> str:
        return str(self.sync_cfg.get("id_field") or "Record ID").strip() or "Record ID"

    def _fields_for(self, at: AirtableSource, br: BaserowApi, table_name: str, tid: int, cache_key: str):
        if cache_key in self._field_cache:
            return self._field_cache[cache_key]
        at_tbl = at.table_by_name(table_name)
        fields_meta = list(at_tbl.get("fields") or [])
        br_fields = list(br.list_fields(tid))
        br_names = {str(f.get("name") or "") for f in br_fields}
        br_names, id_field = ensure_id_field(br, tid, br_names, preferred=self.preferred_id_field())
        br_types = {str(f.get("name") or ""): str(f.get("type") or "") for f in br_fields}
        br_defs = {str(f.get("name") or ""): f for f in br_fields}
        if id_field and id_field not in br_types:
            br_types[id_field] = "text"
        self._field_cache[cache_key] = (fields_meta, br_names, br_types, br_defs, id_field)
        return fields_meta, br_names, br_types, br_defs, id_field

    def sync_table(
        self,
        target_name: str,
        airtable_base_id: str,
        table_name: str,
        tid: int,
        force_full: bool = False,
    ) -> dict:
        br = self._br_client()
        at = self._at_client(airtable_base_id)
        ck = self._cache_key(target_name, table_name)
        state_key = ck

        state = load_sync_state()
        tstate = dict((state.get("tables") or {}).get(state_key) or {})
        since = None if force_full else (tstate.get("last_modified_cursor") or None)
        tick_started = _utc_now_iso()

        try:
            records = fetch_modified_records(at, table_name, since)
        except Exception as exc:
            logger.warning("Baserow sync fetch %s/%s failed: %s", target_name, table_name, exc)
            return {"target": target_name, "table": table_name, "status": "error", "message": str(exc)}

        if not records:
            tstate["last_run"] = tick_started
            tstate["last_result"] = "noop"
            tstate["baserow_table_id"] = tid
            state.setdefault("tables", {})[state_key] = tstate
            save_sync_state(state)
            return {
                "target": target_name,
                "table": table_name,
                "status": "ok",
                "created": 0,
                "updated": 0,
                "fetched": 0,
            }

        try:
            fields_meta, br_names, br_types, br_defs, id_field = self._fields_for(
                at, br, table_name, tid, ck
            )
        except RuntimeError as exc:
            if "ERROR_TABLE_DOES_NOT_EXIST" in str(exc) or "HTTP 404" in str(exc):
                logger.warning("Baserow sync skip %s/%s: table gone", target_name, table_name)
                return {"target": target_name, "table": table_name, "status": "skipped", "reason": "missing"}
            raise

        if not id_field:
            return {
                "target": target_name,
                "table": table_name,
                "status": "skipped",
                "reason": "missing Record ID / airtable_record_id field",
            }

        id_map = self._id_maps.get(ck)
        if id_map is None:
            id_map = airtable_id_to_baserow_row_id(br, tid, id_field=id_field)
            self._id_maps[ck] = id_map

        nk_field = pick_natural_key(br_names, fields_meta)
        nk_map = self._nk_maps.get(ck)
        if nk_map is None and nk_field:
            nk_map = natural_key_index(br, tid, nk_field)
            self._nk_maps[ck] = nk_map
        nk_map = nk_map or {}

        file_cache: dict = {}
        to_create: List[dict] = []
        to_update: List[dict] = []
        skipped_rows = 0
        for rec in records:
            aid = str(rec.get("id") or "")
            payload = build_row_payload(
                rec,
                fields_meta,
                br_names,
                br_field_types=br_types,
                br_field_defs=br_defs,
                br=br,
                file_cache=file_cache,
                id_field=id_field,
            )
            existing = id_map.get(aid)
            if not existing and nk_field:
                nkv = at_natural_value(rec, nk_field)
                if nkv:
                    existing = nk_map.get(nkv)
                    if existing:
                        payload = {**payload, id_field: aid}
            if existing:
                item = {"id": existing, **payload}
                to_update.append(item)
                id_map[aid] = existing
            else:
                if len(payload) <= 1 and payload.get(id_field):
                    skipped_rows += 1
                    continue
                to_create.append(payload)

        created = 0
        updated = 0
        for i in range(0, len(to_create), BATCH_SIZE):
            chunk = to_create[i : i + BATCH_SIZE]
            ok, skip = batch_create_rows_safe(br, tid, chunk)
            created += ok
            skipped_rows += skip
            time.sleep(0.35)
        to_update = dedupe_updates(to_update)
        for i in range(0, len(to_update), BATCH_SIZE):
            chunk = to_update[i : i + BATCH_SIZE]
            ok, skip = batch_update_rows_safe(br, tid, chunk)
            updated += ok
            skipped_rows += skip
            time.sleep(0.35)

        if to_create or to_update:
            self._id_maps[ck] = airtable_id_to_baserow_row_id(br, tid, id_field=id_field)
            if nk_field:
                self._nk_maps[ck] = natural_key_index(br, tid, nk_field)

        tstate["last_run"] = tick_started
        tstate["last_modified_cursor"] = tick_started
        tstate["last_created"] = created
        tstate["last_updated"] = updated
        tstate["baserow_table_id"] = tid
        tstate["id_field"] = id_field
        tstate["natural_key"] = nk_field
        tstate["last_result"] = "ok"
        state.setdefault("tables", {})[state_key] = tstate
        save_sync_state(state)

        return {
            "target": target_name,
            "table": table_name,
            "status": "ok",
            "fetched": len(records),
            "created": created,
            "updated": updated,
            "skipped_rows": skipped_rows,
            "id_field": id_field,
            "natural_key": nk_field,
        }

    def tick(self) -> dict:
        if not self.enabled():
            return {"status": "disabled"}
        state = load_sync_state()
        if state.get("paused"):
            logger.info(
                "Baserow sync paused (%s) — skipping incremental tick",
                state.get("pause_reason") or "full resync",
            )
            return {"status": "paused", "reason": state.get("pause_reason")}
        self._field_cache = {}
        self._at_names_cache = {}
        self._id_maps = {}
        self._nk_maps = {}
        results = []
        for target in self.targets():
            tname = str(target.get("name") or "target")
            base_id = str(target.get("airtable_base_id") or "").strip()
            try:
                pairs = self.resolve_target_tables(target)
            except Exception as exc:
                logger.warning("Baserow sync discover %s failed: %s", tname, exc)
                results.append({"target": tname, "status": "error", "message": str(exc)})
                continue
            if not pairs:
                logger.warning("Baserow sync %s: no overlapping tables yet", tname)
                results.append({"target": tname, "status": "skipped", "reason": "no tables"})
                continue
            logger.info(
                "Baserow sync %s: %s table(s) — %s",
                tname,
                len(pairs),
                ", ".join(n for n, _ in pairs),
            )
            for table_name, tid in pairs:
                try:
                    results.append(self.sync_table(tname, base_id, table_name, tid))
                except Exception as exc:
                    msg = str(exc)
                    if "ERROR_TABLE_DOES_NOT_EXIST" in msg or "HTTP 404" in msg:
                        logger.warning("Baserow sync skip %s/%s: %s", tname, table_name, msg[:180])
                        results.append(
                            {
                                "target": tname,
                                "table": table_name,
                                "status": "skipped",
                                "reason": "missing",
                            }
                        )
                    elif (
                        "ERROR_REQUEST_BODY_VALIDATION" in msg
                        or "ERROR_ROW_IDS_NOT_UNIQUE" in msg
                        or "HTTP 400" in msg
                    ):
                        logger.warning("Baserow sync validation %s/%s: %s", tname, table_name, msg[:240])
                        results.append(
                            {
                                "target": tname,
                                "table": table_name,
                                "status": "partial",
                                "message": msg[:400],
                            }
                        )
                    else:
                        logger.exception("Baserow sync %s/%s failed", tname, table_name)
                        results.append(
                            {
                                "target": tname,
                                "table": table_name,
                                "status": "error",
                                "message": msg,
                            }
                        )
        return {"status": "ok", "results": results}

    def full_resync(self, clear_rows: bool = True, targets_filter: Optional[List[str]] = None) -> dict:
        """
        Airtable is source of truth:
        1) optionally clear Baserow rows (keep columns)
        2) reset cursors
        3) force full Airtable → Baserow sync for every overlapping table
        """
        if not self.enabled():
            return {"status": "disabled"}
        set_sync_paused(True, "full_resync_airtable_sot")
        summary: Dict[str, Any] = {"cleared": [], "synced": [], "errors": []}
        try:
            self._field_cache = {}
            self._at_names_cache = {}
            self._id_maps = {}
            self._nk_maps = {}
            br = self._br_client()
            for target in self.targets():
                tname = str(target.get("name") or "target")
                if targets_filter and tname not in targets_filter:
                    continue
                base_id = str(target.get("airtable_base_id") or "").strip()
                pairs = self.resolve_target_tables(target)
                logger.info("Full resync [%s]: %s tables", tname, len(pairs))
                for table_name, tid in pairs:
                    state_key = self._cache_key(tname, table_name)
                    try:
                        if clear_rows:
                            deleted = clear_baserow_table_rows(br, tid)
                            logger.info(
                                "Cleared %s/%s (id=%s): deleted %s rows",
                                tname,
                                table_name,
                                tid,
                                deleted,
                            )
                            summary["cleared"].append(
                                {
                                    "target": tname,
                                    "table": table_name,
                                    "table_id": tid,
                                    "deleted": deleted,
                                }
                            )
                            self._id_maps.pop(state_key, None)
                            self._nk_maps.pop(state_key, None)
                        reset_table_cursors([state_key])
                        result = self.sync_table(
                            tname, base_id, table_name, tid, force_full=True
                        )
                        summary["synced"].append(result)
                        logger.info(
                            "Full sync done %s/%s: created=%s updated=%s skipped=%s",
                            tname,
                            table_name,
                            result.get("created"),
                            result.get("updated"),
                            result.get("skipped_rows"),
                        )
                    except Exception as exc:
                        logger.exception("Full resync failed %s/%s", tname, table_name)
                        summary["errors"].append(
                            {
                                "target": tname,
                                "table": table_name,
                                "message": str(exc)[:500],
                            }
                        )
            summary["status"] = "ok" if not summary["errors"] else "partial"
            return summary
        finally:
            set_sync_paused(False)
            logger.info("Baserow incremental sync resumed (Airtable → Baserow)")


def main() -> int:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Airtable → Baserow sync (Airtable = source of truth)")
    parser.add_argument(
        "--full-resync",
        action="store_true",
        help="Clear Baserow rows (keep columns) then full sync from Airtable",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="With --full-resync: do not delete existing Baserow rows (upsert only)",
    )
    parser.add_argument(
        "--targets",
        nargs="*",
        default=None,
        help="Optional target names (e.g. main religious)",
    )
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Print overlapping tables and exit",
    )
    args = parser.parse_args()
    syncer = AirtableBaserowSync()
    if not syncer.enabled():
        print("baserow.sync.enabled is false — set it in config.json")
        return 2

    for t in syncer.targets():
        pairs = syncer.resolve_target_tables(t)
        print(f"[{t.get('name')}] db={t.get('database_id')} tables={len(pairs)}")
        for n, tid in pairs:
            print(f"  - {n} (id={tid})")
    if args.discover_only:
        return 0

    if args.full_resync:
        out = syncer.full_resync(
            clear_rows=not args.no_clear,
            targets_filter=args.targets,
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("status") == "ok" else 1

    out = syncer.tick()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("status") in ("ok", "paused") else 1


if __name__ == "__main__":
    raise SystemExit(main())
