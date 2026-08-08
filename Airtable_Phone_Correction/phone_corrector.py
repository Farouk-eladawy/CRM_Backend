import os
import re
import logging
import requests
import json
import phonenumbers
from dotenv import load_dotenv
from pyairtable import Api

# Configure Logging
# Use UTF-8 for file handler to avoid Windows encoding issues
file_handler = logging.FileHandler("phone_correction.log", encoding='utf-8')
console_handler = logging.StreamHandler()
# Set console to handle unicode if possible, or ignore errors
import sys
if sys.platform == 'win32':
    # Windows console might struggle with some unicode chars
    console_handler.stream = sys.stdout

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        file_handler,
        console_handler
    ]
)

# Load Environment Variables
# Assuming .env is in the Bukon_Server folder or root. 
# We'll try to load from Bukon_Server as we saw it there.
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Bukon_Server', '.env')
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')

load_dotenv(env_path)

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE = os.getenv("AIRTABLE_TABLE", "List")
DEEP_SEEK_API_KEY = os.getenv("DEEP_SEEK_API_KEY") # Or OpenAI key if available
DEEP_SEEK_API_URL = os.getenv("DEEP_SEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")

class PhoneCorrector:
    def __init__(self):
        if not AIRTABLE_TOKEN or not AIRTABLE_BASE_ID:
            raise ValueError("Missing Airtable Credentials in .env")
        
        self.api = Api(AIRTABLE_TOKEN)
        self.table = self.api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE)
        
        # Mapping of Field IDs (From airtable_fields.py reference)
        # Using Field Name 'Customer Phone' directly as PyAirtable handles names well usually,
        # but robust code uses IDs if names change. 
        # Based on previous context: FieldIds.CUSTOMER_PHONE = "flduE2TbOmhEv7ebR"
        self.PHONE_FIELD_ID = "flduE2TbOmhEv7ebR" 
        self.PHONE_FIELD_NAME = "Customer Phone"

    def normalize_phone_basic(self, phone_str):
        """
        Basic normalization using phonenumbers library.
        Returns (formatted_number, is_valid)
        """
        try:
            # 1. Remove obvious junk but keep +
            clean_str = str(phone_str).strip()
            
            # If it starts with 00, replace with +
            if clean_str.startswith("00"):
                clean_str = "+" + clean_str[2:]
            
            # Parse
            # Default to generic or try to guess country if missing?
            # We assume international format mostly, or Egypt/UK based on context.
            # If no +, assume it might be local?
            
            # Heuristic: If starts with 010, 011, 012, 015 -> Egypt (+20)
            if re.match(r'^01[0125]\d{8}$', clean_str.replace(' ', '')):
                clean_str = "+20" + clean_str.replace(' ', '')[1:]
            
            parsed = phonenumbers.parse(clean_str, None)
            
            if phonenumbers.is_valid_number(parsed):
                # Return E.164 format (e.g. +201012345678)
                # Or International format with spaces? 
                # User asked to "Remove spaces", so E.164 is best for searching.
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164), True
            else:
                return clean_str, False
        except Exception as e:
            return clean_str, False

    def extract_phone_with_ai(self, text):
        """
        Use AI to extract and format phone number from messy text.
        """
        if not DEEP_SEEK_API_KEY:
            logging.warning("No AI API Key found. Skipping AI extraction.")
            return None

        prompt = f"""
        You are a data cleaning assistant.
        Task: Extract the phone number from the text below and format it as a pure E.164 number (e.g. +2010xxxx).
        - Remove all spaces, dashes, brackets.
        - If multiple numbers, pick the most likely mobile number.
        - If country code is missing:
          - If starts with 010/011/012/015, assume Egypt (+20).
          - If starts with 07, assume UK (+44) or similar based on length.
          - Otherwise return digits only.
        - Output ONLY the cleaned number. If no valid number found, output "NULL".

        Text: "{text}"
        """
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEP_SEEK_API_KEY}"
            }
            payload = {
                "model": "deepseek-chat", # or gpt-3.5-turbo if using openai
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0
            }
            
            response = requests.post(DEEP_SEEK_API_URL, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()['choices'][0]['message']['content'].strip()
                if "NULL" in result:
                    return None
                # Clean up any potential markdown or quotes
                result = result.replace('`', '').replace('"', '').replace("'", "").strip()
                return result
            else:
                logging.error(f"AI Error: {response.text}")
                return None
        except Exception as e:
            logging.error(f"AI Request Failed: {e}")
            return None

    def run(self):
        logging.info("Starting Phone Correction Process...")
        
        # 1. Fetch records from specific View "Phone_Correction"
        # This view should filter records that need correction (e.g. non-empty phone)
        # We can remove the formula since the View handles the logic, or keep it as safety.
        # User requested specific view usage.
        
        view_name = "Phone_Correction"
        logging.info(f"Fetching records from View: {view_name}")
        
        try:
            records = self.table.all(view=view_name)
        except Exception as e:
            logging.warning(f"Could not find view '{view_name}'. Falling back to standard formula.")
            records = self.table.all(formula="NOT({Customer Phone}='')")

        logging.info(f"Found {len(records)} records in view/formula.")
        
        updates = []
        
        for rec in records:
            original_phone = rec['fields'].get(self.PHONE_FIELD_NAME) or rec['fields'].get(self.PHONE_FIELD_ID)
            if not original_phone:
                continue
                
            # Step 1: Basic Normalization
            normalized, is_valid = self.normalize_phone_basic(original_phone)
            
            final_phone = normalized
            
            # Step 2: AI Fallback if invalid or complex text
            # Heuristic: If original has letters or is very long, use AI
            has_letters = bool(re.search('[a-zA-Z]', str(original_phone)))
            if not is_valid and (has_letters or len(str(original_phone)) > 20):
                logging.info(f"Using AI for complex phone: {original_phone}")
                ai_extracted = self.extract_phone_with_ai(original_phone)
                if ai_extracted:
                    final_phone = ai_extracted
            
            # Step 3: Compare and Update
            # We want to remove spaces/dashes as per user request
            final_clean = str(final_phone).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            
            # Check if update is needed
            # (Compare cleaned version of original to final)
            original_clean = str(original_phone).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            
            if final_clean != original_clean:
                # One last check: Ensure we didn't destroy the number (length check)
                if len(final_clean) >= 8:
                    logging.info(f"Correction: '{original_phone}' -> '{final_clean}'")
                    updates.append({
                        "id": rec['id'],
                        "fields": {
                            self.PHONE_FIELD_ID: final_clean
                        }
                    })
                else:
                    logging.warning(f"Skipping correction '{original_phone}' -> '{final_clean}' (Too short)")
            
            # Batch update every 10 records
            if len(updates) >= 10:
                self.batch_update(updates)
                updates = []
        
        # Final batch
        if updates:
            self.batch_update(updates)
            
        logging.info("Phone Correction Process Complete.")

    def batch_update(self, updates):
        try:
            self.table.batch_update(updates)
            logging.info(f"Updated {len(updates)} records.")
        except Exception as e:
            logging.error(f"Failed to batch update: {e}")

if __name__ == "__main__":
    corrector = PhoneCorrector()
    corrector.run()
