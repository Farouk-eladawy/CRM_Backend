"""
Migrate Airtable -> Baserow (simpler than NocoDB path).

Setup:
  1. Baserow on Railway (or Cloud)
  2. Create workspace + database
  3. For migration (creates tables/fields): set admin_email + admin_password in config.json
     OR jwt_token from POST /api/user/token-auth/
  4. Optional api_token for row-only scripts after migration

Usage:
  python tools/migrate_airtable_to_baserow.py discover
  python tools/migrate_airtable_to_baserow.py migrate --link-deps
  python tools/migrate_airtable_to_baserow.py migrate --tables List
  python tools/migrate_airtable_to_baserow.py migrate --all-tables --skip-existing
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from airtable_fields import TABLE_NAME  # noqa: E402

STATE_PATH = ROOT / "baserow_migration_state.json"
BATCH_SIZE = 200

LIST_LINK_TARGETS = [
    "Add Driver Name & Phone copy",
    "Add Guide Name & Phone",
    "Add Representative Name & Phone",
    "Add Supplier Name & Phone",
    "Conversations",
    "Grand_Tickets",
    "Products_Catalog",
]

AIRTABLE_TO_BASEROW = {
    "singleLineText": "text",
    "email": "email",
    "url": "url",
    "multilineText": "long_text",
    "richText": "long_text",
    "number": "number",
    "currency": "number",
    "percent": "number",
    "rating": "rating",
    "date": "date",
    "dateTime": "date",
    "checkbox": "boolean",
    "phoneNumber": "phone_number",
    "singleSelect": "single_select",
    "multipleSelects": "multiple_select",
    "multipleAttachments": "long_text",
    "multipleRecordLinks": "link_row",
    "formula": "long_text",
    "rollup": "long_text",
    "lookup": "long_text",
    "count": "number",
    "autonumber": "number",
    "createdTime": "date",
    "lastModifiedTime": "date",
    "createdBy": "text",
    "lastModifiedBy": "text",
}

SKIP_AIRTABLE_TYPES = {"button"}

# Store Airtable selects as text — schema choices often miss values used in rows.
SELECT_AS_TEXT = {"singleSelect", "multipleSelects"}

# Store as text to avoid strict Baserow validation during bulk import.
STORE_AS_TEXT = {
    "createdTime", "lastModifiedTime", "createdBy", "lastModifiedBy",
    "phoneNumber", "email", "url",
}


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
    return {"tables": {}}


def save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def flatten_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, list):
        if not value:
            return None
        if all(isinstance(x, str) for x in value):
            return ", ".join(value)
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return value


def format_for_baserow(value: Any, at_type: str) -> Any:
    if value is None:
        return None
    if at_type in STORE_AS_TEXT:
        if at_type in ("createdBy", "lastModifiedBy") and isinstance(value, dict):
            return value.get("email") or value.get("name") or json.dumps(value, ensure_ascii=False)
        return flatten_value(value)
    if at_type in ("date", "dateTime", "createdTime", "lastModifiedTime"):
        s = str(value).strip()
        if not s:
            return None
        if "T" in s:
            return s.split("T")[0]
        return s[:10] if len(s) >= 10 else s
    return flatten_value(value)


class BaserowApi:
    def __init__(self, api_url: str, token: str, auth_scheme: str = "Token"):
        self.base_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"{auth_scheme} {token}",
            "Content-Type": "application/json",
        })

    @classmethod
    def from_config(cls, br_cfg: dict) -> "BaserowApi":
        api_url = str(br_cfg.get("api_url") or "https://api.baserow.io").strip()
        jwt = str(br_cfg.get("jwt_token") or "").strip()
        if jwt:
            return cls(api_url, jwt, auth_scheme="JWT")
        email = str(br_cfg.get("admin_email") or "").strip()
        password = str(br_cfg.get("admin_password") or "").strip()
        if email and password:
            jwt = obtain_jwt(api_url, email, password)
            return cls(api_url, jwt, auth_scheme="JWT")
        token = str(br_cfg.get("api_token") or "").strip()
        if not token:
            raise RuntimeError(
                "Set baserow.jwt_token OR admin_email+admin_password OR api_token in config.json"
            )
        return cls(api_url, token, auth_scheme="Token")

    def _req(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        resp = self.session.request(method, url, timeout=180, **kwargs)
        if not resp.ok:
            raise RuntimeError(f"Baserow {method} {path} -> HTTP {resp.status_code}: {resp.text[:800]}")
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def list_applications(self) -> List[dict]:
        data = self._req("GET", "/api/applications/")
        return list(data) if isinstance(data, list) else list(data.get("results") or data)

    def list_tables(self, database_id: int) -> List[dict]:
        data = self._req("GET", f"/api/database/tables/database/{database_id}/")
        return list(data) if isinstance(data, list) else list(data.get("results") or data)

    def list_fields(self, table_id: int) -> List[dict]:
        data = self._req("GET", f"/api/database/fields/table/{table_id}/")
        return list(data) if isinstance(data, list) else list(data.get("results") or data)

    def create_table(self, database_id: int, name: str) -> dict:
        return self._req("POST", f"/api/database/tables/database/{database_id}/", json={"name": name})

    def create_field(self, table_id: int, body: dict) -> dict:
        return self._req("POST", f"/api/database/fields/table/{table_id}/", json=body)

    def delete_table(self, table_id: int) -> None:
        self._req("DELETE", f"/api/database/tables/{table_id}/")

    def batch_create_rows(self, table_id: int, rows: List[dict]) -> Any:
        return self._req(
            "POST",
            f"/api/database/rows/table/{table_id}/batch/?user_field_names=true",
            json={"items": rows},
        )

    def list_all_rows(self, table_id: int) -> List[dict]:
        rows: List[dict] = []
        page = 1
        while True:
            data = self._req(
                "GET",
                f"/api/database/rows/table/{table_id}/",
                params={"user_field_names": "true", "size": 200, "page": page},
            )
            batch = list(data.get("results") or [])
            rows.extend(batch)
            if not data.get("next"):
                break
            page += 1
        return rows

    def find_table_by_name(self, database_id: int, name: str) -> Optional[dict]:
        for t in self.list_tables(database_id):
            if str(t.get("name") or "") == name:
                return t
        return None

    def list_token_tables(self) -> List[dict]:
        data = self._req("GET", "/api/database/tables/all-tables/")
        return list(data) if isinstance(data, list) else list(data.get("results") or data)


def obtain_jwt(api_url: str, email: str, password: str) -> str:
    url = f"{api_url.rstrip('/')}/api/user/token-auth/"
    resp = requests.post(url, json={"email": email, "password": password}, timeout=60)
    if not resp.ok:
        raise RuntimeError(f"Baserow login failed HTTP {resp.status_code}: {resp.text[:400]}")
    token = (resp.json() or {}).get("token")
    if not token:
        raise RuntimeError("Baserow login: no JWT token in response")
    return str(token)


def resolve_database_id(br: BaserowApi, br_cfg: dict) -> int:
    configured = int(br_cfg.get("database_id") or 0)
    if configured:
        return configured
    for app in br.list_applications():
        if str(app.get("type") or "") == "database" and app.get("id"):
            return int(app["id"])
    try:
        tables = br.list_token_tables()
        if tables and tables[0].get("database_id"):
            return int(tables[0]["database_id"])
    except RuntimeError:
        pass
    raise RuntimeError(
        "Could not detect database_id. Open your database in Baserow; URL contains /database/ID/ — set baserow.database_id in config.json"
    )


class AirtableSource:
    def __init__(self, cfg: dict):
        at = cfg.get("airtable") or {}
        self.api_key = str(at.get("api_key") or "").strip()
        self.base_id = str(at.get("base_id") or "").strip()
        if not self.api_key or not self.base_id:
            raise RuntimeError("Missing airtable.api_key or base_id")
        from pyairtable import Api
        self.api = Api(self.api_key)
        self._schema: Optional[List[dict]] = None

    def fetch_schema(self) -> List[dict]:
        if self._schema is None:
            import requests as req
            r = req.get(
                f"https://api.airtable.com/v0/meta/bases/{self.base_id}/tables",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=180,
            )
            r.raise_for_status()
            self._schema = list(r.json().get("tables") or [])
        return self._schema

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


def unique_field_name(title: str, used: set[str]) -> str:
    base = str(title or "Field").strip() or "Field"
    if base not in used:
        used.add(base)
        return base
    i = 2
    while f"{base} ({i})" in used:
        i += 1
    unique = f"{base} ({i})"
    used.add(unique)
    return unique


def field_body_from_airtable(
    field: dict, link_table_ids: Dict[str, int], used_names: set[str]
) -> Optional[dict]:
    at_type = str(field.get("type") or "singleLineText")
    if at_type in SKIP_AIRTABLE_TYPES:
        return None
    name = unique_field_name(str(field.get("name") or "Field"), used_names)
    if at_type == "multipleRecordLinks":
        linked_id = str((field.get("options") or {}).get("linkedTableId") or "")
        if linked_id not in link_table_ids:
            return None
        return {
            "name": name,
            "type": "link_row",
            "link_row_table_id": link_table_ids[linked_id],
        }
    if at_type in SELECT_AS_TEXT or at_type in STORE_AS_TEXT:
        return {"name": name, "type": "text"}
    br_type = AIRTABLE_TO_BASEROW.get(at_type, "text")
    body: dict = {"name": name, "type": br_type}
    if br_type == "single_select":
        choices = (field.get("options") or {}).get("choices") or []
        body["select_options"] = [{"value": c.get("name"), "color": "blue"} for c in choices if c.get("name")]
    return body


def migrate_table(
    br: BaserowApi,
    at: AirtableSource,
    database_id: int,
    table_name: str,
    max_records: int,
    skip_existing: bool,
    recreate: bool,
    state: dict,
    link_table_ids: Dict[str, int],
) -> dict:
    at_table = at.table_by_name(table_name)
    at_id = str(at_table["id"])
    fields = list(at_table.get("fields") or [])

    existing = br.find_table_by_name(database_id, table_name)
    if existing and recreate:
        tid_old = int(existing["id"])
        print(f"  deleting existing table '{table_name}' id={tid_old}")
        br.delete_table(tid_old)
        existing = None
    if existing and skip_existing and not recreate:
        prev = state.get("tables", {}).get(table_name) or {}
        if int(prev.get("records_synced") or 0) > 0:
            print(f"  skip '{table_name}' (exists id={existing['id']}, {prev.get('records_synced')} rows)")
            tid = int(existing["id"])
            link_table_ids[at_id] = tid
            return prev
        print(f"  resume '{table_name}' (exists id={existing['id']}, no rows synced yet)")

    if not existing:
        created = br.create_table(database_id, table_name)
        tid = int(created["id"])
        print(f"  created table '{table_name}' id={tid}")
        # Primary "Name" field exists by default; add airtable_record_id
        br.create_field(tid, {"name": "airtable_record_id", "type": "text"})
        time.sleep(0.1)
    else:
        tid = int(existing["id"])

    link_table_ids[at_id] = tid
    existing_names = {f.get("name") for f in br.list_fields(tid)}
    used_names: set[str] = set(existing_names)
    field_name_map: Dict[str, str] = {}
    added = 0
    for field in fields:
        at_name = str(field.get("name") or "Field")
        body = field_body_from_airtable(field, link_table_ids, used_names)
        if not body:
            continue
        br_name = body["name"]
        field_name_map[at_name] = br_name
        if br_name in existing_names:
            continue
        try:
            br.create_field(tid, body)
            added += 1
            existing_names.add(br_name)
            time.sleep(0.05)
        except RuntimeError as exc:
            print(f"    field skip {br_name}: {exc}")
    if added:
        print(f"  added {added} fields")

    records = at.fetch_records(table_name, max_records=max_records)
    field_names = {str(f["name"]) for f in fields}
    rows: List[dict] = []
    for rec in records:
        row: dict = {"airtable_record_id": rec.get("id")}
        for k, v in (rec.get("fields") or {}).items():
            if k not in field_names:
                continue
            at_type = next((f.get("type") for f in fields if f.get("name") == k), "singleLineText")
            if at_type == "multipleRecordLinks":
                continue  # links in phase 2
            out_key = field_name_map.get(k, k)
            row[out_key] = format_for_baserow(v, at_type)
        rows.append(row)

    inserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        chunk = rows[i : i + BATCH_SIZE]
        br.batch_create_rows(tid, chunk)
        inserted += len(chunk)
        print(f"    inserted {inserted}/{len(rows)}")
        time.sleep(0.2)

    return {"baserow_table_id": tid, "records_synced": inserted}


def cmd_discover(br: BaserowApi, database_id: int, cfg: dict) -> int:
    print("Applications:")
    for app in br.list_applications():
        print(f"  {app.get('name')} id={app.get('id')} type={app.get('type')}")
    print(f"\nTables in database {database_id}:")
    for t in br.list_tables(database_id):
        print(f"  {t.get('name')} id={t.get('id')}")
    br_cfg = cfg.setdefault("baserow", {})
    br_cfg["database_id"] = database_id
    save_config(cfg)
    print(f"\nSaved database_id={database_id} to config.json")
    return 0


def cmd_migrate(
    br: BaserowApi,
    at: AirtableSource,
    database_id: int,
    table_names: List[str],
    max_records: int,
    skip_existing: bool,
    recreate: bool,
    cfg: dict,
) -> int:
    state = load_state()
    state.setdefault("tables", {})
    link_table_ids: Dict[str, int] = {
        str(info.get("airtable_table_id") or ""): int(info["baserow_table_id"])
        for info in state.get("tables", {}).values()
        if info.get("baserow_table_id") and info.get("airtable_table_id")
    }

    schema_names = {t["name"] for t in at.fetch_schema()}
    table_names = [n for n in table_names if n in schema_names]
    id_by_name = {t["name"]: str(t["id"]) for t in at.fetch_schema()}

    # Phase 1: tables without link fields first, then tables with links
    def link_count(name: str) -> int:
        tbl = at.table_by_name(name)
        return sum(1 for f in tbl.get("fields") or [] if f.get("type") == "multipleRecordLinks")

    table_names.sort(key=link_count)

    print(f"Migrating {len(table_names)} table(s) to Baserow database {database_id}")
    for name in table_names:
        print(f"\n== {name} ==")
        info = migrate_table(
            br, at, database_id, name, max_records, skip_existing, recreate, state, link_table_ids
        )
        info["airtable_table_id"] = id_by_name.get(name)
        state["tables"][name] = info

    save_state(state)
    br_cfg = cfg.setdefault("baserow", {})
    br_cfg["database_id"] = database_id
    list_info = state["tables"].get("List") or {}
    if list_info.get("baserow_table_id"):
        br_cfg["list_table_id"] = list_info["baserow_table_id"]
    save_config(cfg)
    print("\nDone. See baserow_migration_state.json")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Airtable -> Baserow migration")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("discover")
    p = sub.add_parser("migrate")
    p.add_argument("--tables", nargs="*", default=[])
    p.add_argument("--link-deps", action="store_true")
    p.add_argument("--all-tables", action="store_true")
    p.add_argument("--max-records", type=int, default=0)
    p.add_argument("--skip-existing", action="store_true")
    p.add_argument("--recreate", action="store_true")

    args = parser.parse_args()
    cfg = load_config()
    br_cfg = cfg.get("baserow") or {}
    try:
        br = BaserowApi.from_config(br_cfg)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    at = AirtableSource(cfg)

    database_id = 0
    db_err = ""
    try:
        database_id = resolve_database_id(br, br_cfg)
    except RuntimeError as exc:
        db_err = str(exc)
        if args.cmd != "discover":
            print(db_err, file=sys.stderr)
            return 2

    if args.cmd == "discover":
        if not database_id:
            print(db_err or "Could not detect database_id", file=sys.stderr)
            return 2
        return cmd_discover(br, database_id, cfg)

    if args.cmd == "migrate":
        if not database_id:
            print("Set baserow.database_id in config.json", file=sys.stderr)
            return 2
        if args.link_deps:
            names = list(LIST_LINK_TARGETS)
        elif args.all_tables:
            names = [t["name"] for t in at.fetch_schema()]
        elif args.tables:
            names = args.tables
        else:
            names = ["List"]
        return cmd_migrate(
            br, at, database_id, names,
            args.max_records, args.skip_existing, args.recreate, cfg,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
