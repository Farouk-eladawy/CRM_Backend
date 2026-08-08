import sqlite3
import json

conn = sqlite3.connect("airtable_mirror.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT field_name, field_type FROM mirror_fields WHERE table_key IN (SELECT table_key FROM mirror_tables WHERE table_name='حجاج حج مباشر')")
fields = [dict(r) for r in c.fetchall()]
print(json.dumps(fields, ensure_ascii=False, indent=2))
