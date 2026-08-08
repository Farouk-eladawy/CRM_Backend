"""
Ad Follow-up Automation for Ad ID: 120246971083710757
Sends a follow-up message 23 hours after the last message in the conversation.

Usage:
    from workflow_ad_followup_120246971083710757 import run
    result = run(agent, payload)
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

# Target ad ID
TARGET_AD_ID = "120246971083710757"

# Follow-up message
FOLLOWUP_MESSAGE = "أهلًا بحضرتك تاني 🌿"

# Time threshold: 23 hours
FOLLOWUP_HOURS = 23

# DB path (same as chat_db)
from fts_paths import get_data_path
DB_FILE = get_data_path('chat_history.db')

# Track sent follow-ups to avoid duplicates
SENT_FOLLOWUPS_KEY = "ad_followup_120246971083710757_sent"


def get_ad_conversations(cursor) -> list:
    """Get all conversations that came from the target ad ID."""
    cursor.execute(
        """
        SELECT chat_id, sender_identifier, contact_name, last_message_time, source,
               facebook_ad_id, receiving_phone_id, location
        FROM conversations
        WHERE facebook_ad_id = ?
          AND (is_deleted IS NULL OR is_deleted = 0)
        ORDER BY last_message_time DESC
        """,
        (TARGET_AD_ID,)
    )
    rows = cursor.fetchall()
    return [
        {
            "chat_id": r[0],
            "sender_identifier": r[1] or "",
            "contact_name": r[2] or "",
            "last_message_time": r[3] or "",
            "source": r[4] or "Facebook",
            "facebook_ad_id": r[5] or "",
            "receiving_phone_id": r[6] or "",
            "location": r[7] or "Unknown",
        }
        for r in rows
    ]


def get_last_message_time_for_chat(cursor, chat_id: str) -> Optional[datetime]:
    """Get the timestamp of the last message in a conversation."""
    cursor.execute(
        """
        SELECT timestamp FROM messages
        WHERE chat_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (chat_id,)
    )
    row = cursor.fetchone()
    if row and row[0]:
        try:
            # Parse ISO format timestamp
            ts_str = str(row[0])
            if 'T' in ts_str:
                return datetime.fromisoformat(ts_str)
            else:
                return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return None
    return None


def load_sent_followups(agent) -> set:
    """Load the set of chat_ids that already received the follow-up."""
    try:
        state = agent.load_state(SENT_FOLLOWUPS_KEY) or {}
        return set(state.get("sent", []))
    except Exception:
        return set()


def save_sent_followup(agent, chat_id: str):
    """Mark a chat_id as having received the follow-up."""
    try:
        state = agent.load_state(SENT_FOLLOWUPS_KEY) or {}
        sent = set(state.get("sent", []))
        sent.add(chat_id)
        agent.save_state(SENT_FOLLOWUPS_KEY, {"sent": list(sent)})
    except Exception as e:
        logging.error(f"Failed to save follow-up state for {chat_id}: {e}")


def send_followup_message(agent, conv: dict) -> bool:
    """Send the follow-up message to the customer."""
    source = str(conv.get("source") or "").strip().lower()
    sender_id = str(conv.get("sender_identifier") or "").strip()
    chat_id = str(conv.get("chat_id") or "").strip()

    if not sender_id:
        logging.warning(f"[AdFollowup] No sender identifier for chat {chat_id}")
        return False

    try:
        if source == "whatsapp" or (sender_id.startswith("20") and len(sender_id) > 10):
            # Send via WhatsApp
            location = str(conv.get("location") or "Unknown").strip()
            receiving_phone_id = str(conv.get("receiving_phone_id") or "").strip() or None
            ok, resp = agent.send_whatsapp_message(
                sender_id,
                text=FOLLOWUP_MESSAGE,
                location=location,
                receiving_phone_id=receiving_phone_id,
            )
            if ok:
                logging.info(f"[AdFollowup] WhatsApp follow-up sent to {sender_id} (chat: {chat_id})")
                # Log the message to chat history
                try:
                    import chat_db
                    chat_db.add_message(
                        chat_id=chat_id,
                        sender_type="agent",
                        text=FOLLOWUP_MESSAGE,
                        status="sent",
                        source="WhatsApp",
                    )
                except Exception as e:
                    logging.warning(f"[AdFollowup] Failed to log WhatsApp message: {e}")
                return True
            else:
                logging.warning(f"[AdFollowup] WhatsApp send failed for {sender_id}: {resp}")
                return False

        else:
            # Send via Facebook Messenger
            ok, resp = agent.send_facebook_message(sender_id, text=FOLLOWUP_MESSAGE)
            if ok:
                logging.info(f"[AdFollowup] Facebook follow-up sent to {sender_id} (chat: {chat_id})")
                # Log the message to chat history
                try:
                    import chat_db
                    chat_db.add_message(
                        chat_id=chat_id,
                        sender_type="agent",
                        text=FOLLOWUP_MESSAGE,
                        status="sent",
                        source="Facebook",
                    )
                except Exception as e:
                    logging.warning(f"[AdFollowup] Failed to log Facebook message: {e}")
                return True
            else:
                logging.warning(f"[AdFollowup] Facebook send failed for {sender_id}: {resp}")
                return False

    except Exception as e:
        logging.error(f"[AdFollowup] Error sending follow-up to {sender_id}: {e}")
        return False


