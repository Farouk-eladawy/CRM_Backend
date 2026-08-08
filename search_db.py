import sqlite3
import pandas as pd

conn = sqlite3.connect('chat_history.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]

for t in tables:
    try:
        df = pd.read_sql_query(f'SELECT * FROM {t}', conn)
        mask = df.astype(str).apply(lambda x: x.str.contains("37186129904335849", na=False)).any(axis=1)
        if mask.any():
            print(f'--- Found in {t} ---')
            for record in df[mask].to_dict('records'):
                print(record)
    except Exception as e:
        pass
