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
  python tools/migrate_airtable_to_baserow.py migrate --list-bundle --skip-existing
  python tools/migrate_airtable_to_baserow.py migrate --tables List
  python tools/migrate_airtable_to_baserow.py migrate --all-tables --skip-existing
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests
from requests.exceptions import ChunkedEncodingError, ConnectionError as ReqConnectionError, Timeout

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from airtable_fields import TABLE_NAME  # noqa: E402

# FTS Egypt — date-only fields use Cairo calendar day (avoid UTC day-shift).
BUSINESS_TZ = ZoneInfo("Africa/Cairo")

STATE_PATH = ROOT / "baserow_migration_state.json"
BATCH_SIZE = 15
MAX_RETRIES = 10
BATCH_SLEEP_SEC = 0.55

LIST_BUNDLE_EXCLUDE_DEFAULT = ["Grand_Tickets"]

LIST_LINK_TARGETS = [
    "Add Driver Name & Phone copy",
    "Add Guide Name & Phone",
    "Add Representative Name & Phone",
    "Add Supplier Name & Phone",
    "Conversations",
    "Grand_Tickets",
    "Products_Catalog",
]


def discover_list_link_targets(at: "AirtableSource", list_table_name: str = "List") -> List[str]:
    """Return Airtable table names linked from List via multipleRecordLinks."""
    try:
        tbl = at.table_by_name(list_table_name)
    except RuntimeError:
        return list(LIST_LINK_TARGETS)
    id_to_name = {str(t["id"]): t["name"] for t in at.fetch_schema()}
    names: List[str] = []
    seen: set[str] = set()
    for field in tbl.get("fields") or []:
        if str(field.get("type") or "") != "multipleRecordLinks":
            continue
        linked_id = str((field.get("options") or {}).get("linkedTableId") or "")
        linked_name = id_to_name.get(linked_id)
        if linked_name and linked_name not in seen:
            seen.add(linked_name)
            names.append(linked_name)
    return sorted(names) if names else list(LIST_LINK_TARGETS)


def list_bundle_table_names(
    at: "AirtableSource",
    list_table_name: str = "List",
    exclude: Optional[List[str]] = None,
) -> List[str]:
    exclude_set = {
        e.strip()
        for e in (exclude if exclude is not None else LIST_BUNDLE_EXCLUDE_DEFAULT)
        if e and e.strip()
    }
    deps = [n for n in discover_list_link_targets(at, list_table_name) if n not in exclude_set]
    return deps + (["List"] if list_table_name not in deps else [])


def clear_list_bundle_state(state: dict, bundle_names: List[str]) -> int:
    tables = state.setdefault("tables", {})
    removed = 0
    for name in bundle_names:
        if name in tables:
            del tables[name]
            removed += 1
    return removed


def build_link_table_ids(
    br: BaserowApi, database_id: int, state: dict, bundle_names: Optional[set[str]] = None
) -> Dict[str, int]:
    """Map Airtable table id -> Baserow table id, only when table still exists."""
    out: Dict[str, int] = {}
    for name, info in (state.get("tables") or {}).items():
        if bundle_names and name in bundle_names:
            continue
        at_id = str(info.get("airtable_table_id") or "")
        tid = int(info.get("baserow_table_id") or 0)
        if not at_id or not tid:
            continue
        found = br.find_table_by_name(database_id, name)
        if found and int(found["id"]) == tid:
            out[at_id] = tid
    return out

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
    "multipleAttachments": "file",
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

# Airtable formula/rollup/lookup/system — Baserow has its own; skip on import.
AUTO_COMPUTED_TYPES = {
    "formula",
    "rollup",
    "lookup",
    "multipleLookupValues",
    "count",
    "autonumber",
    "createdTime",
    "lastModifiedTime",
    "createdBy",
    "lastModifiedBy",
    "button",
    "externalSyncSource",
}

# Store Airtable selects as text — schema choices often miss values used in rows.
SELECT_AS_TEXT = {"singleSelect", "multipleSelects"}

# Numbers imported as text to avoid decimal-place validation mismatches.
NUMERIC_AS_TEXT = {"number", "currency", "percent", "rating"}

# Store as text to avoid strict Baserow validation during bulk import.
STORE_AS_TEXT = {
    "createdTime",
    "lastModifiedTime",
    "createdBy",
    "lastModifiedBy",
    "phoneNumber",
    "email",
    "url",
}