def run(agent, payload: dict = None) -> dict:
    """
    Main entry point called by the automation engine.
    
    Args:
        agent: The AIAgent instance
        payload: Optional dict with override parameters
    
    Returns:
        dict with keys: ok, sent_count, errors, message
    """
    logging.info(f"[AdFollowup] Starting follow-up check for ad {TARGET_AD_ID}")
    
    try:
        conn = sqlite3.connect(DB_FILE, timeout=15.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        error_msg = f"Failed to connect to database: {e}"
        logging.error(f"[AdFollowup] {error_msg}")
        return {"ok": False, "sent_count": 0, "errors": [error_msg], "message": error_msg}

    try:
        # Get all conversations from the target ad
        conversations = get_ad_conversations(cursor)
        logging.info(f"[AdFollowup] Found {len(conversations)} conversations from ad {TARGET_AD_ID}")

        if not conversations:
            return {"ok": True, "sent_count": 0, "errors": [], "message": "No conversations found for this ad"}

        # Load already-sent follow-ups
        sent_already = load_sent_followups(agent)
        now = datetime.now(timezone.utc)
        sent_count = 0
        errors = []

        for conv in conversations:
            chat_id = conv["chat_id"]
            sender_id = conv["sender_identifier"]

            # Skip if no sender ID
            if not sender_id:
                continue

            # Skip if already sent
            if chat_id in sent_already:
                continue

            # Get the last message timestamp (from customer OR agent - both count)
            # The follow-up sends 23 hours after ANY last message activity
            last_msg_time = get_last_message_time_for_chat(cursor, chat_id)
            if not last_msg_time:
                logging.info(f"[AdFollowup] Skipping chat {chat_id}: no message timestamp")
                continue

            # Make timezone-aware
            if last_msg_time.tzinfo is None:
                last_msg_time = last_msg_time.replace(tzinfo=timezone.utc)

            # Check if 23 hours have passed
            elapsed = now - last_msg_time
            if elapsed.total_seconds() < FOLLOWUP_HOURS * 3600:
                # Not yet time, skip
                hours_remaining = (FOLLOWUP_HOURS * 3600 - elapsed.total_seconds()) / 3600
                logging.info(
                    f"[AdFollowup] Chat {chat_id}: only {elapsed.total_seconds()/3600:.1f}h elapsed, "
                    f"need {FOLLOWUP_HOURS}h. Waiting {hours_remaining:.1f}h more."
                )
                continue

            # Send the follow-up
            logging.info(f"[AdFollowup] Sending follow-up to chat {chat_id} ({sender_id})")
            success = send_followup_message(agent, conv)
            
            if success:
                sent_count += 1
                save_sent_followup(agent, chat_id)
                sent_already.add(chat_id)
            else:
                errors.append(f"Failed to send to {sender_id} (chat: {chat_id})")

        message = f"Sent {sent_count} follow-up message(s) with {len(errors)} error(s)"
        logging.info(f"[AdFollowup] {message}")
        
        return {
            "ok": len(errors) == 0,
            "sent_count": sent_count,
            "errors": errors,
            "message": message,
        }

    except Exception as e:
        error_msg = f"Error in ad follow-up run: {e}"
        logging.error(f"[AdFollowup] {error_msg}")
        return {"ok": False, "sent_count": 0, "errors": [error_msg], "message": error_msg}
    finally:
        try:
            conn.close()
        except Exception:
            pass
