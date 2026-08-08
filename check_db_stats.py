import sqlite3

def check_db(db_name):
    print(f"\n--- Checking {db_name} ---")
    try:
        conn = sqlite3.connect(db_name)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        if not tables:
            print("No tables found in the database.")
            return
        for table in tables:
            table_name = table[0]
            try:
                count = conn.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
                print(f"Table '{table_name}': {count} rows")
            except Exception as e:
                print(f"Could not count rows for table {table_name}: {e}")
        conn.close()
    except Exception as e:
        print(f"Error accessing {db_name}: {e}")

check_db('chat_history.db')
check_db('chat_history.backup_20260612_232314.db')
check_db('chat_history.before_location_fix_20260609_072849.db')
