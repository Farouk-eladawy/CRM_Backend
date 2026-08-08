import chat_db

# Try to find an unassigned Religious chat
with chat_db.sqlite3.connect(chat_db.DB_FILE) as conn:
    conn.row_factory = chat_db.sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT chat_id FROM conversations WHERE location = 'Religious' AND lead_owner_user_id IS NULL LIMIT 1")
    row = c.fetchone()
    
if row:
    chat_id = row['chat_id']
    print("Found unassigned chat:", chat_id)
    # Assign it
    try:
        chat_db.assign_sales_lead(chat_id, "1783238796933", "Ahmady_Tester")
        print("Assigned successfully.")
    except Exception as e:
        print("Error assigning:", e)
else:
    print("No unassigned Religious chats found.")