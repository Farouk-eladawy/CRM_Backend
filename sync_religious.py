import json
import sqlite3
import logging
from airtable_mirror import AirtableMirror

logging.basicConfig(level=logging.INFO)

config = json.load(open('config.json', encoding='utf-8'))
m = AirtableMirror(config)

tables = m._list_table_info()
for info in tables:
    if info['base_id'] == 'appzc9rxT8kfD0HMp' and not info['ignored']:
        print(f"Syncing {info['table_name']} ({info['table_key']})...")
        m.sync_table(info)
        print(f"Done syncing {info['table_name']}.")

print("Finished syncing religious base.")
