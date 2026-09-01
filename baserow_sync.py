"""
Airtable -> Baserow continuous sync (transition until Airtable is retired).

Direction: one-way Airtable → Baserow (Baserow is the operational UI).
Uses airtable_record_id for upsert. Skips formula/rollup/lookup/link fields.

Enable in config.json:
  "baserow": {
    "sync": {
      "enabled": true,
      "interval_sec": 60,
      "tables": ["List", "Add Guide Name & Phone", "Add Representative Name & Phone",
                 "Add Supplier Name & Phone", "Add Driver Name & Phone copy", "Products_Catalog"]
    }
  }
"""
from __future__ import annotations

import json
import logging
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
    load_state as load_migration_state,
    resolve_database_id,
)

logger = logging.getLogger(__name__)

SYNC_STATE_PATH = ROOT / "baserow_sync_state.json"
BATCH_SIZE = 15


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
    return s.replace("'", "\\'")


def fetch_modified_records(at: AirtableSource, table_name: str, since_iso: Optional[str], max_records: int = 0) -> List[dict]:
    table = at.api.table(at.base_id, table_name)
    kwargs: dict = {}
    if max_records and max_records > 0:
        kwargs["max_records"] = max_records
    if since_iso:
        formula = f"IS_AFTER(LAST_MODIFIED_TIME(), DATETIME_PARSE('{_airtable_escape(since_iso)}'))"
        kwargs["formula"] = formula
    return list(table.all(**kwargs))


def build_row_payload(
    rec: dict,
    fields_meta: List[dict],
    br_field_names: set[str],
    br: Optional[BaserowApi] = None,
    file_cache: Optional[dict] = None,
) -> dict:
    type_by_name = {str(f.get("name") or ""): str(f.get("type") or "") for f in fields_meta}
    row: dict = {"airtable_record_id": rec.get("id")}
    for k, v in (rec.get("fields") or {}).items():
        at_type = type_by_name.get(k, "singleLineText")
        if at_type in AUTO_COMPUTED_TYPES or at_type == "multipleRecordLinks":
            continue
        if k not in br_field_names:
            continue
        use_file = at_type == "multipleAttachments"
        val = format_for_baserow(
            v,
            at_type,
            br=br if use_file else None,
            file_cache=file_cache if use_file else None,
        )
        if val is not None and val != "":
            row[k] = val
    return row


def airtable_id_to_baserow_row_id(br: BaserowApi, table_id: int) -> Dict[str, int]:
    """Map airtable_record_id -> Baserow row id."""
    out: Dict[str, int] = {}
    page = 1
    while True:
        data = br._req(
            "GET",
            f"/api/database/rows/table/{table_id}/",
            params={"user_field_names": "true", "size": 200, "page": page},
        )
        for row in data.get("results") or []:
            aid = row.get("airtable_record_id")
            rid = row.get("id")
            if aid and rid:
                out[str(aid)] = int(rid)
        if not data.get("next"):
            break
        page += 1
    return out


