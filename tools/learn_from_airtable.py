import os
import json
import logging
import re
import sys
from pyairtable import Api
from datetime import datetime

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Determine Paths
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(TOOLS_DIR)
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')

# Add tools dir to sys.path to import learn_from_feedback
sys.path.append(TOOLS_DIR)
try:
    from learn_from_feedback import learn
except ImportError:
    logging.error("Could not import learn_from_feedback. Make sure it exists in the tools directory.")
    sys.exit(1)

def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        return None

def parse_chat_log_for_learning(chat_log):
    """
    Parses chat log to find pairs of (AI Draft) -> (Human Correction).
    Returns a list of tuples: (ai_draft, human_final, context)
    """
    if not chat_log:
        return []

    lines = chat_log.split('\n')
    lessons = []
    
    last_draft = None
    last_draft_context = "General"
    
    for line in lines:
        content = line.strip()
        
        # 1. Detect AI Draft
        if "[proposed_draft]" in content.lower():
            # Format usually: [timestamp] [OpenClaw Core - proposed_draft]: The text...
            parts = content.split(']:', 1)
            if len(parts) > 1:
                last_draft = parts[1].strip()
                # Try to infer context from previous lines or default
                last_draft_context = "Historical Log Extraction"
        
        # 2. Detect Human Reply (The Correction)
        elif any(tag in content.lower() for tag in [" - user]", " - support]", " - agent]"]):
            # If we have a pending draft, this is likely the correction (or approval)
            if last_draft:
                parts = content.split(']:', 1)
                if len(parts) > 1:
                    human_msg = parts[1].strip()
                    
                    # Only learn if there is a difference (handled by learn function, but we can filter here too)
                    # We pass it to learn() which handles the logic of "Approved" vs "Corrected"
                    lessons.append((last_draft, human_msg, last_draft_context))
                
                # Reset draft
                last_draft = None

        # 3. Detect AI Auto Reply (Reset draft if AI replied itself)
        elif "[ai_auto_reply]" in content.lower() or "[sent_by_ai]" in content.lower():
            last_draft = None

    return lessons

def main():
    logging.info("🚀 Starting Airtable Learning Process...")
    
    config = load_config()
    if not config:
        logging.error("Config not found. Exiting.")
        return

    api_key = config['airtable']['api_key']
    base_id = config['airtable']['base_id']
    table_name = config['airtable']['tables']['main_list']

    logging.info("Connecting to Airtable...")
    api = Api(api_key)
    table = api.table(base_id, table_name)

    # Fetch records with Chat Log
    logging.info("Fetching records with chat logs...")
    # We limit to 100 records for safety in this run, can be increased
    records = table.all(formula="NOT({AI Chat Log} = '')", max_records=100)
    
    logging.info(f"Found {len(records)} records. Analyzing...")

    total_lessons_found = 0
    
    for rec in records:
        chat_log = rec['fields'].get('AI Chat Log', '')
        if not chat_log: continue
        
        pairs = parse_chat_log_for_learning(chat_log)
        
        for ai_text, human_text, ctx in pairs:
            # We skip empty strings
            if not ai_text or not human_text:
                continue
                
            # Log progress
            # logging.info(f"Processing lesson from Record {rec['id']}")
            
            # Call the learning tool
            # Note: learn() prints to stdout, so we'll see the output
            learn(ai_text, human_text, ctx)
            total_lessons_found += 1

    logging.info(f"✅ Completed. Processed {total_lessons_found} potential lessons.")

if __name__ == "__main__":
    main()
