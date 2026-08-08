import argparse
import json
import sqlite3
from typing import Dict, Tuple

from pyairtable import Table


def _load_airtable_table() -> Table:
    with open("config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
    api_key = str(((cfg.get("airtable") or {}).get("api_key") or "")).strip()
    base_id = str(((cfg.get("airtable") or {}).get("base_id") or "")).strip()
    table_name = str((((cfg.get("airtable") or {}).get("tables") or {}).get("main_list") or "")).strip()
    if not api_key or not base_id or not table_name:
        raise RuntimeError("Missing Airtable config (api_key/base_id/main_list)")
    return Table(api_key, base_id, table_name)


def _lookup_airtable_record_id(tbl: Table, booking_number: str) -> str:
    booking_number = str(booking_number or "").strip()
    if not booking_number:
        return ""
    formula = "{{Booking Nr.}}='{}'".format(booking_number.replace("'", "\\'"))
    recs = tbl.all(formula=formula, max_records=1)
    if not recs:
        return ""
    return str(recs[0].get("id") or "").strip()


def _parse_mapping(items) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for x in items or []:
        x = str(x or "").strip()
        if not x:
            continue
        if "=" in x:
            chat_id, booking = x.split("=", 1)
        elif ":" in x:
            chat_id, booking = x.split(":", 1)
        else:
            raise RuntimeError(f"Invalid --map value: {x}")
        chat_id = chat_id.strip()
        booking = booking.strip()
        if not chat_id or not booking:
            raise RuntimeError(f"Invalid --map value: {x}")
        out[chat_id] = booking
    if not out:
        raise RuntimeError("No mappings provided")
    return out


def _get_conv(cur, chat_id: str) -> Tuple[str, str, str, str]:
    cur.execute(
        "SELECT sender_identifier, thread_id, booking_number, airtable_record_id FROM conversations WHERE chat_id = ?",
        (chat_id,),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Conversation not found: {chat_id}")
    return (row[0] or "", row[1] or "", row[2] or "", row[3] or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="chat_history.db")
    ap.add_argument("--map", action="append", dest="maps", default=[])
    args = ap.parse_args()

    mapping = _parse_mapping(args.maps)
    tbl = _load_airtable_table()

    conn = sqlite3.connect(str(args.db), timeout=30.0)
    try:
        conn.execute("PRAGMA busy_timeout = 30000;")
    except Exception:
        pass
    cur = conn.cursor()

    for chat_id, booking_number in mapping.items():
        sender_identifier, thread_id, old_booking, old_airtable = _get_conv(cur, chat_id)
        airtable_id = _lookup_airtable_record_id(tbl, booking_number)

        base_sender = sender_identifier.split("::")[0].strip() if sender_identifier else ""
        base_thread = thread_id.split(":")[0].strip() if thread_id else ""

        new_sender = (base_sender + "::" + booking_number) if base_sender else ("::" + booking_number)
        new_thread = (base_thread + ":" + booking_number) if base_thread else booking_number

        cur.execute(
            "UPDATE conversations SET booking_number = ?, airtable_record_id = ?, sender_identifier = ?, thread_id = ? WHERE chat_id = ?",
            (booking_number, airtable_id, new_sender, new_thread, chat_id),
        )

        print(
            json.dumps(
                {
                    "chat_id": chat_id,
                    "old_booking_number": old_booking,
                    "new_booking_number": booking_number,
                    "old_airtable_record_id": old_airtable,
                    "new_airtable_record_id": airtable_id,
                },
                ensure_ascii=False,
            )
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
