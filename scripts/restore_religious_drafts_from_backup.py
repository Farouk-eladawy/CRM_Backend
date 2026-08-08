import argparse
import json
import os
import sqlite3
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "chat_history.db")
BACKUP_DIR = os.path.join(BASE_DIR, "migration_backups")


def load_backup(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_message_columns(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(messages)")
    return [row[1] for row in cur.fetchall()]


def fetch_current_drafts(cur, chat_id):
    cur.execute(
        """
        SELECT *
        FROM messages
        WHERE chat_id = ?
          AND text LIKE '[PROPOSED_DRAFT]%'
        ORDER BY timestamp ASC, msg_id ASC
        """,
        (chat_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def normalize_drafts(rows):
    normalized = []
    for row in rows or []:
        normalized.append(
            {
                "text": str(row.get("text") or ""),
                "sender_type": str(row.get("sender_type") or ""),
                "status": str(row.get("status") or ""),
                "source": str(row.get("source") or "") if row.get("source") is not None else None,
            }
        )
    return normalized


def restore_backup(backup_path, dry_run=False):
    payload = load_backup(backup_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    result_path = os.path.join(BACKUP_DIR, f"religious_recent_100_restore_result_{ts}.json")

    with sqlite3.connect(DB_PATH, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        message_columns = get_message_columns(conn)

        restored = 0
        unchanged = 0
        errors = 0
        items = []

        for entry in payload:
            conv = entry.get("conversation") or {}
            chat_id = str(conv.get("chat_id") or "").strip()
            if not chat_id:
                continue

            backup_messages = entry.get("messages") or []
            backup_drafts = [m for m in backup_messages if str(m.get("text") or "").startswith("[PROPOSED_DRAFT]")]

            try:
                current_drafts = fetch_current_drafts(cur, chat_id)
                if normalize_drafts(current_drafts) == normalize_drafts(backup_drafts):
                    unchanged += 1
                    items.append(
                        {
                            "chat_id": chat_id,
                            "status": "unchanged",
                            "backup_drafts": len(backup_drafts),
                            "current_drafts": len(current_drafts),
                        }
                    )
                    continue

                if not dry_run:
                    cur.execute(
                        """
                        DELETE FROM messages
                        WHERE chat_id = ?
                          AND text LIKE '[PROPOSED_DRAFT]%'
                        """,
                        (chat_id,),
                    )

                    if backup_drafts:
                        insertable_columns = [col for col in message_columns if col in backup_drafts[0]]
                        placeholders = ", ".join(["?"] * len(insertable_columns))
                        columns_sql = ", ".join(insertable_columns)
                        sql = f"INSERT INTO messages ({columns_sql}) VALUES ({placeholders})"
                        for row in backup_drafts:
                            values = [row.get(col) for col in insertable_columns]
                            cur.execute(sql, values)

                restored += 1
                items.append(
                    {
                        "chat_id": chat_id,
                        "status": "restored",
                        "backup_drafts": len(backup_drafts),
                        "current_drafts_before_restore": len(current_drafts),
                    }
                )
            except Exception as e:
                errors += 1
                items.append(
                    {
                        "chat_id": chat_id,
                        "status": "error",
                        "error": str(e),
                    }
                )

        if not dry_run:
            conn.commit()

    summary = {
        "backup_path": backup_path,
        "dry_run": bool(dry_run),
        "restored": restored,
        "unchanged": unchanged,
        "errors": errors,
        "items": items,
    }
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(result_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    restore_backup(args.backup, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
