import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")


def sync_locations():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from pyairtable import Api
    from fts_paths import get_data_path
    import chat_db
    from chat_location import derive_chat_location_from_des, extract_des_from_fields

    with open(get_data_path("config.json"), "r", encoding="utf-8") as f:
        config = json.load(f)

    api = Api(config["airtable"]["api_key"])
    table = api.table(config["airtable"]["base_id"], config["airtable"]["tables"]["main_list"])

    import sqlite3

    conn = sqlite3.connect(get_data_path("chat_history.db"), timeout=30)
    c = conn.cursor()
    c.execute(
        """
        SELECT chat_id, airtable_record_id, location, booking_number
        FROM conversations
        WHERE airtable_record_id IS NOT NULL AND airtable_record_id != ''
        """
    )
    conversations = c.fetchall()
    conn.close()

    updated_count = 0
    skipped_no_des = 0
    for chat_id, record_id, current_loc, booking_nr in conversations:
        try:
            record = table.get(record_id)
            fields = record.get("fields", {}) if isinstance(record, dict) else {}
            des = extract_des_from_fields(fields)
            if not des:
                skipped_no_des += 1
                continue

            new_loc = derive_chat_location_from_des(des)
            if new_loc != (current_loc or "").strip():
                chat_db.update_conversation_info(chat_id=chat_id, location=new_loc)
                updated_count += 1
                print(
                    f"Updated {booking_nr or chat_id} ({record_id}): "
                    f"{current_loc} -> {new_loc} (des={des!r})"
                )
        except Exception as e:
            print(f"Skip {record_id}: {e}")

    print(
        f"Sync complete. Updated {updated_count} conversation(s); "
        f"skipped {skipped_no_des} with empty des."
    )


if __name__ == "__main__":
    sync_locations()
