import os
import json
from pyairtable import Api

# Load Config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(SCRIPT_DIR, 'config.json')

with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

api_key = config['airtable']['api_key']
base_id = config['airtable']['base_id']
table_name = config['airtable']['tables']['main_list']

print(f"Connecting to Base: {base_id}, Table: {table_name}")
api = Api(api_key)
table = api.table(base_id, table_name)

print("\n--- TEST 1: Fetching with Field Names (Standard) ---")
try:
    records_names = table.all(max_records=1)
    if records_names:
        rec = records_names[0]
        print(f"Record ID: {rec['id']}")
        print("Fields (Names):")
        for k, v in rec['fields'].items():
            print(f"  - {k}: {str(v)[:50]}...")
    else:
        print("No records found.")
except Exception as e:
    print(f"TEST 1 FAILED: {e}")

print("\n--- TEST 2: Fetching with Field IDs (return_fields_by_field_id=True) ---")
try:
    # Note: older pyairtable versions might not support this kwarg in .all()
    records_ids = table.all(max_records=1, return_fields_by_field_id=True)
    if records_ids:
        rec = records_ids[0]
        print(f"Record ID: {rec['id']}")
        print("Fields (IDs):")
        for k, v in rec['fields'].items():
            print(f"  - {k}: {str(v)[:50]}...")
            
        # Match Logic
        print("\n--- MAPPING DISCOVERY ---")
        if records_names:
            rec_name = records_names[0]
            # Create a value map to guess ID -> Name
            # This is heuristic because values might be duplicates, but for unique content it works.
            val_to_name = {}
            for name, val in rec_name['fields'].items():
                # Make hashable representation of value
                val_repr = json.dumps(val, sort_keys=True)
                val_to_name[val_repr] = name
            
            print("Deduced Mapping (ID -> Name):")
            for id_key, val in rec['fields'].items():
                val_repr = json.dumps(val, sort_keys=True)
                name = val_to_name.get(val_repr, "???")
                print(f"  {id_key} -> {name}")
                
    else:
        print("No records found (IDs).")
except Exception as e:
    print(f"TEST 2 FAILED: {e}")
    print("It seems 'return_fields_by_field_id' is NOT supported or failed.")
