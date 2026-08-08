import os
import json
import requests


READ_ONLY_TYPES = {
    "formula",
    "rollup",
    "lookup",
    "count",
    "autoNumber",
    "createdTime",
    "lastModifiedTime",
    "createdBy",
    "lastModifiedBy",
}


LINK_TYPES = {
    "multipleRecordLinks",
    "multipleLookupValues",
}


def load_config(root_dir: str):
    path = os.path.join(root_dir, "config.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_tables_meta(base_id: str, api_key: str):
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {"Authorization": f"Bearer {api_key}"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = load_config(root_dir)
    base_id = cfg["airtable"]["base_id"]
    api_key = cfg["airtable"]["api_key"]
    table_name = cfg["airtable"]["tables"]["main_list"]

    meta = fetch_tables_meta(base_id, api_key)
    tables = meta.get("tables") or []
    table = next((t for t in tables if t.get("name") == table_name), None)
    if not table:
        print(f"Table not found: {table_name}")
        return

    fields = table.get("fields") or []
    by_name = {f.get("name"): f for f in fields if f.get("name")}

    interesting = [
        "Inf",
        "Youth",
        "Net Rate",
        "Total price USD",
        "Total price GBP",
        "Amount",
        "Currency",
        "Supplier Name & Phone",
        "Driver Name & Phone",
        "Tour Guide Name & Phone",
        "Representative Name & Phone",
    ]

    def summarize_field(name: str):
        f = by_name.get(name)
        if not f:
            return {"name": name, "exists": False}
        t = f.get("type")
        opts = f.get("options") or {}
        linked_table = None
        if t == "multipleRecordLinks":
            linked_table = (opts.get("linkedTableId") or opts.get("linkedTable") or None)
        return {
            "name": name,
            "exists": True,
            "type": t,
            "read_only": t in READ_ONLY_TYPES,
            "is_linked": t in LINK_TYPES or t == "multipleRecordLinks",
            "linked_table_id": linked_table,
        }

    print("Airtable Field Audit (schema only)")
    print(f"Table: {table_name}")
    print("")

    print("Target fields:")
    for name in interesting:
        s = summarize_field(name)
        if not s["exists"]:
            print(f"- {name}: NOT FOUND")
            continue
        extra = []
        extra.append(f"type={s['type']}")
        if s["read_only"]:
            extra.append("READ_ONLY")
        if s["is_linked"]:
            extra.append("LINKED")
        print(f"- {name}: " + ", ".join(extra))

    ro = 0
    linked = 0
    for f in fields:
        t = f.get("type")
        if t in READ_ONLY_TYPES:
            ro += 1
        if t in LINK_TYPES or t == "multipleRecordLinks":
            linked += 1

    print("")
    print(f"Totals: fields={len(fields)}, read_only={ro}, linked_like={linked}")


if __name__ == "__main__":
    main()

