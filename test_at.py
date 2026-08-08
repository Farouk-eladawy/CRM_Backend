import os
import json
from pyairtable import Api

# Load config
config_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\config.json"
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

at_config = config.get("airtable", {})
api_key = os.environ.get("AIRTABLE_API_KEY", at_config.get("api_key"))
base_id = at_config.get("base_id")
leads_base_id = at_config.get("leads_base_id")
religious_base_id = at_config.get("religious_base_id")
religious_leads_table = at_config.get("religious_leads_table")
leads_table = at_config.get("leads_table")
bookings_table = at_config.get("table_name")

api = Api(api_key)

def find_record(rec_id):
    # try all tables
    for b_id, t_name in [(base_id, bookings_table), (leads_base_id, leads_table), (religious_base_id, religious_leads_table)]:
        if not b_id or not t_name: continue
        table = api.table(b_id, t_name)
        try:
            rec = table.get(rec_id)
            if rec:
                print(f"Found in Base {b_id}, Table {t_name}")
                print(rec['fields'])
                return
        except Exception as e:
            pass

find_record("recnMhYp0emqZ27Rl")
find_record("recO2iX28afLM6toF")
