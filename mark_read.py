import sqlite3
import datetime
from chat_db import DB_FILE, get_cairo_time

def add_force_read():
    with sqlite3.connect(DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(conversations)")
        columns = [col[1] for col in c.fetchall()]
        if 'force_read_at' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN force_read_at TIMESTAMP")
            
        now = get_cairo_time()
        # Mark all as read
        c.execute("UPDATE conversations SET force_read_at = ?", (now,))
        conn.commit()
        print("All conversations marked as read.")

if __name__ == "__main__":
    add_force_read()
