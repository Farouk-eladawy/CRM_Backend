import os
import json
import logging
import sys
from pyairtable import Api
from collections import defaultdict

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Paths
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(TOOLS_DIR)
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')

# Import AI Helper
sys.path.append(BASE_DIR)
try:
    from ai_helper import query_deepseek
except ImportError:
    logging.error("Could not import ai_helper. Make sure it exists in the parent directory.")
    sys.exit(1)

def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        return None

def analyze_fields_with_ai(fields_sample):
    """
    Uses AI to infer the purpose and ownership of each field based on its name and sample values.
    """
    system_prompt = (
        "You are a System Architect for a travel agency automation system. "
        "I will provide a list of Airtable fields with sample values. "
        "Your task is to analyze each field and output a JSON object describing its 'Semantic Purpose' and 'Likely Owner'.\n\n"
        "Categories for 'purpose': ['Finance', 'Logistics', 'Customer_Info', 'Status', 'System_Meta', 'Communication', 'Booking_Details'].\n"
        "Categories for 'owner': ['Human_Agent', 'Automation_System', 'Mixed'].\n\n"
        "Output Format:\n"
        "{\n"
        "  'Field Name': {'purpose': '...', 'owner': '...', 'description': '...'},\n"
        "  ...\n"
        "}"
    )
    
    # Prepare data for prompt
    prompt_data = ""
    for field, samples in fields_sample.items():
        # Take up to 3 unique non-empty samples
        unique_samples = list(set([str(s) for s in samples if s]))[:3]
        prompt_data += f"- Field: '{field}' | Samples: {unique_samples}\n"
        
    user_prompt = f"Analyze these fields:\n{prompt_data}"
    
    logging.info("🧠 Asking AI to analyze ecosystem structure...")
    response = query_deepseek(system_prompt, user_prompt)
    
    if response:
        try:
            # Clean code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
                
            return json.loads(response)
        except Exception as e:
            logging.error(f"Failed to parse AI response: {e}")
            logging.error(f"Raw Response: {response}")
            return {}
    return {}

def main():
    logging.info("🚀 Starting Ecosystem Analysis...")
    
    config = load_config()
    if not config:
        return

    api_key = config['airtable']['api_key']
    base_id = config['airtable']['base_id']
    table_name = config['airtable']['tables']['main_list']

    api = Api(api_key)
    table = api.table(base_id, table_name)
    
    # 1. Fetch Data Sample
    logging.info("Fetching data sample from Airtable...")
    records = table.all(max_records=50)
    
    fields_sample = defaultdict(list)
    all_fields = set()
    
    for rec in records:
        for f, v in rec['fields'].items():
            all_fields.add(f)
            fields_sample[f].append(v)
            
    # 2. Analyze with AI in Batches
    ecosystem_map = {}
    
    # Split fields into chunks of 10
    field_names = list(fields_sample.keys())
    batch_size = 10
    
    for i in range(0, len(field_names), batch_size):
        batch_keys = field_names[i:i+batch_size]
        batch_sample = {k: fields_sample[k] for k in batch_keys}
        
        logging.info(f"🧠 Asking AI to analyze batch {i//batch_size + 1} ({len(batch_keys)} fields)...")
        batch_result = analyze_fields_with_ai(batch_sample)
        ecosystem_map.update(batch_result)

    # 3. Add default metadata for fields AI missed
    for f in all_fields:
        if f not in ecosystem_map:
            ecosystem_map[f] = {"purpose": "Unknown", "owner": "Mixed", "description": "Auto-detected field"}

    # 4. Save Map
    output_path = os.path.join(BASE_DIR, 'ecosystem_map.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ecosystem_map, f, indent=2, ensure_ascii=False)
        
    logging.info(f"✅ Ecosystem Map generated at: {output_path}")
    logging.info("Sample of understanding:")
    sample_keys = list(ecosystem_map.keys())[:3]
    for k in sample_keys:
        logging.info(f" - {k}: {ecosystem_map[k]}")

if __name__ == "__main__":
    main()
