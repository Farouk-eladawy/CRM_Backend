import sqlite3
import json
import os
from datetime import datetime

DB_FILE = 'draft_audit.db'
CORRECTIONS_FILE = 'learned_corrections.json'

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS draft_tracking (
                draft_id TEXT PRIMARY KEY,
                thread_id TEXT,
                record_id TEXT,
                original_body TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                mailbox TEXT DEFAULT 'booking'
            )
        ''')
        try:
            c.execute("PRAGMA table_info(draft_tracking)")
            cols = [row[1] for row in c.fetchall()]
            if 'mailbox' not in cols:
                c.execute("ALTER TABLE draft_tracking ADD COLUMN mailbox TEXT DEFAULT 'booking'")
        except Exception:
            pass
        conn.commit()

def log_draft(draft_id, thread_id, record_id, original_body, mailbox='booking'):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO draft_tracking (draft_id, thread_id, record_id, original_body, mailbox) VALUES (?, ?, ?, ?, ?)",
                      (draft_id, thread_id, record_id, original_body, mailbox))
            conn.commit()
    except Exception as e:
        print(f"Error logging draft: {e}")

def get_pending_drafts():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM draft_tracking WHERE status = 'pending'")
            return [dict(row) for row in c.fetchall()]
    except Exception as e:
        print(f"Error getting pending drafts: {e}")
        return []

def get_pending_draft_for_thread(thread_id, mailbox=None):
    if not thread_id:
        return None
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            if mailbox:
                c.execute(
                    "SELECT * FROM draft_tracking WHERE status = 'pending' AND thread_id = ? AND mailbox = ? ORDER BY created_at DESC LIMIT 1",
                    (str(thread_id), str(mailbox)),
                )
            else:
                c.execute(
                    "SELECT * FROM draft_tracking WHERE status = 'pending' AND thread_id = ? ORDER BY created_at DESC LIMIT 1",
                    (str(thread_id),),
                )
            row = c.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error getting pending draft for thread: {e}")
        return None

def mark_draft_processed(draft_id, status='processed'):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("UPDATE draft_tracking SET status = ? WHERE draft_id = ?", (status, draft_id))
            conn.commit()
    except Exception as e:
        print(f"Error marking draft processed: {e}")

def save_correction(original, corrected, trigger_context=""):
    """Save the correction for future learning."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "original": original,
        "corrected": corrected,
        "context": trigger_context
    }
    
    data = []
    if os.path.exists(CORRECTIONS_FILE):
        try:
            with open(CORRECTIONS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            pass
            
    data.append(entry)
    
    # Keep only last 100 corrections to avoid context bloat
    if len(data) > 100:
        data = data[-100:]
        
    with open(CORRECTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_learning_examples():
    """Retrieve corrections to inject into prompt."""
    if not os.path.exists(CORRECTIONS_FILE):
        return []
    try:
        with open(CORRECTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []
