import os
import json
import time
import logging
import sys
from datetime import datetime
import pytz
from pyairtable import Api

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [OpenClaw Observer] - %(message)s',
    handlers=[
        logging.FileHandler("observer.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
ECOSYSTEM_MAP_FILE = os.path.join(BASE_DIR, 'ecosystem_map.json')
CACHE_FILE = os.path.join(BASE_DIR, 'observer_cache.json')

# Import AI Helper
sys.path.append(BASE_DIR)
try:
    from ai_helper import query_deepseek
except ImportError:
    logging.error("Could not import ai_helper.")
    sys.exit(1)

def load_json(path):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Error loading {path}: {e}")
    return {}

def save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error saving {path}: {e}")

def get_actor_type(last_modified_by):
    """
    Determines if the change was made by a Human or Automation.
    """
    if not last_modified_by:
        return "Unknown"
        
    # Check if it's a dict (Airtable user object)
    if isinstance(last_modified_by, dict):
        name = last_modified_by.get('name', '')
        email = last_modified_by.get('email', '')
    else:
        # Fallback if string (unlikely in API but possible)
        name = str(last_modified_by)
        email = ""

    # Define known bots/automation users
    automation_keywords = ['automation', 'make', 'zapier', 'api', 'bot', 'system']
    
    if any(k in name.lower() for k in automation_keywords) or any(k in email.lower() for k in automation_keywords):
        return "Automation System"
        
    return f"Human Employee ({name})"

def analyze_change_context(record_id, field, old_val, new_val, record_data, ecosystem_info):
    """
    Uses AI to understand the 'Story' behind a change with strict logic.
    """
    # 1. Determine Actor
    last_modified_by = record_data.get('Last Modified By')
    actor_type = get_actor_type(last_modified_by)

    # 2. Determine Trip Context
    trip_date_str = record_data.get('Date Trip')
    time_context = "Unknown"
    if trip_date_str:
        try:
            trip_dt = datetime.fromisoformat(trip_date_str.replace('Z', '+00:00'))
            now = datetime.now(trip_dt.tzinfo)
            delta = trip_dt - now
            if delta.total_seconds() < 0: time_context = "Post-Trip"
            elif delta.total_seconds() < 86400: time_context = "Urgent (Pre-Trip < 24h)"
            else: time_context = "Planning Phase"
        except: pass

    # 3. Field Context
    field_purpose = ecosystem_info.get('purpose', 'Unknown')
    
    # 4. Strict AI Analysis
    system_prompt = (
        "You are a strict Audit Log Analyzer for a travel agency.\n"
        "Your job is to categorize data changes accurately based on the 'Actor' and 'Context'.\n"
        "Rules:\n"
        "- If Actor is 'Automation System': It is likely a 'System Sync' or 'Auto-Correction'.\n"
        "- If Actor is 'Human Employee': It is a 'Manual Intervention'. Analyze intent (Correction, Update, or Error?).\n"
        "- If Field is 'Price' or 'Amount': Flag as 'Financial Update'.\n"
        "- If Field is 'Status': Flag as 'Workflow Progression'.\n"
        "Output Format: [Category] - Brief Explanation."
    )
    
    user_prompt = (
        f"Change in Record {record_id}:\n"
        f"- Actor: {actor_type}\n"
        f"- Field: {field}\n"
        f"- Old Value: {old_val}\n"
        f"- New Value: {new_val}\n"
        f"- Field Purpose: {field_purpose}\n"
        f"- Timing: {time_context}\n\n"
        "Analyze this change."
    )
    
    return query_deepseek(system_prompt, user_prompt)

def main():
    logging.info("🦅 OpenClaw Observer 2.0 Started (Active Audit Mode)...")
    
    config = load_json(CONFIG_FILE)
    if not config: return

    api_key = config['airtable']['api_key']
    base_id = config['airtable']['base_id']
    table_name = config['airtable']['tables']['main_list']
    
    api = Api(api_key)
    table = api.table(base_id, table_name)
    ecosystem_map = load_json(ECOSYSTEM_MAP_FILE)
    cache = load_json(CACHE_FILE)
    
    while True:
        try:
            logging.info("Scanning for changes...")
            records = table.all(sort=["-Last Modified"], max_records=50)
            changes_detected = 0
            
            for rec in records:
                rid = rec['id']
                fields = rec['fields']
                
                if rid in cache:
                    cached_rec = cache[rid]
                    cached_fields = cached_rec.get('fields', {})
                    
                    for key, new_val in fields.items():
                        if key in ['Last Modified', 'Last Modified By', 'Last Processed']: continue
                        
                        old_val = cached_fields.get(key)
                        if str(old_val) != str(new_val):
                            changes_detected += 1
                            ecosystem_info = ecosystem_map.get(key, {})
                            
                            logging.info(f"🔄 Change in {rid} [{key}]")
                            
                            # Analyze
                            insight = analyze_change_context(rid, key, old_val, new_val, fields, ecosystem_info)
                            logging.info(f"🧠 Audit Result: {insight}")
                            
                cache[rid] = {'last_checked': datetime.now().isoformat(), 'fields': fields}
            
            if changes_detected > 0:
                save_json(CACHE_FILE, cache)
                logging.info(f"Saved {changes_detected} updates.")
            else:
                logging.info("No changes.")
            
            time.sleep(60)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.error(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
