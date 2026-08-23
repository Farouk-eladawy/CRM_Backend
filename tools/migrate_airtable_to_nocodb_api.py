"""
Migrate Airtable -> NocoDB via API (schema-aware, exact table/field names).

Usage (from OpenClaw_Version):
  python tools/migrate_airtable_to_nocodb_api.py discover
  python tools/migrate_airtable_to_nocodb_api.py airtable-schema
  python tools/migrate_airtable_to_nocodb_api.py reset --yes
  python tools/migrate_airtable_to_nocodb_api.py migrate --tables List --dry-run
  python tools/migrate_airtable_to_nocodb_api.py migrate --config-tables
  python tools/migrate_airtable_to_nocodb_api.py migrate --link-deps --skip-existing
  python tools/migrate_airtable_to_nocodb_api.py link-relations --tables List
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

STATE_PATH = ROOT / "nocodb_migration_state.json"
BULK_CHUNK = 50
CREATE_BATCH = 25
ADD_COLUMN_DELAY = 0.05

# Tables linked from List (migrate these before link-relations)
LIST_LINK_TARGETS = [
    "Add Driver Name & Phone copy",
    "Add Guide Name & Phone",
    "Add Representative Name & Phone",
    "Add Supplier Name & Phone",
    "Conversations",
    "Grand_Tickets",
    "Products_Catalog",
]

SKIP_AIRTABLE_TYPES = {"button"}
NON_INSERT_AIRTABLE_TYPES = {
    "button",
    "createdTime",
    "lastModifiedTime",
    "createdBy",
    "lastModifiedBy",
}

AIRTABLE_TO_NOCO: Dict[str, str] = {
    "singleLineText": "SingleLineText",
    "email": "Email",
    "url": "URL",
    "multilineText": "LongText",
    "richText": "LongText",
    "number": "Number",
    "currency": "Currency",
    "percent": "Percent",
    "rating": "Rating",
    "date": "Date",
    "dateTime": "DateTime",
    "checkbox": "Checkbox",
    "phoneNumber": "PhoneNumber",
    "singleSelect": "SingleSelect",
    "multipleSelects": "MultiSelect",
    "multipleAttachments": "LongText",
    "multipleRecordLinks": "LongText",
    "formula": "LongText",
    "rollup": "LongText",
    "lookup": "LongText",
    "count": "Number",
    "autonumber": "Number",
    "barcode": "Barcode",
    "duration": "Duration",
    "button": "Button",
    "createdTime": "DateTime",
    "lastModifiedTime": "DateTime",
    "createdBy": "SingleLineText",
    "lastModifiedBy": "SingleLineText",
    "externalSyncSource": "SingleLineText",
    "aiText": "LongText",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_config() -> dict:
    with open(ROOT / "config.json", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: dict) -> None:
    with open(ROOT / "config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_state() -> dict:
    if STATE_PATH.is_file():
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"version": 2, "tables": {}}


def save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def safe_table_name(title: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", title.strip()).strip("_").lower()
    return s or "table"


def safe_column_name(title: str, used: set[str]) -> str:
    base = re.sub(r"[^a-zA-Z0-9_]+", "_", title.strip()).strip("_").lower() or "field"
    name = base
    i = 2
    while name in used:
        name = f"{base}_{i}"
        i += 1
    used.add(name)
    return name


def select_dtxp(field: dict) -> Optional[str]:
    options = field.get("options") or {}
    choices = options.get("choices") or []
    names: List[str] = []
    for c in choices:
        label = str(c.get("name") or "").strip()
        if label:
            names.append(label.replace("'", ""))
    if not names:
        return None
    return ",".join(names)


def unique_title(title: str, used_titles: set[str]) -> str:
    base = str(title or "Field").strip() or "Field"
    if base not in used_titles:
        used_titles.add(base)
        return base
    i = 2
    while f"{base} ({i})" in used_titles:
        i += 1
    unique = f"{base} ({i})"
    used_titles.add(unique)
    return unique


def airtable_field_to_column(field: dict, used_names: set[str], used_titles: set[str]) -> dict:
    at_type = str(field.get("type") or "singleLineText")
    uidt = AIRTABLE_TO_NOCO.get(at_type, "SingleLineText")
    if at_type in ("singleSelect", "multipleSelects"):
        uidt = "SingleLineText"
    title = unique_title(str(field.get("name") or "Field"), used_titles)
    col: dict = {
        "column_name": safe_column_name(title, used_names),
        "title": title,
        "uidt": uidt,
    }
    dtxp = select_dtxp(field)
    if dtxp and uidt in ("SingleSelect", "MultiSelect"):
        col["dtxp"] = dtxp
    return col


def convert_value(at_type: str, value: Any) -> Any:
    if value is None:
        return None
    if at_type == "checkbox":
        return bool(value)
    if at_type in ("number", "currency", "percent", "rating", "count", "autonumber"):
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None
    if at_type == "multipleRecordLinks":
        if isinstance(value, list):
            return ", ".join(str(x) for x in value)
        return str(value)
    if at_type == "multipleAttachments":
        if isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, dict):
                    parts.append(item.get("url") or item.get("filename") or json.dumps(item))
                else:
                    parts.append(str(item))
            return "\n".join(parts) if parts else None
        return str(value)
    if at_type in ("multipleSelects", "singleSelect"):
        if isinstance(value, list):
            return ", ".join(str(x) for x in value)
        return str(value)
    if at_type in ("createdBy", "lastModifiedBy"):
        if isinstance(value, dict):
            return value.get("email") or value.get("name") or json.dumps(value)
        return str(value)
    if isinstance(value, list):
        if all(isinstance(x, str) for x in value):
            return ", ".join(value)
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return value


class NocoDbApi:
    def __init__(self, api_url: str, token: str):
        self.base_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "xc-token": token,
            "Content-Type": "application/json",
        })

    def _req(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        resp = self.session.request(method, url, timeout=180, **kwargs)
        if not resp.ok:
            raise RuntimeError(f"NocoDB {method} {path} -> HTTP {resp.status_code}: {resp.text[:800]}")
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def list_bases(self) -> List[dict]:
        data = self._req("GET", "/api/v2/meta/bases")
        return list(data.get("list") or data or [])

    def list_tables(self, base_id: str) -> List[dict]:
        data = self._req("GET", f"/api/v2/meta/bases/{base_id}/tables")
        return list(data.get("list") or [])

    def get_table(self, table_id: str) -> dict:
        return self._req("GET", f"/api/v2/meta/tables/{table_id}")

    def delete_table(self, table_id: str) -> None:
        self._req("DELETE", f"/api/v2/meta/tables/{table_id}")

    def create_table(self, base_id: str, title: str, columns: List[dict]) -> dict:
        body = {
            "title": title,
            "table_name": safe_table_name(title),
            "columns": columns,
        }
        return self._req("POST", f"/api/v2/meta/bases/{base_id}/tables", json=body)

    def add_column(self, table_id: str, column: dict) -> None:
        self._req("POST", f"/api/v2/meta/tables/{table_id}/columns", json=column)

    def bulk_insert(self, table_id: str, rows: List[dict]) -> Any:
        return self._req("POST", f"/api/v2/tables/{table_id}/records", json=rows)

    def find_table_by_title(self, base_id: str, title: str) -> Optional[dict]:
        for t in self.list_tables(base_id):
            if (t.get("title") or "") == title:
                return t
        return None

    def delete_column(self, column_id: str) -> None:
        self._req("DELETE", f"/api/v1/db/meta/columns/{column_id}")

    def get_column_by_title(self, table_id: str, title: str) -> Optional[dict]:
        for col in self.get_table(table_id).get("columns") or []:
            if str(col.get("title") or "") == title:
                return col
        return None

    def find_link_column(self, source_table_id: str, target_table_id: str, title: str) -> Optional[dict]:
        table = self.get_table(source_table_id)
        by_title = self.get_column_by_title(source_table_id, title)
        if by_title and str(by_title.get("uidt") or "") == "LinkToAnotherRecord":
            return by_title
        for col in table.get("columns") or []:
            if str(col.get("uidt") or "") != "LinkToAnotherRecord":
                continue
            opts = col.get("colOptions") or {}
            related = str(
                opts.get("fk_related_model_id")
                or opts.get("fk_target_model_id")
                or ""
            )
            if related == target_table_id:
                return col
        return None

    def create_link_column(
        self,
        source_table_id: str,
        target_table_id: str,
        title: str,
        relation_type: str = "mm",
    ) -> dict:
        body = {
            "title": title,
            "uidt": "LinkToAnotherRecord",
            "parentId": target_table_id,
            "childId": source_table_id,
            "type": relation_type,
        }
        return self._req("POST", f"/api/v2/meta/tables/{source_table_id}/columns", json=body)

    def fetch_all_records(self, table_id: str, fields: Optional[List[str]] = None) -> List[dict]:
        rows: List[dict] = []
        offset = 0
        limit = 100
        while True:
            params: dict = {"limit": limit, "offset": offset}
            if fields:
                params["fields"] = ",".join(fields)
            data = self._req("GET", f"/api/v2/tables/{table_id}/records", params=params)
            batch = list(data.get("list") or [])
            if not batch:
                break
            rows.extend(batch)
            page = data.get("pageInfo") or {}
            if page.get("isLastPage"):
                break
            offset += limit
        return rows

    def link_records(
        self,
        source_table_id: str,
        link_column_id: str,
        source_row_id: int,
        target_row_ids: List[int],
    ) -> None:
        if not target_row_ids:
            return
        payload = [{"Id": rid} for rid in target_row_ids]
        self._req(
            "POST",
            f"/api/v2/tables/{source_table_id}/links/{link_column_id}/records/{source_row_id}",
            json=payload,
        )


class AirtableBase:
    def __init__(self, api_key: str, base_id: str):
        self.api_key = api_key
        self.base_id = base_id
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})
        self._schema: Optional[List[dict]] = None
        from pyairtable import Api
        self.api = Api(api_key)

    def fetch_schema(self) -> List[dict]:
        if self._schema is None:
            data = self._req("GET", f"/meta/bases/{self.base_id}/tables")
            self._schema = list(data.get("tables") or [])
        return self._schema

    def _req(self, method: str, path: str, **kwargs) -> Any:
        url = f"https://api.airtable.com/v0{path}"
        resp = self.session.request(method, url, timeout=180, **kwargs)
        if not resp.ok:
            raise RuntimeError(f"Airtable {method} {path} -> HTTP {resp.status_code}: {resp.text[:800]}")
        return resp.json()

    def table_by_name(self, name: str) -> dict:
        for t in self.fetch_schema():
            if t.get("name") == name:
                return t
        raise RuntimeError(f"Airtable table not found: {name}")

    def fetch_records(self, table_name: str, max_records: int = 0) -> List[dict]:
        table = self.api.table(self.base_id, table_name)
        kwargs: dict = {}
        if max_records and max_records > 0:
            kwargs["max_records"] = max_records
        return list(table.all(**kwargs))


def config_table_names(cfg: dict) -> List[str]:
    tables = (cfg.get("airtable") or {}).get("tables") or {}
    names = []
    for key, val in tables.items():
        if not val or str(val).startswith("tbl"):
            continue
        names.append(str(val))
    if "List" not in names:
        names.insert(0, "List")
    return names


def build_columns_from_airtable(fields: List[dict]) -> List[dict]:
    used: set[str] = set()
    used_titles: set[str] = set()
    cols = [{
        "column_name": "airtable_record_id",
        "title": "airtable_record_id",
        "uidt": "SingleLineText",
        "pk": True,
    }]
    used.add("airtable_record_id")
    used_titles.add("airtable_record_id")
    for field in fields:
        if str(field.get("type") or "") in SKIP_AIRTABLE_TYPES:
            continue
        cols.append(airtable_field_to_column(field, used, used_titles))
    return cols


def writable_column_titles(nc: "NocoDbApi", table_id: str) -> set[str]:
    meta = nc.get_table(table_id)
    titles: set[str] = set()
    for col in meta.get("columns") or []:
        if col.get("system"):
            continue
        if col.get("virtual"):
            continue
        if col.get("readonly"):
            continue
        if str(col.get("uidt") or "") in ("Button",):
            continue
        title = str(col.get("title") or "")
        if title:
            titles.add(title)
    return titles


def create_nocodb_table(nc: NocoDbApi, base_id: str, airtable_table: dict) -> str:
    title = str(airtable_table["name"])
    fields = list(airtable_table.get("fields") or [])
    all_cols = build_columns_from_airtable(fields)

    first = all_cols[:CREATE_BATCH]
    created = nc.create_table(base_id, title, first)
    table_id = str(created["id"])
    print(f"  created table '{title}' id={table_id} columns={len(first)}/{len(all_cols)}")

    for col in all_cols[CREATE_BATCH:]:
        nc.add_column(table_id, col)
        time.sleep(ADD_COLUMN_DELAY)
    if len(all_cols) > CREATE_BATCH:
        print(f"  added {len(all_cols) - CREATE_BATCH} more columns")
    return table_id


def record_to_row(
    record: dict,
    field_types: Dict[str, str],
    allowed_columns: set[str],
) -> dict:
    row: dict = {}
    rid = str(record.get("id") or "")
    if "airtable_record_id" in allowed_columns:
        row["airtable_record_id"] = rid
    for name, val in (record.get("fields") or {}).items():
        if name not in allowed_columns:
            continue
        at_type = field_types.get(name, "singleLineText")
        if at_type in NON_INSERT_AIRTABLE_TYPES:
            continue
        row[name] = convert_value(at_type, val)
    return row


def build_record_map(nc: NocoDbApi, table_id: str) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for row in nc.fetch_all_records(table_id):
        rid = str(row.get("airtable_record_id") or "")
        noco_id = row.get("Id")
        if rid and noco_id is not None:
            mapping[rid] = int(noco_id)
    return mapping


def airtable_id_to_table_name(schema: List[dict]) -> Dict[str, str]:
    return {str(t["id"]): str(t["name"]) for t in schema}


def link_relation_type(field: dict) -> str:
    opts = field.get("options") or {}
    if opts.get("prefersSingleRecordLink"):
        return "bt"
    return "mm"


def cmd_discover(nc: NocoDbApi) -> int:
    for b in nc.list_bases():
        bid = b.get("id")
        print(f"Base: {b.get('title')}  id={bid}")
        for t in nc.list_tables(bid):
            print(f"  Table: {t.get('title')}  id={t.get('id')}")
    return 0


def cmd_link_relations(
    nc: NocoDbApi,
    at: AirtableBase,
    base_id: str,
    table_names: List[str],
    state: dict,
    dry_run: bool,
) -> int:
    schema = at.fetch_schema()
    at_id_to_name = airtable_id_to_table_name(schema)
    schema_by_name = {t["name"]: t for t in schema}
    tracked = state.get("tables") or {}

    record_maps: Dict[str, Dict[str, int]] = {}
    for name, info in tracked.items():
        tid = str((info or {}).get("nocodb_table_id") or "")
        if not tid:
            continue
        print(f"Building record map for {name}...")
        record_maps[name] = build_record_map(nc, tid)
        print(f"  {len(record_maps[name])} records")

    for table_name in table_names:
        if table_name not in tracked:
            print(f"Skip {table_name}: not migrated yet")
            continue
        source_tid = str(tracked[table_name]["nocodb_table_id"])
        at_table = schema_by_name.get(table_name) or {}
        link_fields = [
            f for f in (at_table.get("fields") or [])
            if f.get("type") == "multipleRecordLinks"
        ]
        if not link_fields:
            print(f"No link fields on {table_name}")
            continue

        print(f"\n== Link relations: {table_name} ({len(link_fields)} fields) ==")
        source_map = record_maps.get(table_name) or {}

        for field in link_fields:
            field_name = str(field["name"])
            target_at_id = str((field.get("options") or {}).get("linkedTableId") or "")
            target_name = at_id_to_name.get(target_at_id)
            if not target_name or target_name not in tracked:
                print(f"  skip {field_name}: target '{target_name}' not migrated")
                continue

            target_tid = str(tracked[target_name]["nocodb_table_id"])
            target_map = record_maps.get(target_name) or {}
            rel_type = link_relation_type(field)
            print(f"  {field_name} -> {target_name} ({rel_type})")

            if dry_run:
                continue

            existing_col = nc.get_column_by_title(source_tid, field_name)
            if existing_col and str(existing_col.get("uidt") or "") != "LinkToAnotherRecord":
                try:
                    nc.delete_column(str(existing_col["id"]))
                except RuntimeError:
                    pass
                existing_col = None
                time.sleep(0.2)

            link_col = nc.find_link_column(source_tid, target_tid, field_name)
            if not link_col:
                try:
                    nc.create_link_column(source_tid, target_tid, field_name, rel_type)
                    time.sleep(0.3)
                except RuntimeError as exc:
                    print(f"    create link column note: {exc}")
                link_col = nc.find_link_column(source_tid, target_tid, field_name)

            if not link_col:
                print(f"    failed to create link column {field_name}")
                continue
            link_col_id = str(link_col["id"])

            linked = 0
            skipped = 0
            records = at.fetch_records(table_name, max_records=0)
            for rec in records:
                at_source_id = str(rec.get("id") or "")
                source_noco_id = source_map.get(at_source_id)
                if not source_noco_id:
                    skipped += 1
                    continue
                raw_links = (rec.get("fields") or {}).get(field_name)
                if not raw_links:
                    continue
                if not isinstance(raw_links, list):
                    raw_links = [raw_links]
                target_ids = []
                for at_target_id in raw_links:
                    noco_target = target_map.get(str(at_target_id))
                    if noco_target:
                        target_ids.append(noco_target)
                if not target_ids:
                    continue
                try:
                    nc.link_records(source_tid, link_col_id, source_noco_id, target_ids)
                    linked += 1
                except RuntimeError as exc:
                    print(f"    link error {at_source_id}: {exc}")
                if linked and linked % 500 == 0:
                    print(f"    linked {linked} rows...")
                    time.sleep(0.1)
            print(f"    done: {linked} rows linked, {skipped} source rows missing")

    print("\nLink relations complete.")
    return 0
    for b in nc.list_bases():
        bid = b.get("id")
        print(f"Base: {b.get('title')}  id={bid}")
        for t in nc.list_tables(bid):
            print(f"  Table: {t.get('title')}  id={t.get('id')}")
    return 0


def cmd_airtable_schema(at: AirtableBase, only: Optional[List[str]] = None) -> int:
    for t in at.fetch_schema():
        name = t.get("name")
        if only and name not in only:
            continue
        fields = t.get("fields") or []
        print(f"{name}: {len(fields)} fields")
        for f in fields[:6]:
            print(f"  - {f.get('name')} ({f.get('type')})")
        if len(fields) > 6:
            print(f"  ... +{len(fields) - 6} more")
    return 0


def cmd_reset(nc: NocoDbApi, base_id: str, state: dict, table_names: Optional[List[str]], yes: bool) -> int:
    to_delete: List[Tuple[str, str]] = []
    tracked = state.get("tables") or {}
    for name, info in tracked.items():
        tid = str((info or {}).get("nocodb_table_id") or "")
        if tid:
            to_delete.append((name, tid))

    if table_names:
        for name in table_names:
            existing = nc.find_table_by_title(base_id, name)
            if existing:
                to_delete.append((name, str(existing["id"])))

    # unique by table id
    seen = set()
    unique: List[Tuple[str, str]] = []
    for name, tid in to_delete:
        if tid in seen:
            continue
        seen.add(tid)
        unique.append((name, tid))

    if not unique:
        print("Nothing to delete.")
        return 0

    print("Will delete NocoDB tables:")
    for name, tid in unique:
        print(f"  - {name} ({tid})")

    if not yes:
        print("Add --yes to confirm deletion.")
        return 1

    for name, tid in unique:
        try:
            nc.delete_table(tid)
            print(f"  deleted {name}")
        except Exception as e:
            print(f"  failed {name}: {e}")

    if table_names:
        remaining = {k: v for k, v in tracked.items() if k not in table_names}
    else:
        remaining = {}
    state["tables"] = remaining
    save_state(state)
    print("Reset complete.")
    return 0


def migrate_one_table(
    nc: NocoDbApi,
    at: AirtableBase,
    base_id: str,
    table_name: str,
    max_records: int,
    dry_run: bool,
    recreate: bool,
    skip_existing: bool,
    state: dict,
) -> dict:
    airtable_table = at.table_by_name(table_name)
    fields = list(airtable_table.get("fields") or [])
    field_types = {str(f["name"]): str(f.get("type") or "singleLineText") for f in fields}

    existing = nc.find_table_by_title(base_id, table_name)
    prior = (state.get("tables") or {}).get(table_name) or {}
    if existing and skip_existing and not recreate:
        print(f"  skip '{table_name}' (already in NocoDB)")
        return {
            "nocodb_table_id": str(existing["id"]),
            "records_synced": prior.get("records_synced", 0),
            "last_sync": prior.get("last_sync"),
            "field_count": prior.get("field_count"),
        }

    if existing and recreate:
        nc.delete_table(str(existing["id"]))
        existing = None
        print(f"  removed old NocoDB table '{table_name}'")

    if existing:
        table_id = str(existing["id"])
        print(f"  reusing existing table '{table_name}' id={table_id}")
    else:
        if dry_run:
            print(f"  would create table '{table_name}' with {len(fields) + 1} columns")
            table_id = ""
        else:
            table_id = create_nocodb_table(nc, base_id, airtable_table)

    records = at.fetch_records(table_name, max_records=max_records)
    if table_id:
        allowed_columns = writable_column_titles(nc, table_id)
    else:
        allowed_columns = {"airtable_record_id"} | {
            str(f["name"]) for f in fields if str(f.get("type") or "") not in SKIP_AIRTABLE_TYPES
        }
    rows = [record_to_row(r, field_types, allowed_columns) for r in records]
    print(f"  records fetched: {len(rows)}")

    if dry_run:
        for sample in rows[:2]:
            print(json.dumps(sample, ensure_ascii=False, indent=2)[:1500])
        return {"nocodb_table_id": table_id, "records_synced": 0}

    if not table_id:
        raise RuntimeError("Missing table_id")

    inserted = 0
    chunk_size = 20 if len(allowed_columns) > 80 else BULK_CHUNK
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        try:
            nc.bulk_insert(table_id, chunk)
        except RuntimeError as exc:
            print(f"    batch failed ({exc}); retrying row-by-row...")
            for row in chunk:
                try:
                    nc.bulk_insert(table_id, [row])
                except RuntimeError as row_exc:
                    msg = str(row_exc)
                    if "is virtual and cannot be updated" in msg:
                        bad = msg.split('"')[1]
                        row = {k: v for k, v in row.items() if k != bad}
                        nc.bulk_insert(table_id, [row])
                    else:
                        raise
        inserted += len(chunk)
        if inserted % 500 == 0 or inserted == len(rows):
            print(f"    inserted {inserted}/{len(rows)}")
        time.sleep(0.15)

    return {
        "nocodb_table_id": table_id,
        "records_synced": inserted,
        "last_sync": utc_now(),
        "field_count": len(fields) + 1,
    }


def cmd_migrate(
    nc: NocoDbApi,
    at: AirtableBase,
    base_id: str,
    table_names: List[str],
    max_records: int,
    dry_run: bool,
    recreate: bool,
    skip_existing: bool,
    cfg: dict,
) -> int:
    state = load_state()
    state.setdefault("tables", {})
    state["airtable_base_id"] = at.base_id
    state["nocodb_base_id"] = base_id

    missing = []
    schema_names = {t["name"] for t in at.fetch_schema()}
    for name in table_names:
        if name not in schema_names:
            missing.append(name)
    if missing:
        print("Warning: tables not in Airtable base:", ", ".join(missing))

    table_names = [n for n in table_names if n in schema_names]
    if not table_names:
        print("No tables to migrate.")
        return 1

    print(f"Migrating {len(table_names)} table(s) to NocoDB base {base_id}")
    for table_name in table_names:
        print(f"\n== {table_name} ==")
        info = migrate_one_table(
            nc, at, base_id, table_name, max_records, dry_run, recreate, skip_existing, state
        )
        if not dry_run:
            state["tables"][table_name] = info

    if not dry_run:
        save_state(state)
        nocodb_cfg = cfg.setdefault("nocodb", {})
        nocodb_cfg["base_id"] = base_id
        list_info = state["tables"].get("List") or {}
        if list_info.get("nocodb_table_id"):
            nocodb_cfg["list_table_id"] = list_info["nocodb_table_id"]
            nocodb_cfg["bookings_table_id"] = list_info["nocodb_table_id"]
            nocodb_cfg["bookings_table"] = "List"
        save_config(cfg)
        print("\nUpdated config.json and nocodb_migration_state.json")

    print("\nDone.")
    return 0


def resolve_table_names(args: argparse.Namespace, cfg: dict, at: AirtableBase) -> List[str]:
    if getattr(args, "link_deps", False):
        return list(LIST_LINK_TARGETS)
    if args.all_tables:
        return [t["name"] for t in at.fetch_schema()]
    if args.config_tables:
        return config_table_names(cfg)
    if args.tables:
        return args.tables
    return ["List"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Airtable -> NocoDB schema migration")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("discover", help="List NocoDB bases/tables")
    p_schema = sub.add_parser("airtable-schema", help="List Airtable tables/fields")
    p_schema.add_argument("--tables", nargs="*", default=[])

    p_reset = sub.add_parser("reset", help="Delete migrated NocoDB tables")
    p_reset.add_argument("--tables", nargs="*", default=[], help="Only these table names")
    p_reset.add_argument("--yes", action="store_true")

    p_migrate = sub.add_parser("migrate", help="Create tables + sync records")
    p_migrate.add_argument("--tables", nargs="*", default=[], help="Airtable table names, e.g. List")
    p_migrate.add_argument("--config-tables", action="store_true", help="Use names from config.json airtable.tables")
    p_migrate.add_argument("--all-tables", action="store_true", help="Migrate every table in the Airtable base")
    p_migrate.add_argument("--max-records", type=int, default=0, help="Per table (0=all)")
    p_migrate.add_argument("--dry-run", action="store_true")
    p_migrate.add_argument("--recreate", action="store_true", help="Delete existing same-named NocoDB table first")
    p_migrate.add_argument("--skip-existing", action="store_true", help="Skip tables already present in NocoDB")
    p_migrate.add_argument("--link-deps", action="store_true", help="Migrate List link target tables")

    p_links = sub.add_parser("link-relations", help="Convert link fields to NocoDB relations")
    p_links.add_argument("--tables", nargs="*", default=["List"])
    p_links.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    cfg = load_config()
    nc_cfg = cfg.get("nocodb") or {}
    at_cfg = cfg.get("airtable") or {}
    api_url = str(nc_cfg.get("api_url") or "").strip()
    token = str(nc_cfg.get("api_token") or "").strip()
    nc_base_id = str(nc_cfg.get("base_id") or "").strip()
    at_base_id = str(at_cfg.get("base_id") or "").strip()
    at_key = str(at_cfg.get("api_key") or "").strip()

    if not api_url or not token:
        print("Set nocodb.api_url and nocodb.api_token in config.json", file=sys.stderr)
        return 2
    if not at_base_id or not at_key:
        print("Set airtable.base_id and airtable.api_key in config.json", file=sys.stderr)
        return 2

    nc = NocoDbApi(api_url, token)
    at = AirtableBase(at_key, at_base_id)
    state = load_state()

    if args.cmd == "discover":
        return cmd_discover(nc)

    if args.cmd == "airtable-schema":
        only = args.tables or None
        return cmd_airtable_schema(at, only)

    if not nc_base_id:
        print("Set nocodb.base_id in config.json (run discover first)", file=sys.stderr)
        return 2

    if args.cmd == "reset":
        names = args.tables or None
        return cmd_reset(nc, nc_base_id, state, names, args.yes)

    if args.cmd == "migrate":
        names = resolve_table_names(args, cfg, at)
        return cmd_migrate(
            nc, at, nc_base_id, names,
            args.max_records, args.dry_run, args.recreate, args.skip_existing, cfg,
        )

    if args.cmd == "link-relations":
        names = args.tables or ["List"]
        return cmd_link_relations(nc, at, nc_base_id, names, state, args.dry_run)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
