import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime

from pyairtable import Table

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import chat_db
from airtable_fields import FieldIds, LeadFieldIds, LEADS_TABLE_NAME


DB_PATH = os.path.join(PROJECT_ROOT, "chat_history.db")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")


CONVERSATION_REPAIRS = {
    "a99ce367-dc3b-420d-b787-fb2ed15711af": {
        "label": "Rongrong Zhang",
        "contact_name": "Rongrong Zhang",
        "airtable_record_id": "recGjpB5ThtsbROGL",
        "booking_number": None,
        "sender_identifier": "rr_zhang@trip.com",
        "thread_id": "19eb70c15337558f",
    },
    "506b1180-ec02-468e-8d70-961cffd53f03": {
        "label": "Fabio Covelli",
        "contact_name": "Fabio Covelli",
        "airtable_record_id": "rec0USG4nMhweiXj7",
        "booking_number": "BR-1408048409",
        "sender_identifier": "fabcov@gmail.com",
        "thread_id": "19ebc6a3dabd1273",
    },
    "6cbb3ea3-443b-4e3d-b183-4368e4ec7ce5": {
        "label": "Gelsomina Rozza",
        "contact_name": "Gelsomina Rozza",
        "airtable_record_id": "recyzD5K9lYnEtUpH",
        "booking_number": None,
        "sender_identifier": "rozzagelsomina@gmail.com",
        "thread_id": "19ebd4dfba8283d8",
    },
    "aee24b48-5381-4116-95da-9c67ad490b99": {
        "label": "Anna Konate",
        "contact_name": "Anna Konate",
        "airtable_record_id": "recjdOr7j8X48Lr85",
        "booking_number": "GYGFWV66NVKB",
        "sender_identifier": "customer-7jlsqqxat6zpfaa7@reply.getyourguide.com::GYGFWV66NVKB",
        "thread_id": "19eb2be0579ae625:GYGFWV66NVKB",
    },
}


MESSAGE_MOVE_RULES = [
    {
        "source_chat_id": "a99ce367-dc3b-420d-b787-fb2ed15711af",
        "target_chat_id": "6cbb3ea3-443b-4e3d-b183-4368e4ec7ce5",
        "min_timestamp": "2026-06-12T22:40:00",
        "sender_types": ("ai", "agent"),
        "reason": "Moved Gelsomina follow-up replies out of Rongrong thread",
    }
]


AIRTABLE_PATCHES = [
    {
        "table": "main",
        "record_id": "rec0USG4nMhweiXj7",
        "fields": {
            FieldIds.ROOM_NUMBER: "8181",
            FieldIds.HOTEL_NAME: "Reef Oasis Beach Aqua Park Resort",
            FieldIds.CUSTOMER_PERSONAL_EMAIL: "fabcov@gmail.com",
            FieldIds.CUSTOMER_NAME: "Fabio Covelli",
        },
    },
    {
        "table": "leads",
        "record_id": "recGjpB5ThtsbROGL",
        "fields": {
            LeadFieldIds.CUSTOMER_NAME: "Rongrong Zhang",
            LeadFieldIds.CUSTOMER_EMAIL: "rr_zhang@trip.com",
        },
    },
    {
        "table": "leads",
        "record_id": "recyzD5K9lYnEtUpH",
        "fields": {
            LeadFieldIds.CUSTOMER_NAME: "Gelsomina Rozza",
            LeadFieldIds.CUSTOMER_EMAIL: "rozzagelsomina@gmail.com",
        },
    },
]


def _load_tables():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    airtable_cfg = cfg.get("airtable") or {}
    api_key = str(airtable_cfg.get("api_key") or "").strip()
    base_id = str(airtable_cfg.get("base_id") or "").strip()
    tables_cfg = airtable_cfg.get("tables") or {}
    main_table_name = str(tables_cfg.get("main_list") or "").strip()
    if not api_key or not base_id or not main_table_name:
        raise RuntimeError("Missing Airtable configuration")
    main_table = Table(api_key, base_id, main_table_name)
    leads_table = Table(api_key, base_id, LEADS_TABLE_NAME)
    return main_table, leads_table


