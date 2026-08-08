import os
import json
import logging
import sys
import requests
import urllib.parse
import csv
from pyairtable import Api

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Paths
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(TOOLS_DIR)
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
ECOSYSTEM_MAP_FILE = os.path.join(BASE_DIR, 'ecosystem_map.json')
AIRTABLE_FIELDS_CSV = os.path.join(BASE_DIR, 'Airtable Fields.csv')

# Import AI Helper
sys.path.append(BASE_DIR)
try:
    from ai_helper import query_deepseek
except ImportError:
    logging.error("Could not import ai_helper.")
    sys.exit(1)

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load {path}: {e}")
        return {}

def load_field_mapping(csv_path):
    """Loads field name to ID mapping from CSV file."""
    name_to_id = {}
    try:
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name_to_id[row['name']] = row['id']
    except Exception as e:
        logging.error(f"Failed to load CSV mapping: {e}")
    return name_to_id

def analyze_intent_and_plan(command, ecosystem_map):
    """
    Uses AI to understand if this is an UPDATE action or a SEARCH/ANALYTICS query.
    """
    simplified_map = {k: v.get('purpose') for k, v in ecosystem_map.items()}
    
    system_prompt = (
        "You are an intelligent Airtable Data Analyst & Automation Agent.\n"
        "Analyze the user's natural language command and decide the best course of action.\n"
        "I will provide the database schema.\n\n"
        "Determine the 'action_type':\n"
        "- 'update': If the user wants to change data, create invoice, modify record.\n"
        "- 'analytics': If the user asks 'how many', 'sum of', 'list all', 'find', 'search'.\n\n"
        "IF action_type = 'update':\n"
        "  Provide 'search_field', 'search_value', 'updates' (map of field:value), 'triggers'.\n"
        "IF action_type = 'analytics':\n"
        "  Provide 'operation' ('count', 'sum', 'list', 'average').\n"
        "  Provide 'target_field' (for sum/avg/list, e.g., 'Amount').\n"
        "  Provide 'airtable_formula' (A valid Airtable formula string to filter records). Use field names in {}.\n"
        "  Example Formula: \"AND({trip Name}='Luxor', {Date Trip} >= TODAY())\"\n\n"
        "Output JSON ONLY."
    )
    
    user_prompt = (
        f"Schema: {json.dumps(simplified_map, indent=2)}\n\n"
        f"Command: {command}"
    )
    
    response = query_deepseek(system_prompt, user_prompt)
    
    try:
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        return json.loads(response)
    except Exception as e:
        logging.error(f"AI Planning Failed: {e}")
        return None

def execute_analytics(table, plan):
    """Executes search, count, sum, or list operations."""
    formula = plan.get('airtable_formula')
    operation = plan.get('operation')
    target_field = plan.get('target_field')
    
    logging.info(f"🔍 Executing Analytics: {operation} where {formula}")
    
    try:
        # Fetch records matching formula
        records = table.all(formula=formula)
    except Exception as e:
        return f"❌ Error executing formula: {e}"
        
    count = len(records)
    
    if operation == 'count':
        return f"📊 Found {count} records matching your criteria."
        
    elif operation == 'sum':
        if not target_field: return "❌ Target field for sum not specified."
        total = sum(float(r['fields'].get(target_field, 0) or 0) for r in records)
        return f"💰 Total {target_field}: {total}"
        
    elif operation == 'list':
        if not records: return "Empty list."
        # List first 5 results summary
        summary = [f"- {r['fields'].get('Booking Nr.', 'N/A')}: {r['fields'].get('Customer Name', 'Unknown')}" for r in records[:5]]
        if count > 5: summary.append(f"... and {count - 5} more.")
        return "\n".join(summary)
        
    return f"✅ Operation {operation} completed. Records found: {count}"