def safe_print(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


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


def extract_attachment_urls(value: Any) -> List[str]:
    if not value:
        return []
    items = value if isinstance(value, list) else [value]
    urls: List[str] = []
    for item in items:
        if isinstance(item, dict):
            url = str(item.get("url") or "").strip()
            if url:
                urls.append(url)
        elif isinstance(item, str) and item.strip():
            urls.append(item.strip())
    return urls


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


def parse_airtable_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime(value.year, value.month, value.day, 12, 0, 0, tzinfo=BUSINESS_TZ)
    s = str(value).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        # YYYY-MM-DD → noon in business TZ (stable calendar day)
        d = datetime.strptime(s[:10], "%Y-%m-%d").date()
        return datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=BUSINESS_TZ)
    except ValueError:
        return None


def format_date_for_baserow(
    value: Any,
    at_type: str = "date",
    br_field_def: Optional[dict] = None,
) -> Any:
    """
    Normalize Airtable date/datetime for Baserow without timezone day-shift.

    - Baserow date_include_time=false: YYYY-MM-DD in Africa/Cairo.
    - Baserow date_include_time=true: ISO datetime with Africa/Cairo offset
      (date-only Airtable values become midnight Cairo that calendar day).
    """
    br_include_time = bool((br_field_def or {}).get("date_include_time")) if br_field_def else False

    # Pure calendar string YYYY-MM-DD
    if isinstance(value, str):
        s = value.strip()
        if len(s) >= 10 and s[4] == "-" and s[7] == "-" and "T" not in s and " " not in s[:10]:
            try:
                d = datetime.strptime(s[:10], "%Y-%m-%d").date()
                if br_include_time:
                    local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=BUSINESS_TZ)
                    return local.isoformat(timespec="seconds")
                return s[:10]
            except ValueError:
                pass

    dt = parse_airtable_datetime(value)
    if dt is None:
        return None
    local = dt.astimezone(BUSINESS_TZ)
    if not br_include_time:
        return local.strftime("%Y-%m-%d")
    return local.isoformat(timespec="seconds")


def format_for_baserow(
    value: Any,
    at_type: str,
    br: Optional["BaserowApi"] = None,
    file_cache: Optional[dict] = None,
    br_field_def: Optional[dict] = None,
) -> Any:
    if value is None:
        return None
    if at_type in AUTO_COMPUTED_TYPES:
        return None
    if at_type == "multipleAttachments":
        urls = extract_attachment_urls(value)
        if not urls:
            return None
        if br is not None:
            cache = file_cache if file_cache is not None else {}
            files: List[dict] = []
            for url in urls:
                cached = cache.get(url)
                if cached:
                    files.append({"name": cached})
                    continue
                try:
                    uploaded = br.upload_file_via_url(url)
                    name = str(uploaded.get("name") or "")
                    if name:
                        cache[url] = name
                        files.append({"name": name})
                except RuntimeError as exc:
                    print(f"    attachment skip: {exc}")
            return files or None
        # Fallback without upload: plain URLs (not JSON)
        return urls[0] if len(urls) == 1 else "\n".join(urls)
    if at_type in NUMERIC_AS_TEXT or at_type in SELECT_AS_TEXT or at_type in STORE_AS_TEXT:
        if at_type in ("createdBy", "lastModifiedBy") and isinstance(value, dict):
            return value.get("email") or value.get("name") or json.dumps(value, ensure_ascii=False)
        if isinstance(value, (int, float)):
            return str(value)
        return flatten_value(value)
    if at_type in ("date", "dateTime"):
        return format_date_for_baserow(value, at_type=at_type, br_field_def=br_field_def)
    return flatten_value(value)


