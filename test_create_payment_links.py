import json
import sqlite3
import time
import requests

from pyairtable import Api


def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def pick_record_id_from_chat_db():
    with sqlite3.connect("chat_history.db", timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            """
            SELECT airtable_record_id
            FROM conversations
            WHERE airtable_record_id IS NOT NULL AND airtable_record_id != ''
            ORDER BY last_message_time DESC
            LIMIT 1
            """
        )
        row = c.fetchone()
    if not row:
        return None
    return str(row["airtable_record_id"]).strip() or None


def main():
    cfg = load_config()
    base_id = cfg["airtable"]["base_id"]
    table_name = cfg["airtable"]["tables"]["main_list"]
    api = Api(cfg["airtable"]["api_key"])
    table = api.table(base_id, table_name)

    record_id = pick_record_id_from_chat_db()
    if not record_id:
        raise SystemExit("No airtable_record_id found in chat_history.db")

    before = table.get(record_id)
    before_fields = (before or {}).get("fields", {}) or {}
    snapshot = {
        "Trip UUID": before_fields.get("Trip UUID"),
        "Stripe invoice": before_fields.get("Stripe invoice"),
        "Invoice Status": before_fields.get("Invoice Status"),
    }

    print("record_id:", record_id)
    print("snapshot:", json.dumps(snapshot, ensure_ascii=False))

    url = "http://127.0.0.1:5001/api/payments/create"

    print("\n--- Stripe test (USD) ---")
    r1 = requests.post(
        url,
        json={"record_id": record_id, "amount": 1, "currency": "USD"},
        timeout=60,
    )
    print("status:", r1.status_code)
    print(r1.text[:2000])

    time.sleep(1)

    print("\n--- WeTravel test (EUR) ---")
    r2 = requests.post(
        url,
        json={"record_id": record_id, "amount": 1, "currency": "EUR"},
        timeout=60,
    )
    print("status:", r2.status_code)
    print(r2.text[:2000])

    time.sleep(1)

    print("\n--- restore Airtable fields ---")
    table.update(record_id, snapshot)
    print("restored")


if __name__ == "__main__":
    main()

