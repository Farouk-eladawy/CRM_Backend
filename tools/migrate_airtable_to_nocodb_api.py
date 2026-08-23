"""
Migrate Airtable → NocoDB via API (no CSV, no public share link).

Prerequisites:
  1. NocoDB admin account on Railway
  2. API token: NocoDB → Account (avatar) → Account Settings → Tokens
  3. config.json → nocodb.api_token, nocodb.base_id (optional table_id)

Usage (from OpenClaw_Version folder):
  python tools/migrate_airtable_to_nocodb_api.py discover
  python tools/migrate_airtable_to_nocodb_api.py setup --base-id <BASE_ID>
  python tools/migrate_airtable_to_nocodb_api.py sync --max 100 --dry-run
  python tools/migrate_airtable_to_nocodb_api.py sync --date-from 2026-08-23 --date-to 2026-08-23
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from airtable_fields import FieldIds, ID_TO_READABLE_NAME, TABLE_NAME  # noqa: E402

STATE_PATH = ROOT / "nocodb_migration_state.json"
BULK_CHUNK = 50

# Core List columns for FTS (readable Airtable names → NocoDB column titles)
CORE_COLUMNS: List[Tuple[str, str]] = [
    ("airtable_record_id", "SingleLineText"),
    (ID_TO_READABLE_NAME[FieldIds.BOOKING_NR], "SingleLineText"),
    (ID_TO_READABLE_NAME[FieldIds.DATE_TRIP], "Date"),
    (ID_TO_READABLE_NAME[FieldIds.AGENCY], "SingleLineText"),
    (ID_TO_READABLE_NAME[FieldIds.TRIP_NAME], "SingleLineText"),
    (ID_TO_READABLE_NAME[FieldIds.CUSTOMER_NAME], "SingleLineText"),
    (ID_TO_READABLE_NAME[FieldIds.CUSTOMER_PHONE], "PhoneNumber"),
    (ID_TO_READABLE_NAME[FieldIds.CUSTOMER_EMAIL], "Email"),
    (ID_TO_READABLE_NAME[FieldIds.CUSTOMER_PERSONAL_EMAIL], "Email"),
    (ID_TO_READABLE_NAME[FieldIds.HOTEL_NAME], "SingleLineText"),
    (ID_TO_READABLE_NAME[FieldIds.ROOM_NUMBER], "SingleLineText"),
    (ID_TO_READABLE_NAME[FieldIds.PICKUP_TIME], "SingleLineText"),
    (ID_TO_READABLE_NAME[FieldIds.BOOKING_STATUS], "SingleLineText"),
    (ID_TO_READABLE_NAME[FieldIds.CAR_TYPE], "SingleLineText"),
    (ID_TO_READABLE_NAME[FieldIds.LOCAL_CAR_TYPE], "SingleLineText"),
    (ID_TO_READABLE_NAME[FieldIds.DRIVER_NAME_PHONE], "SingleLineText"),
    (ID_TO_READABLE_NAME[FieldIds.DES], "SingleLineText"),
    (ID_TO_READABLE_NAME[FieldIds.OPTION], "LongText"),
    (ID_TO_READABLE_NAME[FieldIds.ADT], "Number"),
    (ID_TO_READABLE_NAME[FieldIds.CHD], "Number"),
    (ID_TO_READABLE_NAME[FieldIds.INF], "Number"),
    (ID_TO_READABLE_NAME[FieldIds.TOTAL_TRAVELERS], "Number"),
    (ID_TO_READABLE_NAME[FieldIds.AMOUNT], "Number"),
    (ID_TO_READABLE_NAME[FieldIds.CURRENCY], "SingleLineText"),
    (ID_TO_READABLE_NAME[FieldIds.REMARKS], "LongText"),
    (ID_TO_READABLE_NAME[FieldIds.CUSTOMER_COUNTRY], "SingleLineText"),
]


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
    return {"synced": {}}


def save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def flatten_airtable_value(value: Any) -> Any:
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


def parse_date_only(raw: Any) -> Optional[str]:
    if not raw:
        return None
    s = str(raw).strip()
    if "T" in s:
        return s.split("T")[0]
    return s[:10] if len(s) >= 10 else s


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
        resp = self.session.request(method, url, timeout=120, **kwargs)
        if not resp.ok:
            raise RuntimeError(f"NocoDB {method} {path} -> HTTP {resp.status_code}: {resp.text[:500]}")
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def list_bases(self) -> List[dict]:
        data = self._req("GET", "/api/v2/meta/bases")
        if isinstance(data, list):
            return data
        return list(data.get("list") or data.get("bases") or [])

    def list_tables(self, base_id: str) -> List[dict]:
        data = self._req("GET", f"/api/v2/meta/bases/{base_id}/tables")
        if isinstance(data, list):
            return data
        return list(data.get("list") or [])

    def create_table(self, base_id: str, title: str, columns: List[Tuple[str, str]]) -> dict:
        cols = []
        for idx, (name, uidt) in enumerate(columns):
            cols.append({
                "column_name": name,
                "title": name,
                "uidt": uidt,
                "pk": idx == 0 and name == "airtable_record_id",
            })
        body = {
            "title": title,
            "table_name": re.sub(r"[^a-zA-Z0-9_]+", "_", title).strip("_").lower() or "bookings",
            "columns": cols,
        }
        return self._req("POST", f"/api/v2/meta/bases/{base_id}/tables", json=body)

    def bulk_insert(self, table_id: str, rows: List[dict]) -> Any:
        return self._req("POST", f"/api/v2/tables/{table_id}/records", json=rows)

    def list_columns(self, table_id: str) -> List[str]:
        data = self._req("GET", f"/api/v2/meta/tables/{table_id}")
        cols = data.get("columns") or []
        return [str(c.get("title") or c.get("column_name") or "") for c in cols]


class AirtableSource:
    def __init__(self, cfg: dict):
        at = cfg.get("airtable") or {}
        self.api_key = str(at.get("api_key") or "").strip()
        self.base_id = str(at.get("base_id") or "").strip()
        if not self.api_key or not self.base_id:
            raise RuntimeError("Missing airtable.api_key or base_id in config.json")
        from pyairtable import Api
        self.table = Api(self.api_key).table(self.base_id, TABLE_NAME)

    def fetch(self, max_records: int = 0, formula: Optional[str] = None) -> List[dict]:
        kwargs: dict = {}
        if max_records and max_records > 0:
            kwargs["max_records"] = max_records
        if formula:
            kwargs["formula"] = formula
        return list(self.table.all(**kwargs))


def build_date_formula(date_from: Optional[str], date_to: Optional[str]) -> Optional[str]:
    if date_from and date_to and date_from == date_to:
        return f"IS_SAME({{Date Trip}}, '{date_from}', 'day')"
    parts = []
    if date_from:
        parts.append(f"IS_AFTER({{Date Trip}}, '{date_from}')")
    if date_to:
        parts.append(f"IS_BEFORE({{Date Trip}}, '{date_to}')")
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else f"AND({','.join(parts)})"


def record_to_nocodb_row(fields: dict, allowed_columns: List[str]) -> dict:
    allowed = set(allowed_columns)
    row: dict = {}
    for fid, val in (fields or {}).items():
        label = ID_TO_READABLE_NAME.get(fid, fid)
        if label not in allowed:
            continue
        v = flatten_airtable_value(val)
        if label == ID_TO_READABLE_NAME.get(FieldIds.DATE_TRIP):
            v = parse_date_only(v)
        row[label] = v
    return row


def cmd_discover(nc: NocoDbApi) -> int:
    bases = nc.list_bases()
    print(f"Found {len(bases)} base(s):\n")
    for b in bases:
        bid = b.get("id") or b.get("base_id")
        title = b.get("title") or b.get("name")
        print(f"  Base: {title}")
        print(f"    id: {bid}")
        try:
            tables = nc.list_tables(bid)
            for t in tables:
                tid = t.get("id")
                ttitle = t.get("title") or t.get("table_name")
                print(f"    Table: {ttitle}  id={tid}")
        except Exception as e:
            print(f"    (tables error: {e})")
        print()
    print("Copy base_id and table id into config.json -> nocodb")
    return 0


def cmd_setup(nc: NocoDbApi, base_id: str, table_title: str, cfg: dict) -> int:
    created = nc.create_table(base_id, table_title, CORE_COLUMNS)
    table_id = created.get("id")
    print(f"Created table '{table_title}' id={table_id}")
    cfg.setdefault("nocodb", {})
    cfg["nocodb"]["base_id"] = base_id
    cfg["nocodb"]["bookings_table_id"] = table_id
    cfg["nocodb"]["bookings_table"] = table_title
    save_config(cfg)
    print("Updated config.json with base_id and bookings_table_id")
    return 0


def cmd_sync(
    nc: NocoDbApi,
    at: AirtableSource,
    table_id: str,
    max_records: int,
    date_from: Optional[str],
    date_to: Optional[str],
    dry_run: bool,
    force: bool,
) -> int:
    formula = build_date_formula(date_from, date_to)
    records = at.fetch(max_records=max_records or 0, formula=formula)
    columns = nc.list_columns(table_id)
    if "airtable_record_id" not in columns:
        raise RuntimeError("Table missing 'airtable_record_id' column — run setup first")

    state = load_state()
    synced = state.get("synced") or {}
    pending_rows: List[dict] = []
    skipped = 0

    for rec in records:
        rid = str(rec.get("id") or "")
        if not rid:
            continue
        if not force and rid in synced:
            skipped += 1
            continue
        fields = rec.get("fields") or {}
        row = record_to_nocodb_row(fields, columns)
        row["airtable_record_id"] = rid
        pending_rows.append(row)

    print(f"Airtable fetched: {len(records)} | to insert: {len(pending_rows)} | skip(already): {skipped}")
    if dry_run:
        for sample in pending_rows[:3]:
            print(json.dumps(sample, ensure_ascii=False, indent=2)[:1200])
        return 0

    inserted = 0
    for i in range(0, len(pending_rows), BULK_CHUNK):
        chunk = pending_rows[i : i + BULK_CHUNK]
        nc.bulk_insert(table_id, chunk)
        for row in chunk:
            synced[row["airtable_record_id"]] = {
                "synced_at": datetime.utcnow().isoformat() + "Z",
            }
        inserted += len(chunk)
        print(f"  inserted {inserted}/{len(pending_rows)}")
        time.sleep(0.3)

    state["synced"] = synced
    state["last_sync"] = datetime.utcnow().isoformat() + "Z"
    save_state(state)
    print(f"Done. Inserted {inserted} rows into NocoDB table {table_id}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Airtable → NocoDB API migration")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("discover", help="List NocoDB bases and tables")

    p_setup = sub.add_parser("setup", help="Create Bookings table in NocoDB")
    p_setup.add_argument("--base-id", required=True)
    p_setup.add_argument("--table-title", default="Bookings")

    p_sync = sub.add_parser("sync", help="Sync records from Airtable List")
    p_sync.add_argument("--max", type=int, default=0, help="Max Airtable records (0=all)")
    p_sync.add_argument("--date-from", default="")
    p_sync.add_argument("--date-to", default="")
    p_sync.add_argument("--dry-run", action="store_true")
    p_sync.add_argument("--force", action="store_true", help="Re-sync even if seen before")

    args = parser.parse_args()
    cfg = load_config()
    nc_cfg = cfg.get("nocodb") or {}
    api_url = str(nc_cfg.get("api_url") or "").strip()
    token = str(nc_cfg.get("api_token") or "").strip()
    if not api_url or not token:
        print("Set nocodb.api_url and nocodb.api_token in config.json first.", file=sys.stderr)
        print("NocoDB → Account Settings → Tokens → Create token", file=sys.stderr)
        return 2

    nc = NocoDbApi(api_url, token)

    if args.cmd == "discover":
        return cmd_discover(nc)

    if args.cmd == "setup":
        return cmd_setup(nc, args.base_id, args.table_title, cfg)

    if args.cmd == "sync":
        table_id = str(nc_cfg.get("bookings_table_id") or "").strip()
        if not table_id:
            print("Missing nocodb.bookings_table_id — run setup or set manually after discover", file=sys.stderr)
            return 2
        at = AirtableSource(cfg)
        return cmd_sync(
            nc,
            at,
            table_id,
            args.max,
            args.date_from or None,
            args.date_to or None,
            args.dry_run,
            args.force,
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