class BaserowApi:
    def __init__(
        self,
        api_url: str,
        token: str,
        auth_scheme: str = "Token",
        reauth: Optional[Callable[[], str]] = None,
    ):
        self.base_url = api_url.rstrip("/")
        self._auth_scheme = auth_scheme
        self._reauth = reauth
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
        })
        self._set_token(token, auth_scheme)

    def _set_token(self, token: str, auth_scheme: Optional[str] = None) -> None:
        scheme = auth_scheme or self._auth_scheme
        self._auth_scheme = scheme
        self.session.headers["Authorization"] = f"{scheme} {token}"

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

            def reauth() -> str:
                return obtain_jwt(api_url, email, password)

            return cls(api_url, jwt, auth_scheme="JWT", reauth=reauth)
        token = str(br_cfg.get("api_token") or "").strip()
        if not token:
            raise RuntimeError(
                "Set baserow.jwt_token OR admin_email+admin_password OR api_token in config.json"
            )
        return cls(api_url, token, auth_scheme="Token")

    def _req(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        delay = 2.0
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                for auth_try in range(2):
                    resp = self.session.request(method, url, timeout=180, **kwargs)
                    if resp.status_code == 401 and self._reauth and auth_try == 0:
                        print("    refreshing expired JWT...")
                        self._set_token(self._reauth(), "JWT")
                        continue
                    break
            except (ReqConnectionError, Timeout, ChunkedEncodingError) as exc:
                if attempt >= MAX_RETRIES:
                    raise RuntimeError(f"Baserow {method} {path} -> connection error: {exc}") from exc
                print(f"    retry {method} ({attempt}/{MAX_RETRIES}) connection: {exc}")
                time.sleep(delay)
                delay = min(delay * 2, 90)
                continue
            if resp.ok:
                if resp.status_code == 204 or not resp.content:
                    return None
                return resp.json()
            msg = f"Baserow {method} {path} -> HTTP {resp.status_code}: {resp.text[:800]}"
            retryable = resp.status_code in (500, 502, 503, 409, 429) and attempt < MAX_RETRIES
            if retryable:
                print(f"    retry {method} ({attempt}/{MAX_RETRIES}) after error: {msg[:120]}")
                time.sleep(delay)
                delay = min(delay * 2, 90)
                continue
            raise RuntimeError(msg)
        raise RuntimeError(f"Baserow {method} {path} -> max retries exceeded")

    def upload_file_via_url(self, file_url: str) -> dict:
        data = self._req("POST", "/api/user-files/upload-via-url/", json={"url": file_url})
        return data if isinstance(data, dict) else {}

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

    def update_field(self, field_id: int, body: dict) -> dict:
        return self._req("PATCH", f"/api/database/fields/{field_id}/", json=body)

    def delete_table(self, table_id: int) -> None:
        self._req("DELETE", f"/api/database/tables/{table_id}/")

    def batch_create_rows(self, table_id: int, rows: List[dict]) -> Any:
        path = f"/api/database/rows/table/{table_id}/batch/?user_field_names=true"
        body = {"items": rows}
        delay = 2.0
        last_err: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return self._req("POST", path, json=body)
            except RuntimeError as exc:
                last_err = exc
                msg = str(exc)
                retryable = any(
                    x in msg
                    for x in (
                        "HTTP 500",
                        "HTTP 502",
                        "HTTP 503",
                        "HTTP 409",
                        "HTTP 429",
                        "HTTP 401",
                        "connection error",
                        "Connection aborted",
                        "Remote end closed",
                    )
                )
                if not retryable or attempt >= MAX_RETRIES:
                    raise
                print(f"    retry batch ({attempt}/{MAX_RETRIES}) after error: {msg[:120]}")
                time.sleep(delay)
                delay = min(delay * 2, 60)
        raise last_err  # type: ignore[misc]

    def existing_airtable_ids(self, table_id: int) -> set[str]:
        ids: set[str] = set()
        page = 1
        while True:
            data = self._req(
                "GET",
                f"/api/database/rows/table/{table_id}/",
                params={
                    "user_field_names": "true",
                    "size": 200,
                    "page": page,
                },
            )
            for row in data.get("results") or []:
                rid = row.get("airtable_record_id")
                if rid:
                    ids.add(str(rid))
            if not data.get("next"):
                break
            page += 1
        return ids

    def get_view(self, view_id: int) -> dict:
        data = self._req("GET", f"/api/database/views/{int(view_id)}/")
        return data if isinstance(data, dict) else {}

    def list_rows_for_view(
        self,
        table_id: int,
        view_id: int,
        *,
        size: int = 200,
        max_pages: int = 50,
    ) -> List[dict]:
        """Fetch all rows visible in a Baserow view (paginated)."""
        rows: List[dict] = []
        page = 1
        while page <= max_pages:
            data = self._req(
                "GET",
                f"/api/database/rows/table/{int(table_id)}/",
                params={
                    "user_field_names": "true",
                    "size": int(size),
                    "page": page,
                    "view_id": int(view_id),
                },
            )
            batch = list(data.get("results") or []) if isinstance(data, dict) else []
            rows.extend(batch)
            if not (isinstance(data, dict) and data.get("next")):
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


def ensure_database_id(br: BaserowApi, br_cfg: dict) -> int:
    """Use configured database if it exists; else find/create FTS target database."""
    target_name = str(br_cfg.get("database_name") or "FTS Travels's company").strip()
    workspace_id = int(br_cfg.get("workspace_id") or 2)
    configured = int(br_cfg.get("database_id") or 0)
    apps = br.list_applications()
    by_id = {int(a["id"]): a for a in apps if a.get("id")}
    if configured and configured in by_id:
        return configured
    for app in apps:
        if str(app.get("type") or "") == "database" and str(app.get("name") or "") == target_name:
            db_id = int(app["id"])
            safe_print(f"Using existing database '{target_name}' id={db_id}")
            return db_id
    created = br._req(
        "POST",
        f"/api/applications/workspace/{workspace_id}/",
        json={"name": target_name, "type": "database"},
    )
    db_id = int(created["id"])
    safe_print(f"Created database '{target_name}' id={db_id} in workspace {workspace_id}")
    return db_id


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


def resolve_field_name(at_name: str, existing_names: set[str], used_names: set[str]) -> Optional[str]:
    """Reuse an existing Baserow column name on resume (avoids creating Foo (2))."""
    raw = str(at_name or "Field")
    base = raw.strip() or "Field"
    for candidate in (raw, base):
        if candidate in existing_names:
            used_names.add(candidate)
            return candidate
    return None


def field_body_from_airtable(
    field: dict, link_table_ids: Dict[str, int], used_names: set[str]
) -> Optional[dict]:
    at_type = str(field.get("type") or "singleLineText")
    if at_type in SKIP_AIRTABLE_TYPES or at_type in AUTO_COMPUTED_TYPES:
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
    if at_type in SELECT_AS_TEXT or at_type in STORE_AS_TEXT or at_type in NUMERIC_AS_TEXT:
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
        synced = int(prev.get("records_synced") or 0)
        # Only skip tables explicitly marked complete (full sync finished).
        # Incomplete tables (e.g. List stopped mid-run) always resume via airtable_id dedupe.
        if prev.get("complete") and synced > 0:
            print(f"  skip '{table_name}' (complete id={existing['id']}, {synced} rows)")
            tid = int(existing["id"])
            link_table_ids[at_id] = tid
            return prev
        if synced > 0:
            print(f"  resume '{table_name}' (exists id={existing['id']}, {synced} rows in state)")
        else:
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
    br_field_types = {
        str(f.get("name") or ""): str(f.get("type") or "") for f in br.list_fields(tid)
    }
    used_names: set[str] = set(existing_names)
    field_name_map: Dict[str, str] = {}
    added = 0
    skipped_computed = 0
    for field in fields:
        at_name = str(field.get("name") or "Field")
        at_type = str(field.get("type") or "")
        if at_type in AUTO_COMPUTED_TYPES:
            skipped_computed += 1
            continue
        existing_br = resolve_field_name(at_name, existing_names, used_names)
        if existing_br:
            field_name_map[at_name] = existing_br
            continue
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
            br_field_types[br_name] = str(body.get("type") or "")
            time.sleep(0.05)
        except RuntimeError as exc:
            if str(body.get("type") or "") == "file":
                body = {"name": br_name, "type": "url"}
                try:
                    br.create_field(tid, body)
                    added += 1
                    existing_names.add(br_name)
                    br_field_types[br_name] = "url"
                    print(f"    field fallback {br_name}: file -> url")
                    time.sleep(0.05)
                    continue
                except RuntimeError:
                    pass
            print(f"    field skip {br_name}: {exc}")
    if skipped_computed:
        print(f"  skipped {skipped_computed} auto-computed Airtable fields (formula/rollup/lookup/system)")
    if added:
        print(f"  added {added} fields")

    br_field_types = {str(f.get("name") or ""): str(f.get("type") or "") for f in br.list_fields(tid)}
    file_cache: dict[str, str] = {}
    records = at.fetch_records(table_name, max_records=max_records)
    rows: List[dict] = []
    for rec in records:
        row: dict = {"airtable_record_id": rec.get("id")}
        for k, v in (rec.get("fields") or {}).items():
            if k not in field_name_map:
                continue
            at_type = next((f.get("type") for f in fields if f.get("name") == k), "singleLineText")
            if at_type == "multipleRecordLinks":
                continue  # links in phase 2
            out_key = field_name_map[k]
            use_file_upload = (
                at_type == "multipleAttachments" and br_field_types.get(out_key) == "file"
            )
            # Prefer Baserow field options for date/time formatting (Cairo calendar day).
            br_field_def = None
            if br_field_types.get(out_key) == "date":
                # list_fields may not be in scope as defs; pass include_time=False for date-only AT types
                br_field_def = {
                    "type": "date",
                    "date_include_time": at_type == "dateTime",
                }
            if at_type == "date":
                br_field_def = {"type": "date", "date_include_time": False}
            val = format_for_baserow(
                v,
                at_type,
                br=br if use_file_upload else None,
                file_cache=file_cache if use_file_upload else None,
                br_field_def=br_field_def,
            )
            if val is not None and val != "":
                row[out_key] = val
        rows.append(row)

    existing_ids = br.existing_airtable_ids(tid)
    if existing_ids:
        before = len(rows)
        rows = [r for r in rows if str(r.get("airtable_record_id") or "") not in existing_ids]
        print(f"  resume: {len(existing_ids)} rows already in Baserow, {before - len(rows)} skipped, {len(rows)} to insert")

    inserted = len(existing_ids)
    total_target = inserted + len(rows)
    for i in range(0, len(rows), BATCH_SIZE):
        chunk = rows[i : i + BATCH_SIZE]
        br.batch_create_rows(tid, chunk)
        inserted += len(chunk)
        print(f"    inserted {inserted}/{total_target}")
        if state is not None and table_name:
            state.setdefault("tables", {})[table_name] = {
                "baserow_table_id": tid,
                "records_synced": inserted,
                "airtable_table_id": at_id,
                "complete": False,
            }
            save_state(state)
        time.sleep(BATCH_SLEEP_SEC)

    result = {
        "baserow_table_id": tid,
        "records_synced": inserted,
        "airtable_table_id": at_id,
        "complete": len(rows) == 0 or inserted >= total_target,
    }
    if state is not None and table_name:
        state.setdefault("tables", {})[table_name] = result
        save_state(state)
    if result["complete"]:
        print(f"  complete '{table_name}' ({inserted} rows)")
    return result


def cmd_discover(br: BaserowApi, database_id: int, cfg: dict) -> int:
    safe_print("Applications:")
    for app in br.list_applications():
        safe_print(f"  {app.get('name')} id={app.get('id')} type={app.get('type')}")
    safe_print(f"\nTables in database {database_id}:")
    for t in br.list_tables(database_id):
        safe_print(f"  {t.get('name')} id={t.get('id')}")
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
    fresh_bundle: bool = False,
) -> int:
    state = load_state()
    state.setdefault("tables", {})
    if fresh_bundle:
        link_table_ids: Dict[str, int] = {}
    else:
        bundle_set = set(table_names) if table_names else None
        link_table_ids = build_link_table_ids(br, database_id, state, bundle_set)

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
    p.add_argument(
        "--list-bundle",
        action="store_true",
        help="Migrate List link-deps (discovered from schema) then List",
    )
    p.add_argument(
        "--fresh-bundle",
        action="store_true",
        help="With --list-bundle: clear saved state for bundle tables before migrate (fresh start)",
    )
    p.add_argument(
        "--exclude-tables",
        nargs="*",
        default=None,
        metavar="TABLE",
        help="Skip tables in --list-bundle (default: Grand_Tickets). Use --exclude-tables with no names to skip nothing.",
    )
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
        if args.cmd == "migrate" and getattr(args, "list_bundle", False):
            database_id = ensure_database_id(br, br_cfg)
            br_cfg["database_id"] = database_id
            save_config(cfg)
        else:
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
        if args.list_bundle:
            exclude = args.exclude_tables
            if exclude is None:
                exclude = list(LIST_BUNDLE_EXCLUDE_DEFAULT)
            names = list_bundle_table_names(at, exclude=exclude)
            if args.fresh_bundle:
                state_pre = load_state()
                clear_names = sorted(set(names) | set(exclude))
                n = clear_list_bundle_state(state_pre, clear_names)
                save_state(state_pre)
                print(f"Cleared state for {n} table(s) (fresh start)")
            if exclude:
                print(f"Excluded: {', '.join(exclude)}")
            print(f"List bundle: {len(names) - 1} linked table(s) + List = {len(names)} total")
            for n in names:
                print(f"  - {n}")
        elif args.link_deps:
            names = discover_list_link_targets(at)
        elif args.all_tables:
            names = [t["name"] for t in at.fetch_schema()]
        elif args.tables:
            names = args.tables
        else:
            names = ["List"]
        return cmd_migrate(
            br, at, database_id, names,
            args.max_records, args.skip_existing, args.recreate, cfg,
            fresh_bundle=bool(args.list_bundle and args.fresh_bundle),
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
