import sqlite3
import os
import uuid
import datetime

DB_NAME = 'internal_chats.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            group_id TEXT PRIMARY KEY,
            name TEXT,
            created_by TEXT,
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS group_members (
            group_id TEXT,
            user_id TEXT,
            PRIMARY KEY (group_id, user_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS internal_messages (
            msg_id TEXT PRIMARY KEY,
            chat_id TEXT, -- group_id or target_user_id (for DMs)
            sender_id TEXT,
            text TEXT,
            timestamp TEXT,
            is_group BOOLEAN,
            read_by TEXT DEFAULT ''
        )
    ''')
    # For existing DB migrations:
    try:
        c.execute('ALTER TABLE internal_messages ADD COLUMN read_by TEXT DEFAULT ""')
    except:
        pass
    try:
        c.execute('ALTER TABLE internal_messages ADD COLUMN attachment_url TEXT DEFAULT ""')
    except:
        pass
    conn.commit()
    conn.close()

def create_group(name, created_by, member_ids):
    conn = get_db()
    c = conn.cursor()
    group_id = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()
    c.execute('INSERT INTO groups (group_id, name, created_by, created_at) VALUES (?, ?, ?, ?)', (group_id, name, created_by, now))
    for uid in member_ids:
        c.execute('INSERT INTO group_members (group_id, user_id) VALUES (?, ?)', (group_id, uid))
    conn.commit()
    conn.close()
    return group_id

def get_groups_for_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT g.* FROM groups g
        JOIN group_members gm ON g.group_id = gm.group_id
        WHERE gm.user_id = ?
    ''', (user_id,))
    groups = [dict(row) for row in c.fetchall()]
    conn.close()
    return groups

def get_all_groups():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM groups')
    groups = [dict(row) for row in c.fetchall()]
    
    for group in groups:
        c.execute('SELECT user_id FROM group_members WHERE group_id = ?', (group['group_id'],))
        group['member_ids'] = [r['user_id'] for r in c.fetchall()]
    conn.close()
    return groups

def send_message(chat_id, sender_id, text, is_group=False, attachment_url=""):
    conn = get_db()
    c = conn.cursor()
    msg_id = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()
    
    # ensure migration is applied if not already
    try:
        c.execute('ALTER TABLE internal_messages ADD COLUMN attachment_url TEXT DEFAULT ""')
    except:
        pass
        
    c.execute('INSERT INTO internal_messages (msg_id, chat_id, sender_id, text, timestamp, is_group, attachment_url) VALUES (?, ?, ?, ?, ?, ?, ?)',
              (msg_id, chat_id, sender_id, text, now, is_group, attachment_url))
    conn.commit()
    conn.close()
    return msg_id

def get_messages(chat_id, is_group=False, user1=None, user2=None):
    conn = get_db()
    c = conn.cursor()
    if is_group:
        c.execute('SELECT * FROM internal_messages WHERE chat_id = ? AND is_group = 1 ORDER BY timestamp ASC', (chat_id,))
    else:
        # For DMs, chat_id is stored as the target user. We need to match where (sender=user1 and chat=user2) OR (sender=user2 and chat=user1)
        c.execute('''
            SELECT * FROM internal_messages 
            WHERE is_group = 0 AND 
            ((sender_id = ? AND chat_id = ?) OR (sender_id = ? AND chat_id = ?))
            ORDER BY timestamp ASC
        ''', (user1, user2, user2, user1))
    messages = [dict(row) for row in c.fetchall()]
    conn.close()
    return messages

def update_group_members(group_id, member_ids):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM group_members WHERE group_id = ?', (group_id,))
    for uid in member_ids:
        c.execute('INSERT INTO group_members (group_id, user_id) VALUES (?, ?)', (group_id, uid))
    conn.commit()
    conn.close()

def mark_messages_as_read(chat_id, user_id, is_group=False, sender_id=None):
    conn = get_db()
    c = conn.cursor()
    search_token = f"|{user_id}|"
    if is_group:
        # Mark all messages in the group as read by this user, where the user hasn't read them yet
        c.execute('''
            UPDATE internal_messages
            SET read_by = read_by || ?
            WHERE chat_id = ? AND is_group = 1 AND read_by NOT LIKE ?
        ''', (search_token, chat_id, f"%{search_token}%"))
    else:
        # For DMs, we only mark messages sent BY the other person TO us as read.
        # chat_id from our perspective is the other person's ID (sender_id).
        # And the messages were sent to us, so the message chat_id is our user_id.
        c.execute('''
            UPDATE internal_messages
            SET read_by = read_by || ?
            WHERE is_group = 0 AND sender_id = ? AND chat_id = ? AND read_by NOT LIKE ?
        ''', (search_token, chat_id, user_id, f"%{search_token}%"))
    conn.commit()
    conn.close()

def get_unread_counts(user_id):
    conn = get_db()
    c = conn.cursor()
    search_token = f"|{user_id}|"
    
    # DMs: Messages sent to user_id, not read by user_id
    c.execute('''
        SELECT sender_id as chat_id, COUNT(*) as count
        FROM internal_messages
        WHERE is_group = 0 AND chat_id = ? AND read_by NOT LIKE ?
        GROUP BY sender_id
    ''', (user_id, f"%{search_token}%"))
    dm_counts = {row['chat_id']: row['count'] for row in c.fetchall()}
    
    # Groups: Messages in groups the user is a member of, not read by user_id, and not sent by user_id
    c.execute('''
        SELECT m.chat_id, COUNT(*) as count
        FROM internal_messages m
        JOIN group_members gm ON m.chat_id = gm.group_id
        WHERE m.is_group = 1 AND gm.user_id = ? AND m.sender_id != ? AND m.read_by NOT LIKE ?
        GROUP BY m.chat_id
    ''', (user_id, user_id, f"%{search_token}%"))
    group_counts = {row['chat_id']: row['count'] for row in c.fetchall()}
    
    conn.close()
    
    # Merge dictionaries
    merged = {**dm_counts, **group_counts}
    return merged

if not os.path.exists(DB_NAME):
    init_db()