def batch_update_rows(br: BaserowApi, table_id: int, items: List[dict]) -> Any:
    """items: [{id: baserow_row_id, ...fields}]"""
    path = f"/api/database/rows/table/{table_id}/batch/?user_field_names=true"
    return br._req("PATCH", path, json={"items": items})


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
        self._br: Optional[BaserowApi] = None
        self._at: Optional[AirtableSource] = None
        self._id_maps: Dict[str, Dict[str, int]] = {}
        self._field_cache: Dict[str, Tuple[List[dict], set[str]]] = {}

    def enabled(self) -> bool:
        return bool(self.br_cfg.get("enabled")) and bool(self.sync_cfg.get("enabled"))

    def interval_sec(self) -> int:
        try:
            return max(30, int(self.sync_cfg.get("interval_sec") or 60))
        except Exception:
            return 60

    def table_names(self) -> List[str]:
        tables = self.sync_cfg.get("tables")
        if isinstance(tables, list) and tables:
            return [str(t).strip() for t in tables if str(t).strip()]
        # Default: List + link deps from migration (excluding Grand_Tickets)
        return [
            "Products_Catalog",
            "Add Guide Name & Phone",
            "Add Representative Name & Phone",
            "Add Supplier Name & Phone",
            "Add Driver Name & Phone copy",
            "List",
        ]

    def _clients(self) -> Tuple[BaserowApi, AirtableSource, int]:
        if self._br is None:
            self._br = BaserowApi.from_config(self.br_cfg)
        if self._at is None:
            self._at = AirtableSource(self.cfg)
        db_id = self._resolve_database_id(self._br)
        return self._br, self._at, db_id

    def _resolve_database_id(self, br: BaserowApi) -> int:
        """Prefer config database_id if it has tables; else discover live."""
        configured = int(self.br_cfg.get("database_id") or 0)
        if configured:
            try:
                tables = br.list_tables(configured)
                if tables:
                    return configured
            except RuntimeError as exc:
                logger.warning("baserow.database_id=%s unusable (%s); rediscovering", configured, exc)
        try:
            return resolve_database_id(br, self.br_cfg)
        except RuntimeError:
            pass
        # Last resort: first database application in workspace
        for app in br.list_applications():
            if str(app.get("type") or "") == "database" and app.get("id"):
                db_id = int(app["id"])
                logger.info("Using Baserow database id=%s name=%s", db_id, app.get("name"))
                self.br_cfg["database_id"] = db_id
                return db_id
        raise RuntimeError("No Baserow database found — set baserow.database_id in config.json")

    def _live_tables_by_name(self, br: BaserowApi, db_id: int) -> Dict[str, int]:
        cache_key = f"db:{db_id}"
        cached = getattr(self, "_tables_cache", None)
        if isinstance(cached, dict) and cached.get("_key") == cache_key:
            return cached["map"]
        mapping: Dict[str, int] = {}
        for t in br.list_tables(db_id):
            name = str(t.get("name") or "").strip()
            if name and t.get("id"):
                mapping[name] = int(t["id"])
        self._tables_cache = {"_key": cache_key, "map": mapping}
        return mapping

    def _clear_stale_migration_id(self, name: str) -> None:
        try:
            from tools.migrate_airtable_to_baserow import save_state
            state = load_migration_state()
            info = (state.get("tables") or {}).get(name)
            if not isinstance(info, dict):
                return
            if info.get("baserow_table_id"):
                logger.warning(
                    "Clearing stale migration baserow_table_id=%s for '%s'",
                    info.get("baserow_table_id"),
                    name,
                )
                info["baserow_table_id"] = None
                info["complete"] = False
                state["tables"][name] = info
                save_state(state)
        except Exception as exc:
            logger.debug("Could not clear migration state for %s: %s", name, exc)

    def _resolve_table_id(self, br: BaserowApi, db_id: int, name: str) -> Optional[int]:
        """Resolve by live table name only (migration state IDs may be stale after recreate)."""
        live = self._live_tables_by_name(br, db_id)
        if name in live:
            return live[name]
        # Stale migration ids caused ERROR_TABLE_DOES_NOT_EXIST — clear them
        mig = (load_migration_state().get("tables") or {}).get(name) or {}
        if mig.get("baserow_table_id"):
            self._clear_stale_migration_id(name)
        if name == "List":
            lid = int(self.br_cfg.get("list_table_id") or 0)
            if lid and lid in set(live.values()):
                return lid
        return None

    def _fields_for(self, at: AirtableSource, br: BaserowApi, table_name: str, tid: int):
        if table_name in self._field_cache:
            return self._field_cache[table_name]
        at_tbl = at.table_by_name(table_name)
        fields_meta = list(at_tbl.get("fields") or [])
        try:
            br_names = {str(f.get("name") or "") for f in br.list_fields(tid)}
        except RuntimeError as exc:
            if "ERROR_TABLE_DOES_NOT_EXIST" in str(exc) or "HTTP 404" in str(exc):
                self._field_cache.pop(table_name, None)
                self._tables_cache = None
                self._clear_stale_migration_id(table_name)
                raise
            raise
        self._field_cache[table_name] = (fields_meta, br_names)
        return fields_meta, br_names

    def sync_table(self, table_name: str, force_full: bool = False) -> dict:
        br, at, db_id = self._clients()
        tid = self._resolve_table_id(br, db_id, table_name)
        if not tid:
            logger.warning(
                "Baserow sync skip '%s': table not found in database_id=%s (re-run migration if needed)",
                table_name,
                db_id,
            )
            return {"table": table_name, "status": "skipped", "reason": "baserow table not found"}

        state = load_sync_state()
        tstate = dict((state.get("tables") or {}).get(table_name) or {})
        since = None if force_full else (tstate.get("last_modified_cursor") or None)

        tick_started = _utc_now_iso()
        try:
            records = fetch_modified_records(at, table_name, since)
        except Exception as exc:
            logger.warning("Baserow sync fetch %s failed: %s", table_name, exc)
            return {"table": table_name, "status": "error", "message": str(exc)}

        if not records:
            tstate["last_run"] = tick_started
            tstate["last_result"] = "noop"
            state.setdefault("tables", {})[table_name] = tstate
            save_sync_state(state)
            return {"table": table_name, "status": "ok", "created": 0, "updated": 0, "fetched": 0}

        try:
            fields_meta, br_names = self._fields_for(at, br, table_name, tid)
        except RuntimeError as exc:
            if "ERROR_TABLE_DOES_NOT_EXIST" in str(exc) or "HTTP 404" in str(exc):
                logger.warning("Baserow sync skip '%s': table id=%s gone", table_name, tid)
                return {"table": table_name, "status": "skipped", "reason": "table does not exist"}
            raise
        if "airtable_record_id" not in br_names:
            return {
                "table": table_name,
                "status": "error",
                "message": "Baserow table missing airtable_record_id field",
            }

        id_map = self._id_maps.get(table_name)
        if id_map is None:
            try:
                id_map = airtable_id_to_baserow_row_id(br, tid)
            except RuntimeError as exc:
                if "ERROR_TABLE_DOES_NOT_EXIST" in str(exc) or "HTTP 404" in str(exc):
                    logger.warning("Baserow sync skip '%s': table id=%s gone", table_name, tid)
                    return {"table": table_name, "status": "skipped", "reason": "table does not exist"}
                raise
            self._id_maps[table_name] = id_map

        file_cache: dict = {}
        to_create: List[dict] = []
        to_update: List[dict] = []
        for rec in records:
            aid = str(rec.get("id") or "")
            payload = build_row_payload(rec, fields_meta, br_names, br=br, file_cache=file_cache)
            existing = id_map.get(aid)
            if existing:
                item = {"id": existing, **{k: v for k, v in payload.items() if k != "airtable_record_id"}}
                to_update.append(item)
            else:
                to_create.append(payload)

        created = 0
        updated = 0
        for i in range(0, len(to_create), BATCH_SIZE):
            chunk = to_create[i : i + BATCH_SIZE]
            br.batch_create_rows(tid, chunk)
            created += len(chunk)
            time.sleep(0.35)
        for i in range(0, len(to_update), BATCH_SIZE):
            chunk = to_update[i : i + BATCH_SIZE]
            batch_update_rows(br, tid, chunk)
            updated += len(chunk)
            time.sleep(0.35)

        if to_create:
            self._id_maps[table_name] = airtable_id_to_baserow_row_id(br, tid)

        tstate["last_run"] = tick_started
        tstate["last_modified_cursor"] = tick_started
        tstate["last_created"] = created
        tstate["last_updated"] = updated
        tstate["baserow_table_id"] = tid
        tstate["last_result"] = "ok"
        state.setdefault("tables", {})[table_name] = tstate
        save_sync_state(state)

        return {
            "table": table_name,
            "status": "ok",
            "fetched": len(records),
            "created": created,
            "updated": updated,
        }

    def tick(self) -> dict:
        if not self.enabled():
            return {"status": "disabled"}
        # Refresh live table list each tick (tables may be recreated)
        self._tables_cache = None
        self._field_cache = {}
        results = []
        for name in self.table_names():
            try:
                results.append(self.sync_table(name))
            except Exception as exc:
                msg = str(exc)
                if "ERROR_TABLE_DOES_NOT_EXIST" in msg or "HTTP 404" in msg:
                    logger.warning("Baserow sync skip '%s': %s", name, msg[:200])
                    results.append({"table": name, "status": "skipped", "reason": "table does not exist"})
                else:
                    logger.exception("Baserow sync table %s failed", name)
                    results.append({"table": name, "status": "error", "message": msg})
        return {"status": "ok", "results": results}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    syncer = AirtableBaserowSync()
    if not syncer.enabled():
        print("baserow.sync.enabled is false — set it in config.json")
        return 2
    out = syncer.tick()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
