import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import chat_db
from ai_agent import AIAgent


DB_PATH = os.path.join(BASE_DIR, "chat_history.db")
BACKUP_DIR = os.path.join(BASE_DIR, "migration_backups")


def fetch_recent_religious_conversations(limit):
    with sqlite3.connect(DB_PATH, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT *
            FROM conversations
            WHERE location = 'Religious'
              AND COALESCE(is_deleted, 0) = 0
            ORDER BY last_message_time DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_backup_payload(conversations):
    payload = []
    with sqlite3.connect(DB_PATH, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        for conv in conversations:
            chat_id = str(conv.get("chat_id") or "").strip()
            if not chat_id:
                continue
            messages = cur.execute(
                """
                SELECT *
                FROM messages
                WHERE chat_id = ?
                ORDER BY timestamp ASC
                """,
                (chat_id,),
            ).fetchall()
            payload.append(
                {
                    "conversation": conv,
                    "messages": [dict(r) for r in messages],
                }
            )
    return payload


def save_backup(conversations):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"religious_recent_100_reprocess_backup_{ts}.json")
    payload = fetch_backup_payload(conversations)
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return backup_path


def build_reprocess_context(messages):
    if not messages:
        return None

    latest_customer_idx = None
    for idx in range(len(messages) - 1, -1, -1):
        if str(messages[idx].get("sender_type") or "").strip().lower() == "customer":
            latest_customer_idx = idx
            break

    if latest_customer_idx is None:
        return None

    latest_customer_message = str(messages[latest_customer_idx].get("text") or "").strip()
    if not latest_customer_message:
        return None

    relevant_messages = messages[: latest_customer_idx + 1]
    filtered = []
    for msg in relevant_messages:
        text = str(msg.get("text") or "").strip()
        if not text:
            continue
        if text.startswith("[PROPOSED_DRAFT]"):
            continue
        sender_type = str(msg.get("sender_type") or "").strip().lower()
        role = "User" if sender_type == "customer" else "AI"
        filtered.append(f"{role}: {text}")

    history_text = "\n".join(filtered[-10:])
    return {
        "latest_customer_message": latest_customer_message,
        "history_text": history_text,
        "latest_customer_timestamp": messages[latest_customer_idx].get("timestamp"),
    }


def make_subject(source, location):
    src = str(source or "").strip().lower()
    loc = str(location or "Unknown").strip() or "Unknown"
    if src == "facebook":
        return f"Facebook Message ({loc})"
    if src == "whatsapp":
        return f"WhatsApp Message ({loc})"
    if src == "email":
        return f"Email Message ({loc})"
    return f"{str(source or 'Message').strip()} ({loc})"


def count_existing_drafts(chat_id):
    with sqlite3.connect(DB_PATH, timeout=30.0) as conn:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT COUNT(*) FROM messages WHERE chat_id = ? AND text LIKE '[PROPOSED_DRAFT]%'",
            (chat_id,),
        ).fetchone()
        return int(row[0] or 0) if row else 0


def reprocess_chat(agent, conv, dry_run=False):
    chat_id = str(conv.get("chat_id") or "").strip()
    if not chat_id:
        return {"status": "skipped", "reason": "missing_chat_id"}

    messages = chat_db.get_messages(chat_id, merge_by_record=False) or []
    ctx = build_reprocess_context(messages)
    if not ctx:
        return {"status": "skipped", "chat_id": chat_id, "reason": "no_customer_context"}

    source = str(conv.get("source") or "").strip() or "Facebook"
    sender_identifier = str(conv.get("sender_identifier") or "").strip()
    location = str(conv.get("location") or "Unknown").strip() or "Unknown"
    subject = make_subject(source, location)
    existing_drafts = count_existing_drafts(chat_id)

    result = agent.process_unified_message(
        sender_identifier=sender_identifier,
        message_body=ctx["latest_customer_message"],
        history_text=ctx["history_text"],
        source=source,
        subject=subject,
        thread_id=conv.get("thread_id"),
        location=location,
        receiving_phone_id=conv.get("receiving_phone_id"),
        skip_db_save=True,
        email_account_id=conv.get("email_account_id"),
    )

    if not result:
        return {
            "status": "skipped",
            "chat_id": chat_id,
            "reason": "no_result",
            "existing_drafts": existing_drafts,
        }

    reply_text = str(result.get("response_text") or "").strip()
    if not reply_text:
        return {
            "status": "skipped",
            "chat_id": chat_id,
            "reason": "empty_reply",
            "existing_drafts": existing_drafts,
        }

    assistant_name, assistant_signature = agent._assistant_identity_for_text(ctx["latest_customer_message"])
    reply_text = agent._ensure_signature_once(reply_text, assistant_signature, chat_id=chat_id, location=location)
    stored_text = "[PROPOSED_DRAFT] " + reply_text

    if not dry_run:
        chat_db.delete_proposed_drafts(chat_id)
        chat_db.add_message(
            chat_id=chat_id,
            sender_type="agent",
            text=stored_text,
            status="sent",
            increment_unread=False,
            source=source,
        )

    return {
        "status": "processed",
        "chat_id": chat_id,
        "source": source,
        "location": location,
        "existing_drafts": existing_drafts,
        "latest_customer_message": ctx["latest_customer_message"],
        "latest_customer_timestamp": ctx["latest_customer_timestamp"],
        "new_draft_preview": reply_text[:500],
        "inquiry_intent": result.get("inquiry_intent"),
        "was_escalated": bool(result.get("was_escalated")),
        "strict_qa_rule_id": result.get("strict_qa_rule_id"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conversations = fetch_recent_religious_conversations(args.limit)
    backup_path = save_backup(conversations)
    agent = AIAgent()
    agent._suppress_chat_log_sync = True

    results = []
    processed = 0
    skipped = 0
    errors = 0

    for conv in conversations:
        chat_id = str(conv.get("chat_id") or "").strip()
        try:
            item = reprocess_chat(agent, conv, dry_run=args.dry_run)
            results.append(item)
            if item.get("status") == "processed":
                processed += 1
            else:
                skipped += 1
        except Exception as e:
            errors += 1
            results.append(
                {
                    "status": "error",
                    "chat_id": chat_id,
                    "error": str(e),
                }
            )

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = os.path.join(BACKUP_DIR, f"religious_recent_100_reprocess_result_{ts}.json")
    summary = {
        "limit": args.limit,
        "dry_run": bool(args.dry_run),
        "backup_path": backup_path,
        "result_path": result_path,
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
        "items": results,
    }
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