def trigger_invoice_webhook(record_fields):
    """Simulates 'Generate Invoice' button."""
    base_url = "https://hook.us2.make.com/35vgcw6t3t8iv2f87p9jgfor34766nly"
    
    # Helper to safe get value
    def get_val(field_name):
        val = record_fields.get(field_name, '')
        if isinstance(val, list): return str(val[0]) if val else ""
        return str(val) if val is not None else ""

    def get_list_str(field_name):
        val = record_fields.get(field_name, [])
        if isinstance(val, list): return ", ".join(str(x) for x in val)
        return str(val) if val else ""

    params = {
        'booking_nr': get_val('Booking Nr.'),
        'customer_email': get_val('Customer Email'),
        'pickup_time': get_val('pickup time'),
        'customer_name': get_val('Customer Name'),
        'date_trip': get_val('Date Trip'),
        'hotel_name': get_val('Hotel Name'),
        'des': get_val('des'),
        'trip_name': get_val('trip Name'),
        'add_ons': get_list_str('Add-Ons ((MultiSelect))'),
        'customer_phone': get_val('Customer Phone'),
        'Option': get_val('Option'),
        'total_travelers': get_list_str('Total Travelers'),
        'non_billable_addons': get_list_str('Non-billable addons'),
        'record_id': record_fields.get('id', ''),
        'youth': get_val('Youth'),
        'chd_age': get_val('CHD Age'),
        'gyg_rating': get_val('GYG Rating'),
        'customer_review': get_val('Customer Review'),
        'net_rate': get_val('Net Rate'),
        'Amount': get_val('Amount'),
        'booking_status': get_val('Booking Status'),
        'google_maps': get_val('Google Maps'),
        'currency': get_list_str('Currency'),
        'traveler_name': get_val('Traveler name'),
        'Add_Ons Multiselect': get_list_str('Add-Ons ((MultiSelect))')
    }
    
    if not params['booking_nr'] or not params['customer_email']:
        logging.error("❌ Missing Booking Nr or Email.")
        return False
        
    logging.info(f"🔗 Triggering Invoice Webhook for {params['booking_nr']}")
    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            logging.info("✅ Invoice Generation Triggered Successfully!")
            return True
        else:
            logging.error(f"❌ Webhook Failed: {response.text}")
            return False
    except Exception as e:
        logging.error(f"❌ Webhook Error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python execute_airtable_action.py \"Your command here\"")
        return

    command = sys.argv[1]
    logging.info(f"🤖 Processing Command: {command}")
    
    # Load Config & Map
    config = load_json(CONFIG_FILE)
    ecosystem_map = load_json(ECOSYSTEM_MAP_FILE)
    field_name_to_id = load_field_mapping(AIRTABLE_FIELDS_CSV)
    
    if not config or not ecosystem_map:
        return

    api_key = config['airtable']['api_key']
    base_id = config['airtable']['base_id']
    table_name = config['airtable']['tables']['main_list']
    
    api = Api(api_key)
    table = api.table(base_id, table_name)
    
    # 1. Analyze Intent
    plan = analyze_intent_and_plan(command, ecosystem_map)
    
    if not plan:
        print("Could not understand command.")
        return
        
    logging.info(f"📋 Plan: {json.dumps(plan, indent=2)}")
    
    action_type = plan.get('action_type', 'update')
    
    # --- BRANCH 1: ANALYTICS ---
    if action_type == 'analytics':
        result = execute_analytics(table, plan)
        print(result) # Print to stdout for OpenClaw to capture
        return

    # --- BRANCH 2: UPDATE (Legacy Logic) ---
    search_field = plan.get('search_field')
    search_value = plan.get('search_value')
    
    if not search_field or not search_value:
        print("No search criteria found for update.")
        return
        
    logging.info(f"🔍 Searching for record where '{search_field}' = '{search_value}'...")
    formula = "{" + search_field + "} = '" + search_value + "'"
    records = table.all(formula=formula)
    
    if not records:
        print("❌ No record found matching criteria.")
        return
        
    record = records[0]
    record_id = record['id']
    record_fields = record['fields']
    record_fields['id'] = record_id
    
    # Execute Updates
    updates = plan.get('updates', {})
    clean_updates = {}
    triggers = plan.get('triggers', [])
    
    for k, v in updates.items():
        if k == 'Generate Invoice':
            triggers.append(k)
        else:
            if k == 'Currency' and isinstance(v, str): v = [v]
            
            if k in field_name_to_id:
                clean_updates[field_name_to_id[k]] = v
            else:
                logging.warning(f"⚠️ Field '{k}' ignored (not in CSV map).")
            
    if clean_updates:
        try:
            table.update(record_id, clean_updates)
            print("✅ Update Successful!")
            # Update local state for webhook
            id_to_name = {v: k for k, v in field_name_to_id.items()}
            for fid, val in clean_updates.items():
                fname = id_to_name.get(fid)
                if fname: record_fields[fname] = val
        except Exception as e:
            print(f"Update Failed: {e}")
    
    # Handle Triggers
    for trigger in triggers:
        if trigger == 'Generate Invoice':
            if trigger_invoice_webhook(record_fields):
                print("✅ Invoice Triggered.")
            else:
                print("❌ Invoice Trigger Failed.")

if __name__ == "__main__":
    main()