def _backup_db():
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(os.path.dirname(DB_PATH), f"chat_history.backup_{ts}.db")
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def _fetch_conversation(cur, chat_id):
    cur.execute(
        """
        SELECT chat_id, source, sender_identifier, contact_name, airtable_record_id,
               booking_number, thread_id, is_deleted, last_message_time
        FROM conversations
        WHERE chat_id = ?
        """,
        (chat_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _refresh_chat_stats(cur, chat_id):
    cur.execute("SELECT MAX(timestamp) FROM messages WHERE chat_id = ?", (chat_id,))
    last_ts = cur.fetchone()[0]
    cur.execute(
        """
        SELECT COUNT(*)
        FROM messages
        WHERE chat_id = ? AND sender_type = 'customer'
        """,
        (chat_id,),
    )
    unread_count = int(cur.fetchone()[0] or 0)
    cur.execute(
        """
        UPDATE conversations
        SET last_message_time = COALESCE(?, last_message_time),
            unread_count = ?
        WHERE chat_id = ?
        """,
        (last_ts, unread_count, chat_id),
    )


def _move_messages(cur, rule):
    cur.execute(
        """
        SELECT msg_id, timestamp, sender_type, text
        FROM messages
        WHERE chat_id = ?
          AND timestamp >= ?
          AND sender_type IN ({})
        ORDER BY timestamp ASC
        """.format(",".join(["?"] * len(rule["sender_types"]))),
        [rule["source_chat_id"], rule["min_timestamp"], *rule["sender_types"]],
    )
    rows = [dict(r) for r in cur.fetchall()]
    if not rows:
        return []
    msg_ids = [r["msg_id"] for r in rows]
    cur.execute(
        "UPDATE messages SET chat_id = ? WHERE msg_id IN ({})".format(",".join(["?"] * len(msg_ids))),
        [rule["target_chat_id"], *msg_ids],
    )
    return rows


def _apply_conversation_repairs(cur):
    report = []
    for chat_id, target in CONVERSATION_REPAIRS.items():
        before = _fetch_conversation(cur, chat_id)
        if not before:
            raise RuntimeError(f"Conversation not found: {chat_id}")
        cur.execute(
            """
            UPDATE conversations
            SET contact_name = ?,
                airtable_record_id = ?,
                booking_number = ?,
                sender_identifier = ?,
                thread_id = ?,
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL,
                deleted_reason = NULL
            WHERE chat_id = ?
            """,
            (
                target["contact_name"],
                target["airtable_record_id"],
                target["booking_number"],
                target["sender_identifier"],
                target["thread_id"],
                chat_id,
            ),
        )
        after = _fetch_conversation(cur, chat_id)
        report.append({"before": before, "after": after, "label": target["label"]})
    return report


def _apply_airtable_patches(main_table, leads_table):
    out = []
    for patch in AIRTABLE_PATCHES:
        table = main_table if patch["table"] == "main" else leads_table
        table.update(patch["record_id"], patch["fields"], typecast=True)
        out.append(
            {
                "table": patch["table"],
                "record_id": patch["record_id"],
                "field_count": len(patch["fields"]),
            }
        )
    return out


def _write_report(report):
    report_path = os.path.join(os.path.dirname(DB_PATH), "repair_conflicting_customer_threads.report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Execute the repair instead of dry-run")
    args = parser.parse_args()

    report = {
        "mode": "apply" if args.apply else "dry-run",
        "db_path": DB_PATH,
        "backup_path": None,
        "conversation_repairs": [],
        "message_moves": [],
        "airtable_patches": [],
        "post_checks": [],
    }

    main_table = None
    leads_table = None
    if args.apply:
        main_table, leads_table = _load_tables()
        report["backup_path"] = _backup_db()

    with sqlite3.connect(DB_PATH, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 30000;")
        cur = conn.cursor()

        if args.apply:
            report["conversation_repairs"] = _apply_conversation_repairs(cur)
            for rule in MESSAGE_MOVE_RULES:
                moved = _move_messages(cur, rule)
                report["message_moves"].append(
                    {
                        "source_chat_id": rule["source_chat_id"],
                        "target_chat_id": rule["target_chat_id"],
                        "reason": rule["reason"],
                        "moved_count": len(moved),
                        "messages": moved,
                    }
                )
            for chat_id in set(CONVERSATION_REPAIRS.keys()) | {r["source_chat_id"] for r in MESSAGE_MOVE_RULES} | {r["target_chat_id"] for r in MESSAGE_MOVE_RULES}:
                _refresh_chat_stats(cur, chat_id)
            conn.commit()
        else:
            report["conversation_repairs"] = [_fetch_conversation(cur, cid) for cid in CONVERSATION_REPAIRS.keys()]
            for rule in MESSAGE_MOVE_RULES:
                cur.execute(
                    """
                    SELECT msg_id, timestamp, sender_type, text
                    FROM messages
                    WHERE chat_id = ?
                      AND timestamp >= ?
                      AND sender_type IN ({})
                    ORDER BY timestamp ASC
                    """.format(",".join(["?"] * len(rule["sender_types"]))),
                    [rule["source_chat_id"], rule["min_timestamp"], *rule["sender_types"]],
                )
                report["message_moves"].append(
                    {
                        "source_chat_id": rule["source_chat_id"],
                        "target_chat_id": rule["target_chat_id"],
                        "reason": rule["reason"],
                        "moved_count": len(cur.fetchall()),
                    }
                )

        for chat_id in CONVERSATION_REPAIRS.keys():
            conv = _fetch_conversation(cur, chat_id)
            cur.execute("SELECT COUNT(*) FROM messages WHERE chat_id = ?", (chat_id,))
            msg_count = int(cur.fetchone()[0] or 0)
            report["post_checks"].append({"chat_id": chat_id, "conversation": conv, "message_count": msg_count})

    if args.apply:
        report["airtable_patches"] = _apply_airtable_patches(main_table, leads_table)
        chat_db.add_message(
            "506b1180-ec02-468e-8d70-961cffd53f03",
            sender_type="agent",
            text="[System Log] Conversation metadata repaired to booking BR-1408048409 and room 8181 restored.",
            increment_unread=False,
        )
        chat_db.add_message(
            "6cbb3ea3-443b-4e3d-b183-4368e4ec7ce5",
            sender_type="agent",
            text="[System Log] Conversation repaired after cross-chat contamination. Messages specific to Gelsomina were restored here.",
            increment_unread=False,
        )
        chat_db.add_message(
            "a99ce367-dc3b-420d-b787-fb2ed15711af",
            sender_type="agent",
            text="[System Log] Conversation metadata repaired to Rongrong Zhang lead after removing unrelated replies.",
            increment_unread=False,
        )

    report_path = _write_report(report)
    print(json.dumps({"status": "ok", "mode": report["mode"], "report_path": report_path, "backup_path": report["backup_path"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
