import sqlite3
import re
import os

DB_FILE = 'chat_history.db'

def clean_andrew_mirman():
    """
    Merge the duplicate conversations for Andrew Mirman and attempt to link them to the correct Airtable Record.
    """
    if not os.path.exists(DB_FILE):
        print(f"Database {DB_FILE} not found.")
        return

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Find all Andrew Mirman conversations
    c.execute("SELECT * FROM conversations WHERE contact_name LIKE '%Andrew Mirman%' OR sender_identifier LIKE '%expressmessaging.tripadvisor.com%'")
    conversations = c.fetchall()

    if len(conversations) <= 1:
        print("No duplicate conversations found for Andrew Mirman.")
        conn.close()
        return

    print(f"Found {len(conversations)} conversations for Andrew Mirman. Merging...")

    # Find the primary conversation (the one that has an airtable record ID if any)
    primary_conv = None
    for conv in conversations:
        if conv['airtable_record_id']:
            primary_conv = conv
            break
            
    if not primary_conv:
        # If none have an Airtable ID, just pick the first one
        primary_conv = conversations[0]
        
    primary_id = primary_conv['chat_id']
    print(f"Primary Chat ID: {primary_id}")

    # Merge messages from others into primary
    for conv in conversations:
        if conv['chat_id'] != primary_id:
            old_id = conv['chat_id']
            print(f"Moving messages from {old_id} to {primary_id}")
            
            # Update messages
            c.execute("UPDATE messages SET chat_id = ? WHERE chat_id = ?", (primary_id, old_id))
            
            # Delete old conversation
            c.execute("DELETE FROM conversations WHERE chat_id = ?", (old_id,))
            print(f"Deleted old conversation: {old_id}")

    conn.commit()
    print("Successfully merged Andrew Mirman conversations!")
    
    # We will let the frontend logic group them properly now that the duplicate records are cleared.
    conn.close()

if __name__ == "__main__":
    clean_andrew_mirman()
