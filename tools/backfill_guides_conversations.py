import json
import re
import sqlite3
import sys
import time
import urllib.parse
from pathlib import Path

import requests


def normalize_digits(phone: str) -> str:
    try:
        return re.sub(r"\D", "", str(phone or ""))
    except Exception:
        return ""


def build_keys(digits: str) -> set[str]:
    d = normalize_digits(digits)
    if not d:
        return set()
    out = {d}
    if d.startswith("20") and len(d) > 10:
        out.add(d[2:])
    if len(d) >= 8:
        out.add(d[-8:])
    return out


def fetch_airtable_records(api_key: str, base_id: str, table_name: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {api_key}"}
    encoded = urllib.parse.quote(table_name, safe="")
    url = f"https://api.airtable.com/v0/{base_id}/{encoded}?pageSize=100"
    out: list[dict] = []
    while True:
        res = requests.get(url, headers=headers, timeout=30)
        res.raise_for_status()
        data = res.json() or {}
        out.extend(data.get("records") or [])
        offset = data.get("offset")
        if not offset:
            break
        url = f"https://api.airtable.com/v0/{base_id}/{encoded}?pageSize=100&offset={urllib.parse.quote(str(offset), safe='')}"
    return out


def main(argv: list[str]) -> int:
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "config.json"
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    airtable = cfg.get("airtable") or {}
    api_key = str(airtable.get("api_key") or "").strip()
    base_id = str(airtable.get("base_id") or "").strip()
    tables = airtable.get("tables") or {}
    guides_table = str(tables.get("guides") or "Add Guide Name & Phone").strip()
    drivers_table = str(tables.get("drivers") or "Add Driver Name & Phone copy").strip()

    if not api_key or not base_id:
        print("Missing Airtable config (api_key/base_id).")
        return 2

    guides = fetch_airtable_records(api_key, base_id, guides_table)
    drivers = fetch_airtable_records(api_key, base_id, drivers_table)

    guide_keys: set[str] = set()
    guide_name_by_key: dict[str, str] = {}
    for r in guides or []:
        fields = (r or {}).get("fields") or {}
        name = str(fields.get("Guide Name") or "").strip()
        phone = str(fields.get("Phone Number") or "").strip()
        digits = normalize_digits(phone)
        if not digits:
            continue
        for k in build_keys(digits):
            guide_keys.add(k)
            if name and k not in guide_name_by_key:
                guide_name_by_key[k] = name

    driver_keys: set[str] = set()
    for r in drivers or []:
        fields = (r or {}).get("fields") or {}
        phone = str(fields.get("Phone Number") or "").strip()
        digits = normalize_digits(phone)
        if not digits:
            continue
        for k in build_keys(digits):
            driver_keys.add(k)

    conn = sqlite3.connect("chat_history.db", timeout=60.0)
    conn.row_factory = sqlite3.Row
    try:
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout = 60000;")
        except Exception:
            pass

        rows = None
        for _ in range(10):
            try:
                rows = conn.execute(
                    """
                    SELECT chat_id, sender_identifier, contact_name, location, source
                    FROM conversations
                    WHERE lower(source) = 'whatsapp'
                      AND sender_identifier IS NOT NULL
                      AND trim(sender_identifier) <> ''
                    """
                ).fetchall()
                break
            except sqlite3.OperationalError as e:
                if "locked" not in str(e).lower():
                    raise
                time.sleep(1.5)

        if rows is None:
            print("Database is locked. Please retry after reducing dashboard traffic.")
            return 1

        updated = 0
        touched: list[tuple[str, str]] = []
        for r in rows:
            chat_id = str(r["chat_id"] or "").strip()
            sender = str(r["sender_identifier"] or "").strip()
            if not chat_id or not sender:
                continue
            digits = normalize_digits(sender)
            if not digits:
                continue
            keys = build_keys(digits)
            if keys & driver_keys:
                continue
            g_match = list(keys & guide_keys)
            if not g_match:
                continue
            g_name = guide_name_by_key.get(g_match[0]) if g_match else None
            new_name = f"Guide - {g_name}" if g_name else "Guide"

            ok = False
            for _ in range(10):
                try:
                    cur = conn.execute(
                        "UPDATE conversations SET location = ?, contact_name = ? WHERE chat_id = ?",
                        ("Guides", new_name, chat_id),
                    )
                    if cur.rowcount > 0:
                        updated += 1
                        touched.append((sender, new_name))
                    ok = True
                    break
                except sqlite3.OperationalError as e:
                    if "locked" not in str(e).lower():
                        raise
                    time.sleep(1.5)
            if not ok:
                print("Database is locked. Partial update applied. Please retry.")
                conn.commit()
                return 1

        conn.commit()
    finally:
        conn.close()

    print(f"Updated conversations to Guides: {updated}")
    if touched:
        sample = touched[:30]
        for phone, name in sample:
            print(f"- {phone} => {name}")
        if len(touched) > len(sample):
            print(f"... and {len(touched) - len(sample)} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
