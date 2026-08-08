import os
import json
import time
import logging
import schedule
import requests
import pytz
import re
import threading
import pandas as pd
import difflib
from flask import Flask, request, jsonify
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from cachetools import TTLCache
from pyairtable import Api
from pyairtable.formulas import match

# Import Field Mappings
from airtable_fields import FieldIds, LeadFieldIds, ID_TO_READABLE_NAME, FINANCIAL_FIELDS, JSON_KEY_TO_ID, LEADS_TABLE_NAME, HOTEL_TRANSFER_TABLE_NAME

# Define Fixed Cairo Offset (UTC+2) - Winter Time Adjustment
CAIRO_OFFSET = timedelta(hours=2)

class KeyedMutex:
    """
    Mutex that locks based on a key (record_id).
    Allows different records to be processed in parallel,
    but serializes access to the same record.
    """
    def __init__(self):
        self._locks = {}
        self._global_lock = threading.Lock()

    @contextmanager
    def lock(self, key):
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            lock = self._locks[key]
        
        with lock:
            yield

# Create Reverse Mapping for Lookup
NAME_TO_ID = {v: k for k, v in ID_TO_READABLE_NAME.items()}

import audit_utils
import email_templates
from gmail_service import GmailService
import web_search_tool
from knowledge_base import KnowledgeBase
from gyg_manager import GYGManager
import cloudinary
import cloudinary.uploader

# Setup Logging
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, 'agent_log.txt')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class AIAgent:
    def __init__(self):
        self.load_config()
        # Initialize Timezone (Cairo)
        try:
            self.cairo_tz = pytz.timezone('Africa/Cairo')
        except Exception:
            logging.warning("pytz timezone failed, falling back to fixed offset")
            self.cairo_tz = None
            
        self.setup_connections()
        
        # Load Headout Catalog (JSON)
        self.script_dir = SCRIPT_DIR # Store for method access
        self.headout_catalog_context = self.load_headout_json()
        
        # Load GYG Data (JSON)
        self.gyg_data_context = self.load_gyg_data()
        
        # Load Viator Data (JSON)
        self.viator_data_context = self.load_viator_data()
        
        # Initialize GYG Manager (If still needed for API/Web search fallback)
        self.gyg_manager = GYGManager()
        
        self.gmail_service = GmailService() # Initialize Gmail OAuth Service
        
        # Initialize Thread Lock for Safety (Keyed by Record ID)
        self.mutex = KeyedMutex()
        
        # Initialize Session Cache (1 Hour TTL, Max 1000 Users)
        self.session_cache = TTLCache(maxsize=1000, ttl=3600)
        
        # Initialize Cloudinary
        self.setup_cloudinary()
        
        # Initialize Audit DB
        audit_utils.init_db()
        
        # Load Knowledge Base
        self.kb = KnowledgeBase()
        
    def setup_cloudinary(self):
        """Configure Cloudinary with provided credentials."""
        try:
            cloudinary.config(
                cloud_name = "dqlurfwet",
                api_key = "676981699546932",
                api_secret = "gcy0eSAwFh6KDHpNa3NAa5bFvwI"
            )
            logging.info("Cloudinary configured successfully.")
        except Exception as e:
            logging.error(f"Failed to configure Cloudinary: {e}")

    def load_headout_catalog(self):
        """Load and format Headout trips from local Excel file."""
        try:
            file_path = os.path.join(self.script_dir, 'Headout trips.xlsx')
            if not os.path.exists(file_path):
                logging.warning(f"Headout Excel file not found at {file_path}")
                return ""
            
            logging.info(f"Loading Headout Catalog from {file_path}...")
            df = pd.read_excel(file_path)
            
            # Fill forward Product Name for merged cells
            if 'Product Name ' in df.columns:
                 df['Product Name '] = df['Product Name '].ffill()
            
            # Select relevant columns to save tokens
            cols_to_keep = ['Product Name ', 'Option Name ', 'Duration', 'Departure', 'Cancellation', 'Net Adult ', 'Net Child ', 'FTS Answer']
            
            text_context = "HEADOUT TRIPS CATALOG:\n"
            
            # Iterate and format
            current_product = ""
            for _, row in df.iterrows():
                prod = str(row.get('Product Name ', '')).strip()
                if prod != current_product:
                    text_context += f"\n--- TRIP: {prod} ---\n"
                    current_product = prod
                
                opt = str(row.get('Option Name ', '')).strip()
                dur = str(row.get('Duration', '')).strip()
                dep = str(row.get('Departure', '')).strip()
                cancel = str(row.get('Cancellation', '')).strip()
                adult = str(row.get('Net Adult ', ''))
                child = str(row.get('Net Child ', ''))
                fts_ans = str(row.get('FTS Answer', ''))
                
                text_context += f"- Option: {opt} | Duration: {dur} | Departs: {dep} | Cancel: {cancel} | Price: Adult ${adult}, Child ${child}\n"
                if fts_ans and fts_ans != "nan":
                    text_context += f"  * Note: {fts_ans}\n"
                
            logging.info(f"Headout Catalog loaded ({len(df)} rows).")
            return text_context
            
        except Exception as e:
            logging.error(f"Failed to load Headout Excel: {e}")
            return ""

    def load_headout_json(self):
        """Load Headout trips from local JSON file."""
        try:
            file_path = os.path.join(self.script_dir, 'Headout_data.json')
            if not os.path.exists(file_path):
                logging.warning(f"Headout JSON file not found at {file_path}")
                return ""
            
            logging.info(f"Loading Headout JSON from {file_path}...")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            tours = data.get('tours', [])
            text_context = "HEADOUT TRIPS CATALOG (JSON SOURCE):\n"
            
            for tour in tours:
                title = tour.get('title', 'Unknown Title')
                tour_id = tour.get('id', 'N/A')
                highlights = ", ".join(tour.get('highlights', []))
                inclusions = ", ".join(tour.get('inclusions', []))
                exclusions = ", ".join(tour.get('exclusions', []))
                duration = tour.get('duration', 'N/A')
                price = tour.get('price_from', 'N/A')
                features = tour.get('features', {})
                skip_line = "Yes" if features.get('skip_the_line') else "No"
                
                text_context += f"\n--- TRIP: {title} (ID: {tour_id}) ---\n"
                text_context += f"- Duration: {duration} | Price Guide: Approx {price} | Skip-the-Line: {skip_line}\n"
                text_context += f"- Highlights: {highlights}\n"
                text_context += f"- Inclusions: {inclusions}\n"
                text_context += f"- Exclusions: {exclusions}\n"
                
                # Operating Hours
                op_hours = tour.get('operating_hours', {})
                if op_hours:
                    daily = op_hours.get('daily', '')
                    text_context += f"- Operating Hours: {daily}\n"

            logging.info(f"Headout JSON loaded ({len(tours)} tours).")
            return text_context
            
        except Exception as e:
            logging.error(f"Failed to load Headout JSON: {e}")
            return ""

    def load_viator_data(self):
        """Load Viator scraped data from local JSON file."""
        try:
            file_path = os.path.join(self.script_dir, 'Viator_data.json')
            if not os.path.exists(file_path):
                logging.warning(f"Viator Data file not found at {file_path}")
                return None
            
            logging.info(f"Loading Viator Data from {file_path}...")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Index or prepare data if needed
            self.viator_data_context = data
            
            logging.info(f"Viator Data loaded ({len(data)} trips).")
            return data
            
        except Exception as e:
            logging.error(f"Failed to load Viator Data: {e}")
            return None

    def load_gyg_data(self):
        """Load GetYourGuide scraped data from local JSON file."""
        try:
            file_path = os.path.join(self.script_dir, 'Get_Your_Guide_data.json')
            if not os.path.exists(file_path):
                logging.warning(f"GYG Data file not found at {file_path}")
                return ""
            
            logging.info(f"Loading GYG Data from {file_path}...")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Index by Product ID for fast lookup
            self.gyg_data_map = {}
            for trip in data:
                pid = trip.get('product_id')
                if pid:
                    self.gyg_data_map[str(pid)] = trip
            
            logging.info(f"GYG Data loaded ({len(data)} trips). Indexed {len(self.gyg_data_map)} products.")
            return data
            
        except Exception as e:
            logging.error(f"Failed to load GYG Data: {e}")
            return []

    def get_mpc_trip_name(self, product_id):
        """
        Lookup the 'Real' or 'Corrected' trip name from MPC table using Product ID.
        """
        if not self.mpc_table or not product_id:
            return None
            
        try:
            # Search MPC table where {ID} = product_id
            formula = match({"ID": product_id})
            records = self.mpc_table.all(formula=formula, max_records=1)
            
            if not records:
                return None
                
            fields = records[0].get('fields', {})
            
            # User Request: Check 'Main Product Name' field first for the real name, then 'Trip name correction'
            # Note: The CSV provided shows 'Main Product Name' and 'Trip name correction' as columns.
            # The 'ID' column corresponds to 'Product ID'.
            
            main_name = fields.get('Main Product Name') 
            correction_name = fields.get('Trip name correction')
            
            # Priority: Main Name > Correction Name (As per user request)
            # However, if 'Main Product Name' is missing (which seems to be the case for 'Luxor by Bus Hurghada'),
            # we are falling back to correction.
            
            # To fix the user issue: If 'Main Product Name' is missing, it means the Airtable record itself is missing data.
            # We will use correction_name if main_name is None.
            final_name = main_name if main_name else correction_name
            
            logging.info(f"MPC Lookup for {product_id}: Main='{main_name}', Correction='{correction_name}' -> Final='{final_name}'")
            return final_name
            
        except Exception as e:
            logging.warning(f"Error looking up MPC for {product_id}: {e}")
            return None

    def _format_gyg_trip_for_context(self, trip, score=None):
        """Format a single GYG trip for context injection."""
        # Fix Bad Title from Scraper
        display_title = trip.get('title')
        if not display_title or "Supply Partner" in display_title:
            # Try to get title from Options or Full Text
            opts = trip.get('options', [])
            if opts:
                display_title = opts[0].get('title')
            else:
                display_title = f"Trip ID {trip.get('product_id')}"
        
        context = ""
        if score is not None:
             context += f"- **Title:** {display_title} (Match Score: {score})\n"
        else:
             context += f"- **Title:** {display_title}\n"
             
        context += f"  **Rating:** {trip.get('rating')} | **ID:** {trip.get('product_id')}\n"
        context += f"  **Highlights:** {', '.join(trip.get('highlights', [])[:5])}\n"
        context += f"  **Inclusions:** {', '.join(trip.get('inclusions', []))}\n"
        context += f"  **Exclusions:** {', '.join(trip.get('exclusions', []))}\n"
        context += f"  **Meeting Point/Pickup:** {trip.get('transportation') or 'See details'}\n"
        context += f"  **Cancellation:** {trip.get('refund_policy')}\n"
        
        # Use Full Description if available, otherwise Short Description
        desc_to_use = trip.get('full_description') or trip.get('short_description') or ""
        if len(desc_to_use) > 3000:
            desc_to_use = desc_to_use[:3000] + "..."
        context += f"  **Description:** {desc_to_use}\n"
        context += "---\n"
        return context

    def search_viator_local_db(self, query):
        """
        Search the local Viator JSON database.
        """
        if not hasattr(self, 'viator_data_context') or not self.viator_data_context:
            return ""

        try:
            # Simple keyword match for now
            matches = []
            q_lower = query.lower()
            
            for trip in self.viator_data_context:
                title = trip['tour_info']['title'].lower()
                code = trip['tour_info']['product_code'].lower()
                
                score = 0
                if code in q_lower: score += 100
                if title in q_lower: score += 50
                
                if score > 0:
                    matches.append((score, trip))
            
            matches.sort(key=lambda x: x[0], reverse=True)
            
            if not matches:
                return ""
                
            # Format top 3
            result_text = "SOURCE 3.3: VIATOR TRIPS CATALOG (Top Matches):\n"
            for score, trip in matches[:3]:
                info = trip['tour_info']
                result_text += f"- **Title:** {info['title']} (Code: {info['product_code']})\n"
                result_text += f"  **Description:** {trip['overview']['description'][:200]}...\n"
                result_text += f"  **Inclusions:** {', '.join(trip['whats_included'][:5])}\n"
                result_text += "---\n"
                
            return result_text
            
        except Exception as e:
            logging.error(f"Viator Search Error: {e}")
            return ""

    def search_gyg_local_db(self, query):
        """
        Search the local GYG JSON database using Token-Based Scoring.
        Matches against Title, Keywords, and Description.
        """
        if not hasattr(self, 'gyg_data_context') or not self.gyg_data_context:
            return ""
            
        try:
            # 1. Preprocess Query
            stop_words = {
                "more", "info", "about", "this", "trip", "please", "can", "i", "book", "want", 
                "details", "price", "cost", "how", "much", "need", "new", "for", "to", "from", "by"
            }
            
            # Clean and tokenize
            clean_query = re.sub(r'[^\w\s]', '', query.lower())
            tokens = [w for w in clean_query.split() if w not in stop_words and len(w) > 2]
            
            if not tokens:
                # Fallback to simple containment if no tokens remain
                tokens = clean_query.split()
            
            logging.info(f"Searching GYG DB with tokens: {tokens}")
            
            matches = []
            
            for trip in self.gyg_data_context:
                score = 0
                title = (trip.get('title') or '').lower()
                # Use short description for speed, full text is too heavy
                desc = (trip.get('short_description') or '').lower()
                keywords = [k.lower() for k in (trip.get('keywords') or [])]
                highlights = [h.lower() for h in (trip.get('highlights') or [])]
                
                # Include Options Titles in Search
                options = trip.get('options', [])
                options_text = " ".join([opt.get('title', '').lower() for opt in options])
                
                # Combined Text for Keyword Search
                trip_text = f"{title} {options_text} {' '.join(keywords)} {' '.join(highlights)}"
                
                matched_tokens = 0
                for token in tokens:
                    # Title Match (High Weight)
                    if token in title:
                        score += 30
                    
                    # Option Title Match (Medium Weight)
                    if token in options_text:
                        score += 20
                    
                    # General Match
                    if token in trip_text:
                        score += 10
                        matched_tokens += 1
                    elif token in desc:
                        score += 5
                
                # Bonus for matching ALL tokens
                if matched_tokens == len(tokens) and len(tokens) > 0:
                    score += 50
                    
                if score > 0:
                    matches.append((score, trip))
            
            # Sort by score
            matches.sort(key=lambda x: x[0], reverse=True)
            
            if not matches:
                return ""
            
            # Format top 3 matches
            context = "**GET YOUR GUIDE TRIPS (LOCAL DB - BEST MATCHES):**\n"
            for score, trip in matches[:3]:
                context += self._format_gyg_trip_for_context(trip, score)
                
            return context

        except Exception as e:
            logging.error(f"Error searching GYG Local DB: {e}")
            return ""

    def shadow_notify_openclaw(self, user_id, user_message, ai_reply):
        """Send interaction to OpenClaw Core for learning (Shadow Mode)."""
        try:
            url = "http://localhost:18789/agent/message"
            payload = {
                "user": str(user_id),
                "message": user_message,
                "shadow_mode": True,
                "teacher_reply": ai_reply
            }
            # Fire and forget (don't wait long)
            requests.post(url, json=payload, timeout=1)
        except Exception:
            pass  # Ignore errors in shadow mode

    def load_config(self):
        try:
            config_path = os.path.join(SCRIPT_DIR, 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            logging.info("Configuration loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load config from {config_path}: {e}")
            raise

    def setup_connections(self):
        try:
            self.airtable_api = Api(self.config['airtable']['api_key'])
            self.base_id = self.config['airtable']['base_id']
            # ENABLE FIELD IDs for Robustness
            # pyairtable uses 'return_fields_by_field_id' ONLY in methods like all(), not in table constructor.
            # But wait, pyairtable 2.x+ supports this in Api.table? No, it's usually per-request.
            # Let's check docs logic: 
            # Actually, to use field IDs in responses, we should pass it to the 'all()' method, NOT the constructor.
            self.table = self.airtable_api.table(
                self.base_id, 
                self.config['airtable']['tables']['main_list']
            )
            
            # Initialize Leads Table
            try:
                self.leads_table = self.airtable_api.table(self.base_id, LEADS_TABLE_NAME)
                logging.info(f"Connected to Leads Table: {LEADS_TABLE_NAME}")
            except Exception:
                logging.warning(f"Leads Table '{LEADS_TABLE_NAME}' not found or connection failed.")
                self.leads_table = None
            
            # Initialize Trips Catalog Table
            self.trips_table = None
            if 'trips_base_id' in self.config['airtable']:
                self.trips_base_id = self.config['airtable']['trips_base_id']
                # Trips catalog can still use names if we want, or switch to IDs if we mapped it.
                # For now, let's keep Trips Catalog as is (Names) to avoid breaking search logic unless we mapped it too.
                # Assuming 'Trips' table structure is stable or less critical for this specific refactor.
                self.trips_table = self.airtable_api.table(self.trips_base_id, self.config['airtable']['tables']['trips_catalog'])
                logging.info("Connected to Trips Catalog Airtable.")
            else:
                logging.warning("Trips Base ID not found in config.")

            # Initialize Hotel Transfer Table
            try:
                self.hotel_transfer_table = self.airtable_api.table(self.base_id, HOTEL_TRANSFER_TABLE_NAME)
                logging.info(f"Connected to Hotel Transfer Table: {HOTEL_TRANSFER_TABLE_NAME}")
            except Exception:
                logging.warning(f"Hotel Transfer Table '{HOTEL_TRANSFER_TABLE_NAME}' not found.")
                self.hotel_transfer_table = None

            # Initialize MPC Table (Master Product Catalog)
            try:
                self.mpc_table = self.airtable_api.table(self.base_id, "MPC")
                logging.info("Connected to MPC Table.")
            except Exception:
                logging.warning("MPC Table not found.")
                self.mpc_table = None

            self.kb = KnowledgeBase()
            # Sync Knowledge Base with Trips if available
            if self.trips_table:
                logging.info("Syncing Trips DB to Knowledge Base...")
                # Fetch with cell_format='string' to get readable names for Linked Records (like Inclusions)
                try:
                    all_trips = self.trips_table.all(cell_format='string', time_zone='Africa/Cairo', user_locale='en-US')
                except Exception as e:
                    logging.warning(f"Failed to fetch trips with string format, falling back to default: {e}")
                    all_trips = self.trips_table.all()
                    
                self.kb.sync_trips_from_airtable(all_trips)
            
            self.kb.build_if_needed()
            
            # --- DYNAMIC SCHEMA DISCOVERY ---
            logging.info("Analyzing Table Schemas for Context...")
            self.trips_schema_context = self._analyze_table_schema(self.trips_table)
            # We can also analyze the Booking table schema if needed, but usually Trips is more opaque
            
            logging.info("Connected to Airtable and Knowledge Base ready.")
        except Exception as e:
            logging.error(f"Airtable connection failed: {e}")

    def _analyze_table_schema(self, table, sample_size=3):
        """
        Dynamically inspects a table to create a schema reference for the AI.
        Returns a string describing fields, types, and examples.
        """
        if not table:
            return "Table not available."
            
        try:
            # Use cell_format='string' to get readable examples
            try:
                records = table.all(max_records=sample_size, cell_format='string', time_zone='Africa/Cairo', user_locale='en-US')
            except Exception:
                records = table.all(max_records=sample_size)
                
            if not records:
                return "Table is empty."
                
            schema_map = {}
            
            for rec in records:
                fields = rec.get('fields', {})
                for key, val in fields.items():
                    if key not in schema_map:
                        # Determine readable name
                        readable = ID_TO_READABLE_NAME.get(key, key)
                        # Infer simple type
                        val_type = type(val).__name__
                        if isinstance(val, list):
                            val_type = "List"
                        
                        schema_map[key] = {
                            "name": readable,
                            "type": val_type,
                            "examples": set()
                        }
                    
                    # Add unique examples (up to 2)
                    if val and len(schema_map[key]["examples"]) < 2:
                        s_val = str(val)
                        if len(s_val) > 50: s_val = s_val[:47] + "..."
                        schema_map[key]["examples"].add(s_val)
            
            # Format output
            lines = []
            for key, info in schema_map.items():
                examples = ", ".join([f'"{ex}"' for ex in info["examples"]])
                lines.append(f'- Field: "{info["name"]}" | Type: {info["type"]} | Examples: {examples}')
                
            return "\n".join(lines)
        except Exception as e:
            logging.error(f"Schema analysis failed: {e}")
            return "Schema analysis failed."

    def _get_manual_cairo_offset(self, dt_utc):
        """
        Manually calculate Cairo Offset (UTC+2 Winter, UTC+3 Summer)
        Egypt DST: Last Friday of April to Last Thursday of October.
        Approximation: May to September is definitely Summer (+3).
        April and October are transitional.
        Jan, Feb, Mar, Nov, Dec are Winter (+2).
        """
        # Simple approximation for fallback
        month = dt_utc.month
        if 5 <= month <= 9: # May to Sept -> Summer
            return timedelta(hours=3)
        elif month in [1, 2, 3, 11, 12]: # Winter
            return timedelta(hours=2)
        else:
            if month == 10:
                return timedelta(hours=3)
            return timedelta(hours=2)

    def get_field_value(self, fields, field_id):
        """
        Robustly get field value using ID or Mapped Name.
        """
        # Safety Check
        if not fields:
            return None
            
        # 1. Try ID directly (if fetch used IDs)
        val = fields.get(field_id)
        if val is not None:
            return val
            
        # 2. Try Mapped Name (if fetch used Names)
        name = ID_TO_READABLE_NAME.get(field_id)
        if name:
            val = fields.get(name)
            if val is not None:
                return val
                
        return None

    def get_corrected_trip_date(self, date_trip_str):
        """
        Parses trip date from Airtable string and converts to EET (Cairo Time).
        Handles ISO format, space-separated format, and simple date.
        """
        try:
            if not date_trip_str:
                return None, "Unknown Date"
            
            # Normalize format: Replace space with T to handle "2026-01-22 00:00:00"
            clean_date_str = date_trip_str.strip()
            if ' ' in clean_date_str and 'T' not in clean_date_str:
                clean_date_str = clean_date_str.replace(' ', 'T')
            
            # Handle ISO format
            if 'T' in clean_date_str:
                # Handle Z for UTC
                if clean_date_str.endswith('Z'):
                    clean_date_str = clean_date_str.replace('Z', '+00:00')
                
                try:
                    trip_dt = datetime.fromisoformat(clean_date_str)
                except ValueError:
                     trip_dt = datetime.fromisoformat(clean_date_str.split('.')[0])

                # If naive (no timezone), ASSUME UTC to avoid system local time interference
                if trip_dt.tzinfo is None:
                    trip_dt = trip_dt.replace(tzinfo=pytz.utc)
                
                # Convert to Cairo Time
                if self.cairo_tz:
                    trip_dt_cairo = trip_dt.astimezone(self.cairo_tz)
                else:
                    offset = self._get_manual_cairo_offset(trip_dt)
                    trip_dt_cairo = trip_dt + offset
                    
                return trip_dt_cairo.date(), trip_dt_cairo.strftime("%A, %d %B %Y")
            else:
                # Handle simple YYYY-MM-DD
                trip_date = datetime.strptime(clean_date_str, "%Y-%m-%d").date()
                return trip_date, trip_date.strftime("%A, %d %B %Y")
        except Exception as e:
            logging.warning(f"Date parsing failed for '{date_trip_str}': {e}")
            try:
                match = re.search(r'(\d{4}-\d{2}-\d{2})', str(date_trip_str))
                if match:
                     d_str = match.group(1)
                     d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                     return d_obj, d_obj.strftime("%A, %d %B %Y")
            except:
                pass
            return None, str(date_trip_str)


    def search_trips_db(self, query):
        """
        Search the Trips Airtable for trip details.
        Matches against Title, TripCode, or keywords in Description.
        """
        if not self.trips_table:
            return ""
            
        try:
            all_trips = self.trips_table.all()
            
            query_lower = query.lower()
            matches = []
            
            for trip in all_trips:
                fields = trip['fields']
                title = fields.get('Title', '').lower()
                code = fields.get('TripCode', '').lower()
                
                # Score match
                score = 0
                if code and code in query_lower:
                    score += 100 # Exact code match is strong
                
                # Check for Title Match
                if title:
                    # Exact phrase match (Strong)
                    if query_lower in title:
                        score += 50
                    
                    # Keyword match (Flexible)
                    query_words = set(query_lower.split())
                    # Clean title words (remove punctuation)
                    title_clean = re.sub(r'[^\w\s]', '', title).lower()
                    title_words = set(title_clean.split())
                    
                    overlap = len(query_words.intersection(title_words))
                    if overlap > 0:
                        score += 10 * overlap
                        
                if score > 0:
                    matches.append((score, fields))
            
            matches.sort(key=lambda x: x[0], reverse=True)
            
            if not matches:
                return ""
                
            best_match = matches[0][1]
            
            context = f"""
            **Trip Details Found in Database:**
            - **Title:** {best_match.get('Title')}
            - **Code:** {best_match.get('TripCode')}
            - **Duration:** {best_match.get('Duration_Hours')} {best_match.get('Duration_Unit')}
            - **Price From:** {best_match.get('Price_From')} {best_match.get('Currency')}
            - **Highlights:** {best_match.get('TripHighlights')}
            - **Description:** {best_match.get('Trip_Description', '')[:800]}...
            - **Inclusions:** {best_match.get('TripIncludes')}
            - **Exclusions:** {best_match.get('TripExcludes')}
            - **Itinerary Steps:** {best_match.get('ItinerarySteps')}
            - **Itinerary Description:** {best_match.get('Itinerary_Description', '')[:500]}...
            - **FAQs:** {best_match.get('TripFAQs')}
            - **Important Notes:** {best_match.get('FTS_Notice')}
            """
            return context

        except Exception as e:
            logging.error(f"Error searching Trips DB: {e}")
            return ""

    def get_kb_context(self, query_text):
        """
        Retrieves relevant context from the Knowledge Base (Trips & Past Emails).
        """
        try:
            if not query_text:
                return ""
                
            # Search KB (Trips + Emails)
            # The KB now has smart fallback (Strict -> Keywords) to find "similar meaning"
            results = self.kb.search(query_text, top_k=4)
            
            if not results:
                return ""

            ctx = ""
            for r in results:
                # Format clearly for the LLM to understand this is PAST DATA
                source_label = r.get('source', 'Unknown Source')
                content = r.get('content', '')
                
                if source_label == "Email Archive":
                    ctx += f"--- [PAST SIMILAR TICKET] ---\n{content}\n"
                else:
                    ctx += f"--- [INTERNAL DATA: {source_label}] ---\n{content}\n"
            
            return ctx
        except Exception as e:
            logging.error(f"KB search error: {e}")
            return ""

    def update_booking_record(self, record_id, updates, table_name=None):
        """Update a record in the correct table (Main or Leads)."""
        try:
            target_table = self.table # Default
            
            if table_name == LEADS_TABLE_NAME and self.leads_table:
                target_table = self.leads_table
            
            # Use typecast=True to allow creating new Select options if needed
            target_table.update(record_id, updates, typecast=True)
            logging.info(f"Updated record {record_id} in {table_name or 'Main List'}")
        except Exception as e:
            logging.error(f"Failed to update record {record_id} in {table_name}: {e}")
            raise e

    def find_booking_by_number(self, booking_nr):
        """Find a booking record by Booking Nr. using ID query"""
        try:
            # Formula still uses Field Names usually! 
            # PyAirtable 'formula' parameter sends string to Airtable API.
            # Airtable API formulas use Field Names, NOT IDs.
            # So we MUST keep using Names in the formula string.
            
            # Sanitize booking_nr (trim spaces)
            booking_nr = str(booking_nr).strip()
            
            formula = f"{{Booking Nr.}}='{booking_nr}'"
            logging.info(f"DEBUG: Searching Table with formula: {formula}")
            
            records = self.table.all(formula=formula)
            logging.info(f"DEBUG: Search result count: {len(records)}")
            
            if records:
                rec = records[0]
                rec['table_name'] = self.config['airtable']['tables']['main_list']
                return rec
            
            # Check Leads Table
            # SKIP: Leads Table usually does not have "Booking Nr." field. 
            # Searching it causes API errors and confusion.
            # if self.leads_table:
            #    try:
            #        # Leads table might not have "Booking Nr." field.
            #        # Only search if we are sure, or catch the error.
            #        logging.info(f"DEBUG: Searching Leads Table with formula: {formula}")
            #        lead_records = self.leads_table.all(formula=formula)
            #        if lead_records:
            #            rec = lead_records[0]
            #            rec['table_name'] = LEADS_TABLE_NAME
            #            return rec
            #    except Exception as e:
            #        # Ignore error if field doesn't exist in Leads
            #        logging.warning(f"Skipping Leads lookup for Booking Nr {booking_nr} (Field might be missing): {e}")
            
            return None
        except Exception as e:
            logging.error(f"Error finding booking {booking_nr}: {e}")
            return None



    def create_lead_record(self, email, name="Guest", initial_message="", phone=None):
        """
        Create a new 'Lead' record for an unknown user.
        If 'Leads' table exists, create there. Otherwise, create in Main Table as 'Inquiry'.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            fake_booking_nr = f"LEAD-{timestamp}"
            
            # Clean phone if provided
            clean_phone = self.clean_phone_for_whatsapp(phone) if phone else None
            
            if self.leads_table:
                # Use Leads Table Fields
                fields = {
                    LeadFieldIds.CUSTOMER_NAME: name,
                    LeadFieldIds.CUSTOMER_EMAIL: email,
                    LeadFieldIds.LEAD_STATUS: "New (جديد)", 
                    LeadFieldIds.AI_CHAT_LOG: f"[SYSTEM]: New Lead Created. Initial Message: {initial_message}",
                    LeadFieldIds.LAST_INTERACTION: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                if clean_phone:
                    fields[LeadFieldIds.CUSTOMER_PHONE] = clean_phone
                    
                record = self.leads_table.create(fields, typecast=True)
                logging.info(f"Created new Lead record in Leads Table: {email}")
                return record
            else:
                # Fallback to Main Table
                fields = {
                    FieldIds.BOOKING_NR: fake_booking_nr,
                    FieldIds.CUSTOMER_NAME: name,
                    FieldIds.CUSTOMER_EMAIL: email,
                    FieldIds.BOOKING_STATUS: "Inquiry", 
                    FieldIds.AI_CHAT_LOG: f"[SYSTEM]: New Lead Created. Initial Message: {initial_message}"
                }
                if clean_phone:
                     fields[FieldIds.CUSTOMER_PHONE] = clean_phone
                     
                record = self.table.create(fields, typecast=True)
                logging.info(f"Created new Lead record in Main Table: {fake_booking_nr}")
                return record

        except Exception as e:
            logging.error(f"Failed to create lead record for {email}: {e}")
            return None

    def send_email(self, to_email, subject, html_content, thread_id=None, in_reply_to_message_id=None, attachments=None, record_id=None):
        """
        Send HTML email using Gmail OAuth Service
        Respects 'draft_mode' setting in config.
        """
        if not self.gmail_service.service:
            logging.error("Gmail Service not authenticated. Cannot send email.")
            return False
        
        # Check Draft Mode
        email_settings = self.config.get('email', {}).get('settings', {})
        draft_mode = email_settings.get('draft_mode', False)
        
        # In draft mode, we create a draft and log it for human review/learning
        if draft_mode:
            logging.info(f"DRAFT MODE ON: Creating draft instead of sending to {to_email}")
            result = self.gmail_service.create_draft(
                to_email, 
                subject, 
                html_content, 
                sender_name=self.config['company_info']['name'],
                thread_id=thread_id,
                in_reply_to_message_id=in_reply_to_message_id,
                attachments=attachments
            )
            
            if result and record_id:
                # Log draft for future audit/learning
                audit_utils.log_draft(result['id'], thread_id, record_id, html_content)
                
            return result is not None
            
        return self.gmail_service.send_email(
            to_email, 
            subject, 
            html_content, 
            sender_name=self.config['company_info']['name'],
            thread_id=thread_id,
            in_reply_to_message_id=in_reply_to_message_id,
            attachments=attachments
        )

    def learn_from_human_edits(self):
        """
        SELF-LEARNING: Scan drafts that were sent by humans (not by AI directly)
        to see if the human changed the AI's suggested draft.
        """
        logging.info("Checking for human-edited drafts to learn...")
        pending = audit_utils.get_pending_drafts()
        
        if not pending:
            return

        for draft in pending:
            draft_id = draft['draft_id']
            thread_id = draft['thread_id']
            record_id = draft['record_id']
            original_body = draft['original_body']
            
            # Check if draft still exists
            try:
                self.gmail_service.service.users().drafts().get(userId='me', id=draft_id).execute()
                # Draft exists -> Still pending review
                continue
            except:
                # Draft gone -> Likely sent (or deleted)
                pass
            
            # Get thread history
            history = self.gmail_service.get_thread_history(thread_id)
            if not history:
                audit_utils.mark_draft_processed(draft_id, 'missing_history')
                continue
                
            # Assume last message is the sent one
            last_message = history[-1]
            
            sent_body = last_message['body']
            
            # Compare
            # Simple clean HTML
            clean_orig = re.sub('<[^<]+?>', '', original_body).strip()
            clean_sent = re.sub('<[^<]+?>', '', sent_body).strip()
            
            similarity = difflib.SequenceMatcher(None, clean_orig, clean_sent).ratio()
            
            if similarity < 0.99: # If changed
                logging.info(f"Draft {draft_id} was edited (Sim: {similarity:.2f})")
                
                # Log to Airtable
                log_msg = f"[HUMAN_CORRECTION]: Draft edited before sending.\nSimilarity: {similarity*100:.1f}%\nFinal Sent: {clean_sent}..."
                self.append_to_chat_log(record_id, log_msg, sender="System", source="Audit")
                
                # Save for learning
                audit_utils.save_correction(clean_orig, clean_sent, trigger_context="Draft Edit")
            else:
                logging.info(f"Draft {draft_id} sent without changes.")
                
            audit_utils.mark_draft_processed(draft_id, 'checked')

    def log_proposed_reply_for_learning(self, record_id, proposed_text, table_name=None):
        """
        Log the AI's proposed reply to a special field or log for later comparison.
        This helps in self-learning by comparing what AI proposed vs what Human actually sent.
        """
        try:
            # We will append this to the AI Chat Log with a special tag [PROPOSED_DRAFT]
            self.append_to_chat_log(
                record_id, 
                f"[PROPOSED_DRAFT]\n{proposed_text}", 
                sender="System", 
                source="AI_Learning", 
                table_name=table_name
            )
        except Exception as e:
            logging.warning(f"Failed to log proposed reply for learning: {e}")

    def append_to_chat_log(self, record_id, message, sender="AI", source="System", table_name=None):
        """
        Unified helper to append messages to Airtable Chat Log and Session Cache.
        Format: [YYYY-MM-DD HH:MM:SS] [Source - Sender]: Message
        THREAD-SAFE: Uses Keyed Mutex to allow parallel processing of DIFFERENT records.
        """
        with self.mutex.lock(record_id):
            try:
                timestamp = (datetime.utcnow() + CAIRO_OFFSET).strftime("%Y-%m-%d %H:%M:%S")
                log_entry = f"\n[{timestamp}] [{source} - {sender}]: {message}"
                
                # 1. Update Airtable
                table = self.table
                if table_name == LEADS_TABLE_NAME and self.leads_table:
                    table = self.leads_table
                
                # Fetch current log
                rec = table.get(record_id)
                current_log = self.get_field_value(rec['fields'], FieldIds.AI_CHAT_LOG) or ""
                
                # Use Lead ID if Main ID missing
                if not current_log and table_name == LEADS_TABLE_NAME:
                     current_log = self.get_field_value(rec['fields'], LeadFieldIds.AI_CHAT_LOG) or ""

                new_log = current_log + "\n" + log_entry
                
                update_data = {FieldIds.AI_CHAT_LOG: new_log}
                # For Leads, map to Lead Field ID if needed
                if table_name == LEADS_TABLE_NAME:
                     # FORCE using the Lead Field ID directly if we are in Leads Table
                     update_data = {LeadFieldIds.AI_CHAT_LOG: new_log}
                
                table.update(record_id, update_data, typecast=True)
                logging.info(f"Appended to Chat Log for {record_id} ({source})")
                
                return True
            except Exception as e:
                logging.error(f"Failed to append to chat log: {e}")
                return False

    def process_new_bookings(self):
        """
        Check Airtable for new bookings based on specific views
        """
        logging.info("Checking for new bookings...")
        try:
            # Fetch records from the 'Ahmady' view (or Main View)
            # Use NAMES directly to avoid issues with ID support in this environment
            records = self.table.all(view=self.config['airtable']['views']['ahmady_view'], max_records=10)
            
            for record in records:
                self.handle_booking(record)
                
        except Exception as e:
            logging.error(f"Error checking bookings: {e}")

    def handle_booking(self, record):
        """
        Process a single booking record (Using IDs)
        """
        record_id = record['id']
        fields = record['fields']
        
        logging.info(f"Processing booking: {record_id}")
        
        # 1. Handle Pickup Details (Priority 1)
        # We assume the config 'update_status' maps to 'pickup time' -> FieldIds.PICKUP_TIME
        pickup_time = self.get_field_value(fields, FieldIds.PICKUP_TIME)
        
        if pickup_time and pickup_time != 'Done':
            self.process_pickup_details(record_id, fields, pickup_time)

        # 2. Handle Customer Inquiries (Priority 2)
        customer_message = self.get_field_value(fields, FieldIds.CUSTOMER_LAST_MESSAGE) 
        ai_chat_log = self.get_field_value(fields, FieldIds.AI_CHAT_LOG) or ''
        
        if customer_message and customer_message not in ai_chat_log:
             self.handle_customer_inquiry(record_id, fields, customer_message)


    def _download_file_content(self, url):
        """Download file content from URL."""
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logging.error(f"Failed to download file from {url}: {e}")
            return None

    def _get_valid_attachments(self, fields):
        """
        Download and filter attachments from Airtable fields.
        Checks both 'Attachments' and 'Tickets Files' fields.
        Returns a list of dicts suitable for send_email.
        Filters out images (png, jpg) and keeps documents (pdf, etc).
        """
        processed_attachments = []
        
        # Helper to process a list of attachments
        def process_list(att_list):
            if not att_list:
                return
            
            # Safety Fix for AttributeError
            if isinstance(att_list, str):
                att_list = [{'url': att_list, 'filename': 'document'}]
            elif isinstance(att_list, dict):
                att_list = [att_list]
            elif not isinstance(att_list, list):
                return

            for att in att_list:
                if not isinstance(att, dict): continue
                
                filename = att.get('filename', 'document').lower()
                url = att.get('url')
                
                # Filter out images - logic matches Template Pickup.txt
                if filename.endswith(('.png', '.jpg', '.jpeg')):
                    continue
                    
                content = self._download_file_content(url)
                if content:
                    processed_attachments.append({
                        'filename': att.get('filename'),
                        'content': content,
                        'mime_type': att.get('type', 'application/octet-stream')
                    })

        # 1. Check 'Attachments' field
        process_list(self.get_field_value(fields, FieldIds.ATTACHMENTS))
        
        # 2. Check 'Tickets Files' field (Common for ticket-only trips)
        process_list(self.get_field_value(fields, FieldIds.TICKETS))
        
        return processed_attachments

    def process_pickup_details(self, record_id, fields, pickup_time, force_resend=False):
        logging.info(f"Processing pickup for {record_id}. Time: {pickup_time} (Force: {force_resend})")
        
        # 0. Check DEDUPLICATION (Avoid Resending)
        ai_chat_log = self.get_field_value(fields, FieldIds.AI_CHAT_LOG) or ""
        
        if not force_resend:
            if "[SYSTEM]: Pickup Email Sent" in ai_chat_log or "[SYSTEM]: Ticket Email Sent" in ai_chat_log:
                logging.info(f"Skipping {record_id} - Email already sent (found in log).")
                return

        # 1. Parse Trip Date Correctly
        date_trip_str = self.get_field_value(fields, FieldIds.DATE_TRIP)
        trip_date_obj, formatted_trip_date = self.get_corrected_trip_date(date_trip_str)

        # 2. Extract Data (Using IDs)
        trip_name = self.get_field_value(fields, FieldIds.TRIP_NAME) or ''
        agency = self.get_field_value(fields, FieldIds.AGENCY) or ''
        hotel_name = self.get_field_value(fields, FieldIds.HOTEL_NAME)
        room_number = self.get_field_value(fields, FieldIds.ROOM_NUMBER)
        customer_email = self.get_field_value(fields, FieldIds.CUSTOMER_EMAIL)
        customer_name = self.get_field_value(fields, FieldIds.CUSTOMER_NAME)
        booking_nr = self.get_field_value(fields, FieldIds.BOOKING_NR)
        
        if not customer_email:
            logging.warning(f"No customer email found for record {record_id}")
            return

        # 3. Determine Email Type
        trip_name_lower = trip_name.lower()
        is_ticket_email = 'qr' in trip_name_lower or 'sound' in trip_name_lower
        is_flight_booking = 'plane' in trip_name_lower or 'flight' in trip_name_lower
        
        # 4. Handle Attachments
        processed_attachments = self._get_valid_attachments(fields)
        has_attachments = len(processed_attachments) > 0

        # 5. Check Missing Info (Only if NOT Ticket Email)
        missing_details = []
        if not is_ticket_email:
             if not hotel_name: missing_details.append("Hotel Name")
             if not room_number: missing_details.append("Room Number")
        
        if missing_details:
             logging.info(f"Missing info for {record_id}: {missing_details}. Sending Action Required Email.")
             html_content = email_templates.generate_missing_info_email(
                 customer_name, trip_name, booking_nr, formatted_trip_date, missing_details
             )
             subject = f"Action Required: Missing Information for {trip_name} - {booking_nr}"
             self.send_email(customer_email, subject, html_content, record_id=record_id)
             return

        # 6. Prepare Data for Templates
        booking_data = {
            'customerName': customer_name,
            'bookingNr': booking_nr,
            'dateTrip': formatted_trip_date,
            'pickupTime': pickup_time,
            'hotelName': hotel_name,
            'nonBillableAddons': self.get_field_value(fields, FieldIds.NON_BILLABLE_ADDONS),
            'addOns': self.get_field_value(fields, FieldIds.COLLECTING_ON_DATE_TRIP), # Assuming this is 'Add Ons' amount or text? Field map says COLLECTING_ON_DATE_TRIP
            'tripName': trip_name,
            'has_attachments': has_attachments,
            'agency': agency
        }

        # 7. Generate & Send Primary Email
        if is_ticket_email:
            # Send Ticket Email
            html_content = email_templates.generate_ticket_email(
                customer_name, trip_name, booking_nr, agency, 
                pickup_time=pickup_time, hotel_name=hotel_name, 
                has_attachments=has_attachments, trip_name=trip_name
            )
            subject = f"Your Tickets for {trip_name} - {booking_nr} ✨"
            email_type_log = "Ticket Email"
        else:
            # Send Pickup Email
            html_content = email_templates.generate_pickup_email_html(booking_data)
            subject = f"Pickup Details: {trip_name} - {booking_nr} 🚐"
            email_type_log = "Pickup Email"

        success = self.send_email(customer_email, subject, html_content, attachments=processed_attachments, record_id=record_id)

        if success:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_msg = f"\n[SYSTEM]: {email_type_log} Sent at {timestamp}"
            
            # 8. Send Airport Email (if Flight)
            if is_flight_booking:
                time.sleep(2) # Small delay
                airport_html = email_templates.generate_airport_email_html(customer_name, booking_nr, trip_name)
                airport_subject = f"Important Airport Instructions - {trip_name} {booking_nr} ✈️"
                
                if self.send_email(customer_email, airport_subject, airport_html, record_id=record_id):
                    log_msg += f"\n[SYSTEM]: Airport Email Sent at {timestamp}"
            
            # Update Log
            updated_log = ai_chat_log + log_msg
            self.table.update(record_id, {FieldIds.AI_CHAT_LOG: updated_log})
            logging.info(f"Processed {record_id}: {log_msg}")

    def handle_customer_inquiry(self, record_id, fields, message):
        """
        Analyze customer message using Hybrid Logic (Rules -> KB -> AI).
        """
        logging.info(f"Handling inquiry for {record_id}: {message}")
        
        # --- PREPARE CONTEXT ---
        date_trip_str = self.get_field_value(fields, FieldIds.DATE_TRIP)
        trip_date, formatted_trip_date = self.get_corrected_trip_date(date_trip_str)
        
        trip_name = self.get_field_value(fields, FieldIds.TRIP_NAME) or ''
        booking_nr = self.get_field_value(fields, FieldIds.BOOKING_NR)
        customer_name = self.get_field_value(fields, FieldIds.CUSTOMER_NAME) or 'Guest'
        customer_email = self.get_field_value(fields, FieldIds.CUSTOMER_EMAIL)
        msg_lower = message.lower().strip()

        # Extract Attachments
        processed_attachments = self._get_valid_attachments(fields)
        has_attachments = len(processed_attachments) > 0

        # --- LEVEL 1: RULE-BASED RESPONSES ---
        
        # Rule 1: Ticket Request
        is_ticket_only = 'qr' in trip_name.lower() or 'sound' in trip_name.lower() or self.get_field_value(fields, FieldIds.AGENCY) == 'Tiqets'
        
        # Check if user is asking for tickets
        user_wants_tickets = "ticket" in msg_lower and ("send" in msg_lower or "where" in msg_lower or "need" in msg_lower or "didn't receive" in msg_lower)
        
        if user_wants_tickets:
             if processed_attachments:
                 html_content = email_templates.generate_ticket_email(
                     customer_name, trip_name, booking_nr, self.get_field_value(fields, FieldIds.AGENCY) or '', 
                     has_attachments=True, trip_name=trip_name
                 )
                 self.send_email(customer_email, f"Your Tickets: {trip_name}", html_content, attachments=processed_attachments)
                 logging.info(f"Resent tickets to {customer_email}")
                 return
             else:
                 # Escalation needed if user wants tickets but we have none
                 self.notify_operations(fields, message, "[User requested tickets but none found in Airtable]")
                 return

        # 2. Check for URGENT Pickup Inquiry
        is_urgent_pickup = False
        if trip_date:
            now_cairo = datetime.utcnow() + CAIRO_OFFSET
            if trip_date == now_cairo.date() or trip_date == (now_cairo + timedelta(days=1)).date():
                if now_cairo.hour >= 18:
                    is_urgent_pickup = True

        # 3. Check for Missing Hotel/Room Info
        hotel_name = self.get_field_value(fields, FieldIds.HOTEL_NAME) or ''
        room_number = self.get_field_value(fields, FieldIds.ROOM_NUMBER) or ''
        pickup_time_val = self.get_field_value(fields, FieldIds.PICKUP_TIME)
        
        missing_details = []
        if not hotel_name:
            missing_details.append("Hotel Name")
        if not room_number:
            missing_details.append("Room Number")
            
        missing_hotel_info = len(missing_details) > 0

        # Rule 1.5: RESEND Pickup Confirmation (If requested)
        is_pickup_query = "pickup" in msg_lower or "time" in msg_lower or "when" in msg_lower
        
        if is_pickup_query and pickup_time_val and not missing_hotel_info:
             logging.info(f"User requested pickup time for {record_id}. Resending formal email.")
             self.process_pickup_details(record_id, fields, pickup_time_val, force_resend=True)
             return
        
        # --- LEVEL 2: KNOWLEDGE BASE SEARCH ---
        kb_results = self.kb.search(f"{trip_name} {message}", top_k=3)
        kb_context = ""
        if kb_results:
            kb_context = "**KNOWLEDGE BASE (Trusted Internal Data):**\n"
            for res in kb_results:
                kb_context += f"[{res['source']}]\n{res['content']}\n---\n"

        # --- AI DECISION & RESPONSE ---
        booking_record = {'id': record_id, 'fields': fields}
        
        # Only attach if user explicitly asks for tickets/docs OR it's a ticket-related inquiry
        should_attach = has_attachments and user_wants_tickets
        
        response = self.generate_smart_reply(
            f"Conversation History:\n{message}", 
            kb_context, 
            message, 
            has_attachments=should_attach,
            booking_record=booking_record
        )
        
        logging.info(f"AI Response generated: {response}")
        
        # Check for Escalation
        was_escalated = False
        if response.strip().startswith("[ESCALATE]"):
            was_escalated = True
            logging.info("Response requires escalation. Notifying Operations.")
            response = response.replace("[ESCALATE]", "").strip() 
            
            # Pass customer email from fields if available
            cust_email = self.get_field_value(fields, FieldIds.CUSTOMER_EMAIL)
            self.notify_operations(fields, message, response, sender_email=cust_email)
        
        # 3. Send Reply
        customer_email = self.get_field_value(fields, FieldIds.CUSTOMER_EMAIL)
        if customer_email:
            subject = f"Re: Your inquiry about {self.get_field_value(fields, FieldIds.TRIP_NAME)}"
            html_content = email_templates.generate_standard_email_template(
                content=response.replace('\n', '<br>'),
                title=subject,
                customer_name=self.get_field_value(fields, FieldIds.CUSTOMER_NAME) or 'Guest'
            )
            
            # Only send attachments if logic decided to
            final_attachments = processed_attachments if should_attach else []
            self.send_email(customer_email, subject, html_content, attachments=final_attachments, record_id=record_id)
            
            # 4. Log to Airtable
            try:
                current_log = self.get_field_value(fields, FieldIds.AI_CHAT_LOG) or ''
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_log = f"{current_log}\n\n[{timestamp}] [Customer]: {message}\n[AI]: {response}"
                
                updates = {FieldIds.AI_CHAT_LOG: new_log}
                if was_escalated:
                     updates[FieldIds.AI_CHAT_STATUS] = "ESCALATED"
                else:
                     # Clear RESOLVED status on new activity
                     current_status = self.get_field_value(fields, FieldIds.AI_CHAT_STATUS)
                     if current_status == "RESOLVED":
                         updates[FieldIds.AI_CHAT_STATUS] = None
                     
                self.table.update(record_id, updates)
            except Exception as e:
                logging.error(f"Failed to update chat log: {e}") 

    def process_ticket_request(self, record):
        """
        Handle user requests for tickets.
        1. Check Airtable Attachments.
        2. If found, upload to Cloudinary to get permanent link.
        3. If not found, trigger escalation.
        Returns: (reply_text, is_success)
        """
        attachments = record['fields'].get(FieldIds.ATTACHMENTS)
        
        if not attachments:
            return ("I could not find your tickets attached to the booking. I have escalated this to our operations team to send them to you manually immediately.", False)
            
        links = []
        try:
            for att in attachments:
                url = att.get('url')
                filename = att.get('filename', 'ticket')
                if url:
                    # Upload to Cloudinary
                    # Use 'auto' to handle PDFs, Images, etc.
                    # Use upload_preset if configured, otherwise default
                    res = cloudinary.uploader.upload(
                        url, 
                        resource_type="auto",
                        folder="Customer_tiqets", # Organization
                        public_id=f"{record['id']}_{filename}" # Unique name
                    )
                    secure_url = res.get('secure_url')
                    if secure_url:
                        links.append(secure_url)
                        
            if links:
                links_text = "\n".join([f"- {link}" for link in links])
                return (f"Here are the permanent links to your tickets/documents:\n{links_text}\n\nPlease let me know if you have any trouble opening them.", True)
            else:
                return ("I found attachment records but could not generate links. Escalating to human agent.", False)
                
        except Exception as e:
            logging.error(f"Error uploading to Cloudinary: {e}")
            return ("I encountered a technical error retrieving your tickets. I have notified our team to send them to you directly.", False)

    def notify_operations(self, fields, customer_message, ai_reply, sender_email=None, other_contacts=None, department="SUPPORT"):
        ops_email = "quality.fts@ftstravels.com" 
        booking_nr = self.get_field_value(fields, FieldIds.BOOKING_NR) or 'Unknown'
        trip_name = self.get_field_value(fields, FieldIds.TRIP_NAME) or 'Unknown Trip'
        customer_name = self.get_field_value(fields, FieldIds.CUSTOMER_NAME) or 'Unknown Customer'
        
        # Prepare Contact Info Block
        contact_info_html = ""
        if sender_email:
            contact_info_html += f"<li><b>Sender Email:</b> {sender_email}</li>"
        
        if other_contacts:
             if other_contacts.get("email"):
                 contact_info_html += f"<li><b>Extracted Email:</b> {other_contacts.get('email')}</li>"
             if other_contacts.get("phone"):
                 contact_info_html += f"<li><b>Extracted Phone:</b> {other_contacts.get('phone')}</li>"
        
        subject = f"⚠️ [{department}] ESCALATION: Booking {booking_nr} - {customer_name}"
        
        html_content = f"""
        <h2>⚠️ Action Required: {department} Escalation</h2>
        <p>The AI Assistant has routed this inquiry to the <b>{department}</b> team.</p>
        
        <h3>Booking Details:</h3>
        <ul>
            <li><b>Customer:</b> {customer_name}</li>
            <li><b>Booking Nr:</b> {booking_nr}</li>
            <li><b>Trip:</b> {trip_name}</li>
            {contact_info_html}
        </ul>
        
        <hr>
        <h3>💬 Customer Message:</h3>
        <p style="background-color: #f9f9f9; padding: 10px; border-left: 3px solid #007bff;">{customer_message}</p>
        
        <h3>🤖 AI Provisional Reply (Sent to Customer):</h3>
        <p style="background-color: #f0f0f0; padding: 10px; border-left: 3px solid #28a745;">{ai_reply}</p>
        
        <hr>
        <p><b>Please review this case and follow up with the customer if necessary.</b></p>
        <p style="color: #666; font-size: 12px;">
            <b>System Instruction:</b> When this issue is resolved, please change the <b>AI Chat Status</b> field in Airtable to <code>RESOLVED</code>. 
            This will allow the AI Agent to resume normal handling for this customer.
        </p>
        """
        
        logging.info(f"Sending escalation email to {ops_email}")
        self.send_email(ops_email, subject, html_content)

    def query_ai(self, prompt, system_role="assistant"):
        ai_section = self.config.get('ai', {})
        
        # Determine providers and order based on config structure
        if 'providers' in ai_section:
            providers_order = ai_section.get('order', [])
            providers = ai_section.get('providers', {})
        else:
            # Legacy config support (single provider)
            providers_order = ['default']
            providers = {'default': ai_section}
            
        last_error = None
        
        for provider_name in providers_order:
            provider_config = providers.get(provider_name)
            if not provider_config:
                continue
                
            api_key = provider_config.get('api_key')
            # Basic validation to skip placeholder keys
            if not api_key or "YOUR_" in api_key or len(api_key) < 10:
                logging.warning(f"AI Provider '{provider_name}' has invalid API Key. Skipping.")
                continue
                
            logging.info(f"Querying AI using provider: {provider_name}")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            system_content = f"You are a helpful travel assistant for {self.config['company_info']['name']}."
            if system_role == "assistant":
                 system_content += " CRITICAL RULE: You MUST reply in the SAME LANGUAGE as the user's last message. If they speak English, reply in English. If Arabic, reply in Arabic."
            elif system_role == "analyzer":
                system_content = "You are a logic analyzer. Output only keywords."

            payload = {
                "model": provider_config.get('model', 'gpt-3.5-turbo'),
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ],
                "temperature": provider_config.get('temperature', 0.7),
                "max_tokens": provider_config.get('max_tokens', 1000)
            }

            try:
                # 60s timeout to avoid hanging indefinitely
                response = requests.post(provider_config['api_url'], headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                result = response.json()
                content = result['choices'][0]['message']['content']
                return content
            except Exception as e:
                last_error = f"Provider {provider_name} failed: {e}"
                logging.error(last_error)
                # Continue to next provider in the loop
                continue

        return f"All AI providers failed. Last error: {last_error}"

    def update_session_memory(self, user_id, message, role="user"):
        """
        Update the in-memory session cache for a user (email or phone).
        Structure: List of dicts {'role': 'user'|'assistant', 'content': '...', 'timestamp': '...'}
        """
        if not user_id:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "role": role, 
            "content": message, 
            "timestamp": timestamp
        }
        
        if user_id in self.session_cache:
            # Append to existing session
            session = self.session_cache[user_id]
            session.append(entry)
            # Keep only last 20 messages to prevent bloat
            if len(session) > 20:
                session = session[-20:]
            self.session_cache[user_id] = session # Re-insert to refresh TTL
        else:
            # Create new session
            self.session_cache[user_id] = [entry]
            
    def get_session_memory(self, user_id, airtable_log=""):
        """
        Combine Airtable Log (Long-term) with Session Cache (Short-term/Immediate).
        """
        history_text = ""
        
        # 1. Add Airtable Log (Base)
        if airtable_log:
            history_text += f"{airtable_log}\n"
            
        # 2. Add Session Cache (Recent)
        # We need to be careful not to duplicate if Airtable sync is fast.
        # But since cache is transient, we can label it.
        
        if user_id and user_id in self.session_cache:
            session = self.session_cache[user_id]
            history_text += "\n--- [RECENT SESSION CACHE] ---\n"
            for msg in session:
                sender = "Customer" if msg['role'] == "user" else "AI"
                history_text += f"[{msg['timestamp']}] {sender}: {msg['content']}\n"
        
        return history_text

    def clean_phone_for_whatsapp(self, phone):
        """
        Cleans phone number to meet WhatsApp Cloud API requirements.
        - Removes spaces, dashes, parentheses.
        - Ensures it starts with '+' if it looks international.
        - ALLOWS '+' at start, but removes all other non-numeric chars.
        """
        if not phone:
            return None
        
        # 1. Remove all non-numeric characters EXCEPT '+'
        cleaned = re.sub(r'[^\d+]', '', str(phone))
        
        # 2. If multiple '+' exist (e.g. ++20), keep only the first one
        if cleaned.count('+') > 1:
            cleaned = '+' + cleaned.replace('+', '')
            
        # 3. Ensure it starts with + if missing (Heuristic: length > 10 and not starting with 00)
        # However, user requirement says "MUST be suitable for WhatsApp".
        # WhatsApp usually expects E.164 (e.g., +15551234567).
        # If the AI extracted "01012345678" (Egypt local), we might need to assume a country code?
        # For now, we just stick to the user's strict rule: "No spaces, no marks except +".
        
        return cleaned

    def extract_booking_data_using_ai(self, history_text, sender_email=None):
        """Extract booking details from conversation using AI. Returns dict of extracted data."""
        extraction_prompt = f"""
        Analyze the conversation history to extract NEW details provided by the customer.
        
        CRITICAL RULES:
        1. **CONTEXT IS KING**: Only extract data if the user is explicitly PROVIDING information to update their booking.
           - If user asks "What is Orange Bay?", "Orange Bay" is a TRIP QUERY, NOT a hotel name. DO NOT extract it.
           - If user says "My hotel is Orange Bay", THEN extract it.
           - If user says "I want details" (Arabic: "Ayza tafasil"), "Ayza" is a verb, NOT a name. DO NOT extract.
           
        2. **NAME VALIDATION (CRITICAL)**:
           - "Customer Name" MUST be a REAL PERSON'S NAME (e.g. "Monika", "John Smith").
           - Do NOT extract Company Names (e.g. "Viator", "Expedia", "GetYourGuide", "Tours", "Travels") as Customer Name.
           - Do NOT extract generic greetings (e.g. "Guest", "Customer", "Sir", "Madam") as Customer Name.
           - If the name looks like a company or generic term, return null for "Customer Name".

        3. **IGNORE QUERIES**: Do NOT extract entities mentioned in questions.
           - "Can I change to Hilton?" -> DO NOT extract Hilton yet (it's a request, not a confirmed fact).
           - "I am staying at Hilton." -> EXTRACT Hilton.

        3. **ARABIC WARNING**: 
           - Words like "Ayza", "Ayez", "Momken", "Law samht" are NOT names. Ignore them.

        Look for:
        - Booking Number (Booking Nr.)
        - Customer Name (The main contact person)
        - Traveler name (List ALL traveler names mentioned. Separate with commas)
        - Hotel Name
        - Room Number
        - Child Age (CHD Age)
        - Personal Email
        - Customer Phone
        
        Output ONLY valid JSON. Keys must match exactly: 
        "Booking Nr.", "Customer Name", "Traveler name", "Hotel Name", "Room number", "CHD Age", "Customer personal email", "Customer Phone".
        If a value is not found, do not include the key.
        
        Conversation:
        {history_text}
        """
        extracted_data_json = self.query_ai(extraction_prompt, system_role="analyzer")
        
        try:
            # Clean up JSON string
            if "```json" in extracted_data_json:
                extracted_data_json = extracted_data_json.split("```json")[1].split("```")[0]
            elif "```" in extracted_data_json:
                extracted_data_json = extracted_data_json.split("```")[1].split("```")[0]
                
            extracted_data = json.loads(extracted_data_json.strip())
            return extracted_data
            
        except Exception as e:
            logging.error(f"Error during AI data extraction: {e}")
            return {}

    def update_booking_from_extracted_data(self, record, extracted_data):
        """Update a booking record with data extracted by AI."""
        if not record or not extracted_data:
            return

        try:
            updates = {}
            for json_key, v in extracted_data.items():
                if json_key == 'Booking Nr.':
                    continue
                if not v:
                    continue
                
                # Map Friendly Key to Field ID
                field_id = JSON_KEY_TO_ID.get(json_key)
                if field_id:
                    # SPECIAL HANDLING: PHONE NUMBERS
                    if field_id == FieldIds.CUSTOMER_PHONE:
                        v = self.clean_phone_for_whatsapp(v)
                    
                    # Check if value is different? (Optional optimization)
                    # ONLY Update if the current value is EMPTY or different
                    # BUT for Hotel/Room/Passport, usually we want to update/overwrite if user provides it.
                    # We assume AI is smart enough to only extract if it's new info.
                    
                    current_val = record.get('fields', {}).get(field_id)
                    
                    # Logic: 
                    # 1. If current is empty -> UPDATE
                    # 2. If current exists but user provides new info -> UPDATE (Overwrite)
                    # 3. If same -> SKIP
                    
                    if str(current_val).strip() != str(v).strip():
                         updates[field_id] = v
                else:
                    logging.warning(f"Extracted key {json_key} not found in JSON_KEY_TO_ID map.")
                
            if updates:
                # Safe access for logging
                booking_nr = record.get('fields', {}).get(FieldIds.BOOKING_NR, "Unknown")
                logging.info(f"Updating Airtable for Booking {booking_nr} with {updates}")
                
                self.update_booking_record(record['id'], updates, table_name=record.get('table_name'))
                
                # Update local record fields to reflect changes immediately
                if 'fields' not in record:
                    record['fields'] = {}
                    
                for k, v in updates.items():
                    record['fields'][k] = v
                    
        except Exception as e:
             logging.error(f"Error updating booking from extracted data: {e}")

    def extract_and_update_booking_data(self, history_text, sender_email=None):
        """Deprecated wrapper for backward compatibility."""
        data = self.extract_booking_data_using_ai(history_text, sender_email)
        # We can't update here without finding the record first.
        # This wrapper is essentially broken now for the old logic unless we duplicate search logic.
        # But since we will update callers, it's fine.
        pass


    def extract_booking_numbers_regex(self, text):
        """Extract potential booking numbers using Regex. Returns list of (code, confidence)."""
        
        # 1. Mask Emails to avoid extracting parts of them
        # Pattern for email: something@something.something
        text_no_emails = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', ' ', text)
        
        # Pattern: Alphanumeric, 5-15 chars.
        matches = re.findall(r'\b[A-Z0-9-]{5,15}\b', text_no_emails, re.IGNORECASE)
        
        # Filter out common false positives
        ignore_words = {
            "drop-off", "pick-up", "check-in", "check-out", "sign-in", "sign-up", 
            "log-in", "log-out", "e-mail", "wi-fi", "add-on", "top-up", "follow-up",
            "stand-by", "part-time", "full-time", "re-send", "pre-pay", "on-line",
            "hello", "thank", "please", "booking", "number", "reference", "ticket",
            "details", "contact", "service", "support", "travel", "agency", "cancel",
            "refund", "update", "change", "status", "confirm", "regards", "thanks",
            "whatsapp", "mobile", "phone"
        }
        
        candidates = []
        for m in matches:
            if m.lower() in ignore_words:
                continue
            
            # Filter out likely phone numbers (Pure digits >= 11 chars)
            if m.isdigit() and len(m) >= 11:
                continue

            if not m.isalpha(): # Contains at least one number or symbol -> STRONG
                 candidates.append((m, "STRONG"))
            elif m.isupper(): # All caps words might be codes -> WEAK
                 candidates.append((m, "WEAK"))
        
        return candidates

    def extract_emails_regex(self, text):
        """Extract email addresses using Regex."""
        return re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)

    def is_agency_email(self, email):
        """
        Check if an email address belongs to an OTA or Agency proxy.
        """
        if not email: return False
        
        email_lower = email.lower()
        agency_domains = [
            "viator.com", "getyourguide.com", "expedia.com", "booking.com", 
            "tripadvisor.com", "headout.com", "bokun.io", "check24.de", 
            "airbnb.com", "agoda.com", "klook.com", "tui.com", "ctrip.com",
            "musement.com", "civitatis.com", "tiqets.com"
        ]
        
        # Check domain
        domain = email_lower.split('@')[-1]
        if any(d in domain for d in agency_domains):
            return True
            
        # Check common proxy patterns
        if "guest" in domain or "proxy" in domain or "marketplace" in domain:
            return True
            
        return False

    def find_booking_strictly(self, message_text, sender_email=None, sender_phone=None, ai_extracted_data=None):
        """
        Strict Lookup Order as requested:
        1. Booking Number (AI Extracted)
        2. Booking Number (in text)
        3. Email (AI Extracted)
        4. Email (in text)
        5. Sender Email
        6. Phone (AI Extracted)
        7. Sender Phone (PRIORITY for WhatsApp)
        """
        logging.info("Starting Strict Lookup...")
        
        # PRIORITIZE SENDER PHONE FOR WHATSAPP
        # If we have a sender phone (WhatsApp source), check it IMMEDIATELY if no explicit booking number is in text.
        # This solves the issue where valid customers are treated as new Leads because regex failed or text was vague.
        if sender_phone and not self.extract_booking_numbers_regex(message_text):
             logging.info(f"WhatsApp Source Detected: Checking Sender Phone First: {sender_phone}")
             rec = self.find_booking_by_contact(phone=sender_phone)
             if rec:
                 logging.info(f"Found booking by Sender Phone (Priority): {sender_phone}")
                 return rec

        # 0. AI Extracted Booking Number (HIGHEST PRIORITY)
        if ai_extracted_data:
            ai_booking_nr = ai_extracted_data.get('Booking Nr.')
            if ai_booking_nr:
                logging.info(f"Checking AI Extracted Booking Nr: {ai_booking_nr}")
                rec = self.find_booking_by_number(ai_booking_nr)
                if rec:
                    logging.info(f"Found booking by AI Booking Nr: {ai_booking_nr}")
                    # Update email if needed
                    if sender_email:
                        self._link_email_if_needed(rec, sender_email)
                    return rec
                else:
                     logging.warning(f"AI Extracted Booking Nr '{ai_booking_nr}' NOT found in DB.")

        # 1. Booking Number in Text
        candidates = self.extract_booking_numbers_regex(message_text)
        
        # NOTE: We DO NOT block fallback if booking number is not found.
        # User might mention a booking number that is wrong, but their phone/email is correct.
        
        for cand, confidence in candidates:
            logging.info(f"Checking Booking Nr ({confidence}): {cand}")
            rec = self.find_booking_by_number(cand)
            if rec:
                logging.info(f"Found booking by Number in text: {cand}")
                if sender_email:
                    self._link_email_if_needed(rec, sender_email)
                return rec
            else:
                # --- VIATOR BR- PREFIX RETRY LOGIC ---
                if confidence == "STRONG" and cand.isdigit() and not cand.startswith("BR-"):
                     viator_cand = f"BR-{cand}"
                     logging.info(f"Retrying with Viator Prefix: {viator_cand}")
                     rec_viator = self.find_booking_by_number(viator_cand)
                     if rec_viator:
                         logging.info(f"Found booking with Viator Prefix: {viator_cand}")
                         return rec_viator
                # -------------------------------------

                if confidence == "STRONG":
                    logging.warning(f"Strong Booking ID candidate '{cand}' NOT found in DB. Continuing to search by contact info...")

        # 2. Email (AI Extracted)
        if ai_extracted_data:
            ai_email = ai_extracted_data.get('Customer personal email')
            if ai_email and ai_email.lower() != (sender_email or "").lower():
                 logging.info(f"Checking AI Extracted Email: {ai_email}")
                 rec = self.find_booking_by_contact(email=ai_email)
                 if rec:
                     logging.info(f"Found booking by AI Extracted Email: {ai_email}")
                     return rec

        # 3. Email in Text
        email_candidates = self.extract_emails_regex(message_text)
        for email in email_candidates:
            if email.lower() == (sender_email or "").lower():
                continue # Skip if same as sender (will check later)
            
            if self.is_agency_email(email):
                logging.info(f"Skipping Agency Email in text: {email}")
                continue

            logging.info(f"Checking Email candidate from text: {email}")
            rec = self.find_booking_by_contact(email=email)
            if rec:
                logging.info(f"Found booking by Email in text: {email}")
                return rec

        # 4. Sender Email (Only if NOT phone)
        if sender_email:
            # Check if it's actually a phone number (WhatsApp)
            is_phone = sender_email.replace('+', '').isdigit() and len(sender_email) > 6
            
            if is_phone:
                logging.info(f"Skipping Sender Email Check (It's a phone number: {sender_email})")
            elif self.is_agency_email(sender_email):
                logging.warning(f"Sender Email {sender_email} is Agency/Proxy. Skipping direct lookup to avoid false match.")
            else:
                logging.info(f"Checking Sender Email: {sender_email}")
                rec = self.find_booking_by_contact(email=sender_email)
                if rec:
                    logging.info(f"Found booking by Sender Email: {sender_email}")
                    return rec

        # 5. Phone (AI Extracted)
        if ai_extracted_data:
            ai_phone = ai_extracted_data.get('Customer Phone')
            if ai_phone:
                 logging.info(f"Checking AI Extracted Phone: {ai_phone}")
                 rec = self.find_booking_by_contact(phone=ai_phone)
                 if rec:
                     logging.info(f"Found booking by AI Extracted Phone: {ai_phone}")
                     return rec

        # 6. Sender Phone
        if sender_phone:
            logging.info(f"Checking Sender Phone: {sender_phone}")
            rec = self.find_booking_by_contact(phone=sender_phone)
            if rec:
                logging.info(f"Found booking by Sender Phone: {sender_phone}")
                return rec
                
        logging.info("Strict Lookup Failed.")
        return None

    def _link_email_if_needed(self, rec, sender_email):
        """Helper to link sender email to booking if safe."""
        if not rec or 'fields' not in rec:
            logging.warning(f"Cannot link email: Record {rec.get('id', 'unknown')} is missing 'fields' data.")
            return
        
        # Check if sender_email is actually a phone number (WhatsApp)
        is_phone = sender_email.replace('+', '').isdigit() and len(sender_email) > 6
        
        if is_phone:
             current_phone = self.get_field_value(rec['fields'], FieldIds.CUSTOMER_PHONE)
             # Only update phone if empty
             if not current_phone:
                 logging.info(f"Linking Booking {rec['id']} to new phone: {sender_email}")
                 try:
                    self.update_booking_record(rec['id'], {FieldIds.CUSTOMER_PHONE: sender_email}, table_name=rec.get('table_name'))
                    rec['fields'][FieldIds.CUSTOMER_PHONE] = sender_email
                 except Exception as e:
                    logging.error(f"Failed to link phone: {e}")
             return

        # Email Linking Logic
        current_email = self.get_field_value(rec['fields'], FieldIds.CUSTOMER_PERSONAL_EMAIL)
        is_sender_agency = self.is_agency_email(sender_email)
        should_update = False
        
        if not current_email:
            should_update = True
        elif not is_sender_agency:
            if current_email.lower().strip() != sender_email.lower().strip():
                should_update = True
        
        if should_update:
            logging.info(f"Linking Booking {rec['id']} to new email: {sender_email}")
            try:
                self.update_booking_record(rec['id'], {FieldIds.CUSTOMER_PERSONAL_EMAIL: sender_email}, table_name=rec.get('table_name'))
                rec['fields'][FieldIds.CUSTOMER_PERSONAL_EMAIL] = sender_email
            except Exception as e:
                logging.error(f"Failed to link email: {e}")


    def _generate_phone_variants(self, phone):
        """
        Generate variations of a phone number to improve search hit rate.
        Handles International formats robustly.
        """
        if not phone:
            return []
            
        variants = set()
        # 1. Clean completely (Keep only digits and +)
        raw_clean = re.sub(r'[^\d+]', '', str(phone))
        variants.add(raw_clean)
        
        # 2. Digits Only Version (No +)
        digits_only = re.sub(r'\D', '', raw_clean)
        variants.add(digits_only)
        
        # 3. Add '+' version if missing
        if not raw_clean.startswith('+'):
             variants.add('+' + digits_only)

        # 4. Handle Egypt Specifics (Legacy Support)
        if digits_only.startswith('20') and len(digits_only) > 10:
             variants.add('0' + digits_only[2:]) # 2010... -> 010...
        elif digits_only.startswith('01') and len(digits_only) == 11:
             variants.add('20' + digits_only[1:]) # 010... -> 2010...
             variants.add('+20' + digits_only[1:]) # 010... -> +2010...

        # 5. Handle France Specifics (+33)
        # 33651812108 -> 0651812108 (Standard Local)
        if digits_only.startswith('33') and len(digits_only) == 11:
             variants.add('0' + digits_only[2:]) 
        
        # 6. Handle UK Specifics (+44)
        # 447776747623 -> 07776747623
        if digits_only.startswith('44') and len(digits_only) >= 11:
             variants.add('0' + digits_only[2:])

        # 7. Last Resort: Partial Match Strings (Last 8-9 digits)
        # Useful for cases where country code is confusing or missing
        if len(digits_only) > 8:
             variants.add(digits_only[-9:]) # Last 9 digits
             variants.add(digits_only[-8:]) # Last 8 digits

        return list(variants)

    def find_booking_by_contact(self, email=None, phone=None, booking_nr=None):
        if not email and not phone and not booking_nr:
            return None
        try:
            # 1. Search Main Table
            main_conditions = []
            if email:
                main_conditions.append(f"{{Customer personal email}}='{email}'")
                main_conditions.append(f"{{Customer Email}}='{email}'")
            
            if phone:
                phone_variants = self._generate_phone_variants(phone)
                logging.info(f"Searching Phone Variants: {phone_variants}")
                
                # ROBUST SEARCH: Use SEARCH() function for partial matches and ignore formatting
                db_phone_clean = "SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({Customer Phone}, ' ', ''), '-', ''), '+', '')"
                
                for p in phone_variants:
                    # Standard Exact Match (for safety - against raw field)
                    main_conditions.append(f"{{Customer Phone}}='{p}'")
                    
                    # Robust Search (Ignore spaces/dashes in DB field by using SEARCH on cleaned field)
                    p_clean = p.replace('+', '').replace(' ', '').replace('-', '')
                    
                    if len(p_clean) > 5: # Only search if we have enough digits to be specific
                         # Search for the clean number within the clean DB field
                         main_conditions.append(f"SEARCH('{p_clean}', {db_phone_clean})")
                         
                         # SUPER ROBUST: Search for last 6-8 digits
                         # Helpful for "+33 6..." vs "336..." vs "06..."
                         if len(p_clean) >= 8:
                             last_8 = p_clean[-8:]
                             main_conditions.append(f"SEARCH('{last_8}', {db_phone_clean})")
                         elif len(p_clean) >= 6:
                             # For shorter numbers, try last 6
                             last_6 = p_clean[-6:]
                             main_conditions.append(f"SEARCH('{last_6}', {db_phone_clean})")

            
            if booking_nr:
                main_conditions.append(f"{{Booking Nr.}}='{booking_nr}'")
            
            if main_conditions:
                formula = "OR(" + ",".join(main_conditions) + ")"
                records = self.table.all(formula=formula)
                
                if records:
                    # Handle Multiple Bookings:
                    # If user has multiple bookings, we should ideally check which one is relevant.
                    # For now, we return the list of all found bookings in a wrapper or pick the most relevant (future date).
                    # But the current system expects a single 'rec'.
                    # FIX: We will sort them by Date and pick the most relevant one, 
                    # OR we can aggregate them if needed. 
                    # Let's try to pick the upcoming one or the most recently created.
                    
                    # Sort by 'Date' field (Descending) to get latest
                    # Assuming 'Date' field exists and is YYYY-MM-DD
                    # If we need to return ALL bookings context, we need to modify how we return data.
                    # The current architecture seems to rely on returning ONE record.
                    # We will attach 'other_bookings' to the record.
                    
                    sorted_records = sorted(records, key=lambda r: r['fields'].get('Date', '0000-00-00'), reverse=True)
                    rec = sorted_records[0]
                    rec['table_name'] = self.config['airtable']['tables']['main_list']
                    
                    if len(sorted_records) > 1:
                        rec['other_related_bookings'] = sorted_records[1:]
                        logging.info(f"Found {len(sorted_records)} bookings for this contact. Using most recent: {rec['id']}")
                        
                    return rec
            
            # 2. Search Leads Table
            if self.leads_table:
                leads_conditions = []
                if email:
                    leads_conditions.append(f"{{Customer Email}}='{email}'")
                if phone:
                    phone_variants = self._generate_phone_variants(phone) if phone else []
                    
                    # Same cleaned DB field formula for Leads
                    db_phone_clean = "SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({Customer Phone}, ' ', ''), '-', ''), '+', '')"
                    
                    for p in phone_variants:
                        leads_conditions.append(f"{{Customer Phone}}='{p}'")
                        # Add Robust Search for Leads too
                        p_clean = p.replace('+', '').replace(' ', '').replace('-', '')
                        
                        if len(p_clean) > 5:
                             leads_conditions.append(f"SEARCH('{p_clean}', {db_phone_clean})")
                             
                             if len(p_clean) >= 8:
                                 last_8 = p_clean[-8:]
                                 leads_conditions.append(f"SEARCH('{last_8}', {db_phone_clean})")
                             elif len(p_clean) >= 6:
                                 last_6 = p_clean[-6:]
                                 leads_conditions.append(f"SEARCH('{last_6}', {db_phone_clean})")
                
                if leads_conditions:
                    formula_leads = "OR(" + ",".join(leads_conditions) + ")"
                    lead_records = self.leads_table.all(formula=formula_leads)
                    if lead_records:
                        logging.info(f"Found booking in Leads Table for {email or phone}")
                        rec = lead_records[0]
                        rec['table_name'] = LEADS_TABLE_NAME
                        return rec
            
            return None
        except Exception as e:
            logging.error(f"Error finding booking by contact: {e}")
            return None

    def extract_contact_from_text(self, history_text, body):
        """Extract email and phone from text using AI."""
        prompt = f"""
        Extract contact information from the text below.
        Return JSON with keys: "email", "phone".
        If not found, value should be null.
        Text:
        {history_text}
        {body}
        """
        result_json = self.query_ai(prompt, system_role="analyzer")
        try:
             if "```json" in result_json:
                result_json = result_json.split("```json")[1].split("```")[0]
             elif "```" in result_json:
                result_json = result_json.split("```")[1].split("```")[0]
             return json.loads(result_json.strip())
        except:
            return {}

    def get_booking_record_from_history(self, history_text):
        prompt = f'Extract only booking number as JSON with key "Booking Nr.":\\n{history_text}'
        out = self.query_ai(prompt, system_role="analyzer")
        try:
            if "```json" in out:
                out = out.split("```json")[1].split("```")[0]
            elif "```" in out:
                out = out.split("```")[1].split("```")[0]
            data = json.loads(out.strip())
            booking_nr = data.get("Booking Nr.")
            if booking_nr:
                rec = self.find_booking_by_number(booking_nr)
                return rec
            
            # Try to find by contact if booking number not found
            contacts = self.extract_contact_from_text(history_text, "")
            email = contacts.get("email")
            phone = contacts.get("phone")
            if email or phone:
                return self.find_booking_by_contact(email, phone)
                
            return None
        except Exception:
            return None

    def check_hotel_transfer_fee(self, hotel_name, trip_name):
        """
        Check if the Hotel + Trip combination requires an extra transfer fee.
        Based on GAS logic: Table has columns named after Trips. Values are Hotels.
        Returns: None (if no fee/not found) or a Tuple (Fee Amount/Details, Notes)
        """
        if not self.hotel_transfer_table or not hotel_name or not trip_name:
            return None

        try:
            records = self.hotel_transfer_table.all() 
            
            hotel_lower = hotel_name.lower()
            trip_lower = trip_name.lower()
            
            for rec in records:
                fields = rec.get('fields', {})
                
                # Iterate over all fields to find the Trip Column
                for key, val in fields.items():
                    # Check if Column Name matches Trip Name (Fuzzy)
                    # We ignore standard fields like 'ID', 'Created', etc.
                    if key.lower() in ['name', 'notes', 'id']: 
                        continue
                        
                    if trip_lower in key.lower() or key.lower() in trip_lower:
                        # Found a potential Trip Column
                        # Check if the Value (Hotel Name) matches User's Hotel
                        if isinstance(val, list):
                            # Handle Multi-select or Linked records
                            for item in val:
                                if hotel_lower in str(item).lower() or str(item).lower() in hotel_lower:
                                    return fields
                        else:
                            val_str = str(val).lower()
                            if hotel_lower in val_str or val_str in hotel_lower:
                                return fields
            
            return None
        except Exception as e:
            logging.error(f"Error checking hotel transfer fee: {e}")
            return None

    def _get_real_booking_status(self, fields):
        """
        Determine the ACTUAL status of the booking based on CXL Date and Status Field.
        Logic:
        1. If CXL Date (fldDeFCFR74boCvJe) has value -> CANCELLED
        2. If Status (fldqYNM9cO0gP0j0y) contains "Cancel" -> CANCELLED
        3. Else -> ACTIVE
        """
        cxl_date = self.get_field_value(fields, FieldIds.CXL_DATE)
        status_text = self.get_field_value(fields, FieldIds.BOOKING_STATUS) or ""
        
        if cxl_date:
            return "CANCELLED"
            
        if status_text and "cancel" in status_text.lower():
            return "CANCELLED"
            
        # If fields are empty or status is not 'cancel', it is ACTIVE
        return "ACTIVE"

    def generate_smart_reply(self, history_text, kb_context, latest_message_body, fallback_email=None, fallback_phone=None, has_attachments=False, booking_record=None, **kwargs):
        # 1. Identify Booking Record First (Essential for context)
        rec = booking_record
        if not rec:
            rec = self.find_booking_strictly(history_text, sender_email=fallback_email, sender_phone=fallback_phone)
        
        # 2. Check Escalation State
        is_already_escalated = False
        if rec and rec.get("fields"):
             # NEW: Check dedicated Status Field
             chat_status = self.get_field_value(rec["fields"], FieldIds.AI_CHAT_STATUS)
             
             if chat_status == "ESCALATED":
                 is_already_escalated = True
             elif chat_status == "RESOLVED":
                 is_already_escalated = False
             
             # Fallback: Check log ONLY if status field is empty (migration support)
             elif not chat_status:
                 chat_log = self.get_field_value(rec["fields"], FieldIds.AI_CHAT_LOG) or ""
                 if "[STATUS: ESCALATED]" in chat_log and "[STATUS: RESOLVED]" not in chat_log:
                     is_already_escalated = True

        # Flag to distinguish real bookings from Leads
        is_unverified_lead = False
        
        if rec and rec.get("fields"):
            # Check if this is a LEAD record (Potential Customer / Unverified)
            if rec.get('table_name') == LEADS_TABLE_NAME:
                is_unverified_lead = True
                
        # 3. Classify Intent & Department
        # NOTE: If user is a LEAD (not a confirmed booking), we force intent to "TRIP_INFO_QUERY" or "OTHER"
        # to avoid asking for pickup details or handling complaints about non-existent bookings.
        
        classify_prompt = f"""Classify the user's latest message: "{latest_message_body}".
        
        1. DETERMINE INTENT (Choose one):
        - PICKUP_QUERY (Time/Place)
        - TRIP_INFO_QUERY (Price/Details/New Booking)
        - INFO_UPDATE (Sending Passport/Room/Hotel)
        - LOST_ITEM
        - COMPLAINT
        - CANCELLATION
        - FOLLOW_UP
        - TICKET_REQUEST (Asking for tickets, vouchers, or saying ticket link is broken/not working)
        - OTHER

        2. DETERMINE DEPARTMENT (Choose one):
        - OPERATIONS (For Pickup, Lost Item, Info Update, Cancellation, Current Trip Issues)
        - SALES (For New Bookings, Price Inquiries, Add-ons)
        - SUPPORT (For Complaints, General Questions, Feedback, Ticket Issues)

        Output format: "INTENT|DEPARTMENT" (e.g. "PICKUP_QUERY|OPERATIONS")"""
        
        classification_result = self.query_ai(classify_prompt, system_role="analyzer").strip()
        
        if "|" in classification_result:
            kind, department = classification_result.split("|", 1)
            kind = kind.strip()
            department = department.strip()
        else:
            kind = classification_result
            department = "SUPPORT" # Default
            
        # OVERRIDE FOR LEADS: If we only have a Lead record (no confirmed booking), treat as SALES/INQUIRY
        if is_unverified_lead:
             logging.info("User is a Lead (No Confirmed Booking). Forcing intent to TRIP_INFO_QUERY/SALES context.")
             if kind in ["PICKUP_QUERY", "COMPLAINT", "CANCELLATION", "LOST_ITEM", "TICKET_REQUEST"]:
                 # If a Lead asks about pickup, it's likely a confusion or they are asking about a *potential* pickup.
                 pass 
             
             # Ensure Department is Sales/Support
             if department == "OPERATIONS":
                 department = "SALES"

        # --- TICKET REQUEST HANDLING ---
        # If user is asking for tickets and has a valid booking, process it immediately.
        if kind == "TICKET_REQUEST" and not is_unverified_lead and rec:
            logging.info("Detected TICKET_REQUEST. Checking attachments...")
            ticket_reply, success = self.process_ticket_request(rec)
            
            # If successfully retrieved tickets, return immediately
            # If failed (escalated), we can either return immediately or let AI add some fluff.
            # Returning immediately is safer to ensure the exact links are sent without AI hallucination.
            return ticket_reply
        
        # 3. Gather Context
        booking_details_str = "No Booking Details Found."
        trip_name = None
        agency = "FTS Travels"
        past_conversations = "No previous conversation logged."
        gyg_context = "" # Initialize here to prevent UnboundLocalError
        
        # Flag to distinguish real bookings from Leads
        # is_unverified_lead is already set above before classification
        
        if rec and rec.get("fields"):
            # Check if this is a LEAD record (Potential Customer / Unverified)
            if rec.get('table_name') == LEADS_TABLE_NAME:
                # is_unverified_lead = True # Set earlier
                raw_fields = rec.get("fields", {})
                
                # Format Lead Details nicely for AI
                lead_context = {
                    "Status": "Potential Customer (Lead / Inquiry)",
                    "Customer Name": self.get_field_value(raw_fields, LeadFieldIds.CUSTOMER_NAME) or "Guest",
                    "Phone": self.get_field_value(raw_fields, LeadFieldIds.CUSTOMER_PHONE),
                    "Email": self.get_field_value(raw_fields, LeadFieldIds.CUSTOMER_EMAIL),
                    "Last Interaction": self.get_field_value(raw_fields, LeadFieldIds.LAST_INTERACTION),
                    "Interested Trip": self.get_field_value(raw_fields, LeadFieldIds.INTERESTED_TRIP)
                }
                booking_details_str = json.dumps(lead_context, indent=2, ensure_ascii=False)
                
                # IMPORTANT: For Leads, we need to set 'agency' to something generic so Web Search is enabled if needed
                agency = "FTS Travels" 
                
            else:
                raw_fields = rec["fields"]
                
                # --- ROBUST CONTEXT BUILDER (MAPPING ID -> NAME) ---
                clean_fields = {}
                for key, value in raw_fields.items():
                    # Determine ID and Name regardless of what Key is (ID or Name)
                    if key.startswith('fld'):
                        f_id = key
                        f_name = ID_TO_READABLE_NAME.get(key, key)
                    else:
                        f_name = key
                        f_id = NAME_TO_ID.get(key, key) # Best effort ID lookup

                    # Exclude Financials
                    if f_id in FINANCIAL_FIELDS:
                        continue
                    
                    # Format Date Trip
                    if f_id == FieldIds.DATE_TRIP:
                         _, val = self.get_corrected_trip_date(value)
                         clean_fields[f_name] = val
                    
                    # Special Logic for Guide -> Tour Language
                    elif f_id == FieldIds.GUIDE:
                         lang_code = str(value).strip().upper() if value else "E"
                         # Map codes to full names
                         lang_map = {
                             "E": "English", "G": "German", "F": "French", "R": "Russian", 
                             "I": "Italian", "S": "Spanish", "P": "Polish", "C": "Czech",
                             "D": "Dutch"
                         }
                         # If it's a single letter, try to map it
                         if len(lang_code) == 1 and lang_code in lang_map:
                             full_lang = lang_map[lang_code]
                         elif not value:
                             full_lang = "English"
                         else:
                             full_lang = str(value)
                         
                         clean_fields[f_name] = full_lang

                    else:
                         clean_fields[f_name] = value

            # Extract key fields for logic
            # Only extract if NOT unverified lead (to avoid confusing AI with fake data)
            if not is_unverified_lead:
                trip_name = self.get_field_value(raw_fields, FieldIds.TRIP_NAME) or self.get_field_value(raw_fields, FieldIds.REAL_PRODUCT_NAME)
                agency = self.get_field_value(raw_fields, FieldIds.AGENCY) or "FTS Travels"
                
                # --- DETERMINE REAL BOOKING STATUS ---
                real_status = self._get_real_booking_status(raw_fields)
                clean_fields["[REAL_BOOKING_STATUS]"] = real_status
                
                # --- DETERMINE COMPANY WHATSAPP NUMBER (Based on Destination) ---
                # Default Number (Hurghada & Others)
                company_whatsapp = "+20 10 30774440"
                
                destination_val = self.get_field_value(raw_fields, FieldIds.DES)
                if destination_val and "sharm" in str(destination_val).lower():
                    company_whatsapp = "+20 10 50995272"
                    
                clean_fields["[Company Support WhatsApp]"] = company_whatsapp
                # -------------------------------------------------------------
                
                booking_details_str = json.dumps(clean_fields, indent=2, ensure_ascii=False)
            
            # Extract Chat Log for Memory (Even for Leads)
            # We need to fetch fields again if it was a lead because 'raw_fields' variable wasn't set in the Lead block above
            current_fields = rec.get("fields", {})
            chat_log_raw = self.get_field_value(current_fields, FieldIds.AI_CHAT_LOG) or self.get_field_value(current_fields, LeadFieldIds.AI_CHAT_LOG)
            if chat_log_raw:
                past_conversations = chat_log_raw
            
            if not is_unverified_lead:
                # Remove Chat Log from 'clean_fields' to avoid duplication in JSON dump
                keys_to_remove = [k for k, v in ID_TO_READABLE_NAME.items() if v == 'AI Chat Log'] + ['AI Chat Log']
                for k in keys_to_remove:
                    clean_fields.pop(k, None)

        # 4. Search Internal Trips Database
        # 4. Web Search (PRIORITY: Source of Truth for Updated Content)
        web_ctx = ""
        need_web = False
        if "TRIP_INFO_QUERY" in kind or "OTHER" in kind or "LOST_ITEM" in kind:
             need_web = True
             
        if need_web:
             # Use Agency Specific Search if Agency is known
             if agency:
                 web_ctx = web_search_tool.search_agency_specific(agency, trip_name or "", latest_message_body)
             else:
                 search_q = f"{agency} {trip_name if trip_name else ''} {latest_message_body}"
                 web_ctx = web_search_tool.search_travel_info(search_q)

        # 5. Internal Trips DB Search (Secondary / Fallback)
        internal_trips_context = ""
        
        # Always search internal DB as well to cross-reference, but Web is priority
        # Strategy A: Use booked trip name if available
        if trip_name:
             search_q = f"{agency} {trip_name} details"
             internal_trips_context = self.search_trips_db(search_q)
        
        # Strategy B: If no booking (Inquiry), search using user's keywords
        elif not trip_name and ("price" in latest_message_body.lower() or "trip" in latest_message_body.lower() or "details" in latest_message_body.lower() or len(latest_message_body) > 5):
             search_q = latest_message_body[:100] 
             internal_trips_context = self.search_trips_db(search_q)
             logging.info(f"Searching Trips DB for Inquiry: {search_q}")

        # --- HEADOUT HANDLING LOGIC ---
        # If agency is Headout, we should prioritize Headout Catalog search
        is_headout = agency and "Headout" in agency
        if is_headout:
            logging.info("Detected Headout Booking. Prioritizing Headout Catalog.")
            # Search Headout Catalog using Trip Name
            headout_query = trip_name
            # If we have a product ID, maybe we can use it? Headout usually relies on names in our DB
            
            # We can reuse the existing 'search_trips_db' but specifically target Headout if needed
            # Or just rely on the fact that search_trips_db searches the whole catalog
            
            # BUT, we should add a specific instruction to the AI to trust Headout details
            # And maybe fetch specific Headout policy if available
            pass # The context is already injected via 'internal_trips_context' and 'headout_catalog_context'
        # ------------------------------

        # --- GYG LOCAL DB SEARCH ---
        # Search if agency is GYG OR if it's a general inquiry
        is_gyg = agency and "GetYourGuide" in agency
        
        # SEARCH LOGIC:
        # 1. If user explicitly asks for a NEW trip (TRIP_INFO_QUERY) -> Use User Message
        # 2. If user is asking about the CURRENT trip (PICKUP_QUERY) -> Use Trip Name
        # 3. INTELLIGENT MATCHING: If the user mentions a specific trip in the message, SEARCH FOR IT regardless of current booking.
        
        should_use_msg_body = "TRIP_INFO_QUERY" in kind or not trip_name
        
        # Heuristic: If message contains "trip" or specific keywords, assume they might be asking about another trip
        # BUT: If they say "my trip" or "this trip", they likely mean the current one.
        msg_lower = latest_message_body.lower()
        keywords = ["trip", "tour", "ticket", "booking"]
        is_about_current = "my " in msg_lower or "this " in msg_lower or "booked" in msg_lower or "current" in msg_lower
        
        has_keywords = any(k in msg_lower for k in keywords)
        
        if len(latest_message_body) > 10 and has_keywords and not is_about_current:
            should_use_msg_body = True
        
        # --- GYG DATA RETRIEVAL (ID MATCH -> MPC MATCH -> TEXT SEARCH) ---
        gyg_direct_match_context = ""
        mpc_found = False
        mpc_name_context = "Not Available" # Default for prompt context
        
        # Default query
        gyg_query = trip_name

        if rec:
            # We are searching for the booked trip. Try to get better name from MPC.
            rec_fields = rec.get('fields', {})
            product_id = self.get_field_value(rec_fields, FieldIds.PRODUCT_ID)
            # Retrieve Option value again (it's also retrieved later, but I need it here)
            opt_val = self.get_field_value(rec_fields, FieldIds.OPTION) or ""
            
            if product_id:
                # 1. PRIORITY: Direct Lookup in GYG JSON by Product ID
                if hasattr(self, 'gyg_data_map') and str(product_id) in self.gyg_data_map:
                    logging.info(f"Direct GYG Match found for ID: {product_id}")
                    match_data = self.gyg_data_map[str(product_id)]
                    gyg_direct_match_context = "**GET YOUR GUIDE SUPPLIER DATA (EXACT ID MATCH):**\n"
                    gyg_direct_match_context += self._format_gyg_trip_for_context(match_data)

                # 2. SECONDARY: MPC Lookup (For Name Correction or Fallback Search)
                mpc_name = self.get_mpc_trip_name(product_id)
                if mpc_name:
                    logging.info(f"MPC Lookup Success: {product_id} -> {mpc_name}")
                    # Construct query: Name + Option
                    # Cleaning option value slightly
                    clean_option = str(opt_val).replace("Option:", "").strip()
                    gyg_query = f"{mpc_name} {clean_option}"
                    mpc_found = True
                    mpc_name_context = mpc_name # Store for prompt injection
        # ----------------------------

        if should_use_msg_body:
            gyg_query = latest_message_body[:100]

        if gyg_direct_match_context:
            gyg_context = gyg_direct_match_context
        elif is_gyg or should_use_msg_body or mpc_found:
            # Prioritize Local DB over Web Search
            gyg_context = self.search_gyg_local_db(gyg_query)
            if not gyg_context:
                # Fallback to Web Search via Manager
                gyg_results = self.gyg_manager.search(gyg_query)
                if gyg_results:
                    gyg_context = "**GET YOUR GUIDE SUPPLIER DATA (WEB SOURCE):**\n"
                    for res in gyg_results:
                        gyg_context += self.gyg_manager.format_trip_details(res) + "\n---\n"
    def get_learned_corrections_context(self, current_message):
        """
        Retrieve relevant corrections based on simple keyword matching or recent history.
        """
        corrections = audit_utils.get_learning_examples()
        if not corrections:
            return ""
            
        # Filter corrections relevant to current context (simple keyword match)
        relevant = []
        msg_lower = current_message.lower()
        
        for c in reversed(corrections): # Newest first
            # Check if original text keywords overlap with current message
            # This is a very basic heuristic. Ideally, we use vector search.
            # For now, just show the last 3 corrections to reinforce general style.
            if len(relevant) < 3:
                relevant.append(c)
        
        if not relevant:
            return ""
            
        context = "**LEARNED CORRECTIONS (FROM PREVIOUS MISTAKES):**\n"
        context += "You have previously made mistakes that were corrected by a human. LEARN from them:\n"
        for i, item in enumerate(relevant):
            context += f"--- Example {i+1} ---\n"
            context += f"AI Proposed: {item['original'][:200]}...\n"
            context += f"Human Corrected: {item['corrected'][:200]}...\n"
            context += f"Rule: Adopt the style/content of the 'Human Corrected' version.\n"
            
        return context

    def generate_smart_reply(self, history_text, kb_context, latest_message_body, fallback_email=None, booking_record=None, has_attachments=False, kind=None):
        """
        Generate AI response with strict adherence to data.
        """
        
        # Get Learned Context
        learned_ctx = self.get_learned_corrections_context(latest_message_body)
        
        # Initialize the master instruction variable
        classification_instruction = ""

        # --- LEAD / MISSING BOOKING INSTRUCTION ---
        lead_instruction = ""
        is_unverified_lead = False
        
        # Logic to check if it's a lead or just missing booking
        if booking_record and booking_record.get('table_name') == LEADS_TABLE_NAME:
             is_unverified_lead = True
        
        # If NO booking found at all OR it is a Lead
        if not booking_record or is_unverified_lead:
             # Check if the user message implies they HAVE a booking or a problem
             user_msg_lower = latest_message_body.lower()
             needs_booking_context = (
                 "booking" in user_msg_lower or "reservation" in user_msg_lower or 
                 "ticket" in user_msg_lower or "voucher" in user_msg_lower or 
                 "driver" in user_msg_lower or "pickup" in user_msg_lower or
                 "cancel" in user_msg_lower or "change" in user_msg_lower or
                 "late" in user_msg_lower or "waiting" in user_msg_lower or
                 "problem" in user_msg_lower or "issue" in user_msg_lower or
                 "refund" in user_msg_lower or "confirmed" in user_msg_lower
             )
             
             if needs_booking_context:
                 lead_instruction = """
                 **NO CONFIRMED BOOKING FOUND**:
                 - The user is asking about a booking/service/problem, but we DO NOT have a confirmed booking record linked to this contact.
                 - **ACTION**: You MUST politely ask for their identification details to find the booking.
                 - **PRIORITY REQUEST**: Ask for **Booking Number** (e.g. BR-XXXX, GYG-XXXX) OR **Email Address** OR **Phone Number** used during booking.
                 - **SAY**: "I apologize, but I couldn't locate your booking with the current contact information. Could you please provide your **Booking Number**, **Email Address**, or the **Phone Number** you used for the reservation? This will help me find your details immediately."
                 """
                 classification_instruction += "\n" + lead_instruction
             else:
                 # General inquiry (Lead)
                 pass # Default behavior for leads (Sales mode)

        # --- FAILED BOOKING LOOKUP ---
        # If the lookup failed but user insists on a booking (even if not explicitly saying "booking")
        # e.g. "I am waiting", "Where is my driver", "My ticket is wrong"
        # We can add a fallback instruction here if booking_record is None
        
        if not booking_record and not is_unverified_lead: # True 'None' means lookup failed completely
             user_msg_lower = latest_message_body.lower()
             needs_booking_context = (
                 "booking" in user_msg_lower or "reservation" in user_msg_lower or 
                 "ticket" in user_msg_lower or "voucher" in user_msg_lower or 
                 "driver" in user_msg_lower or "pickup" in user_msg_lower or 
                 "cancel" in user_msg_lower or "change" in user_msg_lower or 
                 "late" in user_msg_lower or "waiting" in user_msg_lower or 
                 "problem" in user_msg_lower or "issue" in user_msg_lower or 
                 "refund" in user_msg_lower or "confirmed" in user_msg_lower or 
                 "my trip" in user_msg_lower
             )
             
             if needs_booking_context:
                 lead_instruction = """
                 **NO CONFIRMED BOOKING FOUND**:
                 - The user is asking about a booking/service/problem, but we DO NOT have a confirmed booking record linked to this contact.
                 - **ACTION**: You MUST politely ask for their identification details to find the booking.
                 - **PRIORITY REQUEST**: Ask for **Booking Number** (e.g. BR-XXXX, GYG-XXXX) OR **Email Address** OR **Phone Number** used during booking.
                 - **SAY**: "I apologize, but I couldn't locate your booking with the current contact information. Could you please provide your **Booking Number**, **Email Address**, or the **Phone Number** you used for the reservation? This will help me find your details immediately."
                 """
                 classification_instruction += "\n" + lead_instruction

        # HUMAN HANDOVER TRIGGER
        human_handover_instruction = """
        **HUMAN HANDOVER OPTION**:
        - At the end of your reply (unless you are escalating or solving a simple query), 
        - You MAY add a small, polite note: "If you prefer to speak with a human agent, just reply with 'Human'."
        - **ACTION**: IF the user explicitly asks for a human (e.g., "Talk to agent", "Human", "Customer service", "Representative"):
          1. Start your reply with `[ESCALATE]`.
          2. Say: "I have forwarded your request to our customer service team. An agent will contact you via WhatsApp shortly."
          3. Do NOT ask for more details. Just confirm the handover.
        """
        classification_instruction += "\n" + human_handover_instruction
        
        # --- DRIVER WAITING/DELAY HANDLING ---
        # If user says "ready", "waiting", "where is driver" AND it is close to pickup time
        # The Python code will trigger a webhook.
        # The AI should just be polite and reassuring.
        driver_waiting_instruction = """
        **DRIVER/PICKUP STATUS**:
        - IF the user says "We are ready", "Waiting in lobby", "Where is the driver?":
        - **ACTION**: Acknowledge their message warmly.
        - **SAY**: "Perfect, thank you for letting us know. The driver will be there to meet you shortly."
        - **INFO**: Mention the scheduled pickup time and location from the booking details to reassure them.
        """
        classification_instruction += "\n" + driver_waiting_instruction
        
        # --- PICKUP TIME SOURCE OF TRUTH POLICY ---
        pickup_source_policy = """
        **PICKUP TIME AUTHORITY**:
        - The ONLY source of truth for the confirmed pickup time is the field named 'Pickup Time' in the Booking Details.
        - **CRITICAL**: Do NOT infer, guess, or extract pickup times from the 'Option Name', 'Product Name', or 'Description' fields. These are often generic or incorrect placeholders (e.g., 'Tour starts at 4:00' does NOT mean pickup is at 4:00).
        - **IF 'Pickup Time' field is EMPTY or NULL**:
          - You MUST NOT invent a time.
          - You MUST say: "Your specific pickup time will be determined and sent to you shortly (usually one day before the trip)."
          - You can mention the generic start time if you clearly state it is the "Tour Start Time", not the pickup time.
        - **IF 'Pickup Time' field HAS A VALUE**:
          - Use THAT value as the confirmed pickup time.
        """
        classification_instruction += "\n" + pickup_source_policy

        # -------------------------------
        
        # --- HEADOUT TICKET INSTRUCTION ---
        # Special handling for Headout ticket issues
        headout_instruction = """
        **HEADOUT TICKET POLICY (CRITICAL)**:
        - IF the Agency/Provider is **Headout** (or "Headout Inc"):
        - AND the user is complaining about missing tickets/vouchers:
        - **YOU MUST**:
          1. **Empathize** with the user first (e.g., "I understand your concern about the tickets").
          2. **ADVISE**: Politely ask them to check their voucher/email again, as Headout usually attaches the tickets there.
          3. **DIRECT**: If they still can't find it, tell them to contact **Headout customer services directly** as they are the provider.
          4. **SAY**: "Could you please double-check your voucher? Headout usually sends the tickets directly. If you still can't find them, please get in touch with Headout customer services directly for the fastest assistance."
          5. **DO NOT** say "I will notify operations" for missing Headout tickets.
        """
        
        # Add to system prompt
        classification_instruction += headout_instruction

        # Generate System Instructions
        classification_instruction += """
        You are 'فرح Farah', an intelligent AI Assistant for FTS Travels (Egypt).
        Your role is to help customers with their bookings, answer questions about tours, and solve issues.
        
        **CRITICAL CONTEXT ANALYSIS POLICY**:
        - You MUST analyze the ENTIRE conversation history provided in 'PAST CONVERSATIONS' before replying.
        - **DO NOT** reply based only on the latest message if the previous messages provide essential context.
        - **SCENARIO**: If the user sends "Hello" and then immediately "I have a problem", treat it as one thought: "Hello, I have a problem".
        - **SCENARIO**: If the user sends multiple details in separate messages (e.g., "My name is John", "Room 101", "Pickup tomorrow"), AGGREGATE them before processing.
        - **EXCEPTION**: If the latest message is a BUTTON CLICK (e.g., "Confirm Pickup", "Send Details Now", "Cancel"), prioritize the action associated with that button immediately.
        
        **CRITICAL SPAM/IGNORE POLICY**:
        - You must ONLY ignore messages that are obvious marketing spam (e.g. "Buy SEO", "Cheap viagra", "Win $1000").
        - **NEVER** ignore messages from potential customers, even if they are short like "Hi", "Hello", "Price?", "Tour info".
        - If a message is a greeting or a simple inquiry, **IT IS NOT SPAM**. Treat it as a valid customer interaction.
        - If the sender is 'V...' (Tawk.to Visitor), assume they are a legitimate customer unless the text is 100% spam.

        **ESCALATION & UNKNOWN QUESTIONS POLICY**:
        - IF you cannot answer a question based on the provided context (Web Search or Database):
          1. **DO NOT** make up an answer.
          2. **DO NOT** just say "I don't know".
          3. **INSTEAD, SAY**: "I'm checking this specific detail with our operations team to be 100% sure. I will get back to you shortly with the answer."
          4. **MANDATORY**: If we do NOT have the customer's contact info (Email or Phone), you **MUST** ask for it politely: "Could you please leave your Email or WhatsApp number so we can send you the answer as soon as we have it?"
          5. Start your reply with `[ESCALATE]` to trigger an immediate notification to the team.
        """
        
        rec = booking_record
        chat_log_raw = ""
        trip_name = ""
        agency = ""
        customer_first_name = "Guest" # Default
        
        if rec:
            chat_log_raw = self.get_field_value(rec.get("fields", {}), FieldIds.AI_CHAT_LOG) or ""
            trip_name = self.get_field_value(rec.get("fields", {}), FieldIds.TRIP_NAME) or ""
            agency = self.get_field_value(rec.get("fields", {}), FieldIds.AGENCY) or ""
            
            # Extract First Name for Personalization
            full_name = self.get_field_value(rec.get("fields", {}), FieldIds.CUSTOMER_NAME)
            if full_name:
                customer_first_name = str(full_name).split()[0].title()
            
            # If still default, try Traveler Name
            if customer_first_name == "Guest":
                 traveler_name = self.get_field_value(rec.get("fields", {}), FieldIds.TRAVELER_NAME)
                 if traveler_name:
                     customer_first_name = str(traveler_name).split()[0].title()

        # Initialize missing variables for prompt
        past_conversations = chat_log_raw
        
        # --- CLEAN UP PROPOSED DRAFTS FROM HISTORY ---
        # If we are in learning mode, [PROPOSED_DRAFT] entries might confuse the AI context 
        # because they look like system messages but weren't sent to the user.
        # However, for "Context Awareness", seeing what the AI *thought* it should reply might be useful?
        # NO, usually it causes repetition or hallucination that the user saw the reply.
        # BETTER STRATEGY: Remove [PROPOSED_DRAFT] blocks from 'past_conversations' variable 
        # before passing it to the Prompt.
        
        if "[PROPOSED_DRAFT]" in past_conversations:
            # Simple regex removal or line filtering
            # Remove lines starting with [PROPOSED_DRAFT] and maybe the content following it?
            # Actually, the log format is:
            # [TIMESTAMP] [AI_Learning - System]: [PROPOSED_DRAFT]
            # Reply Content...
            # This is hard to parse reliably with simple replace.
            # But we can try to mark them clearly in the prompt as "INTERNAL THOUGHTS (NOT SENT)"
            pass 
            # Decided NOT to remove, but to instruct AI to treat them as internal thoughts.
            # OR better: Filter them out to avoid confusion.
            # Let's filter lines containing [PROPOSED_DRAFT] and [AI_Learning - System]
            
            clean_lines = []
            lines = past_conversations.split('\n')
            skip_next = False
            for line in lines:
                if "AI_Learning" in line or "PROPOSED_DRAFT" in line:
                    continue # Skip the header
                # We might want to skip the body too? 
                # The body is just text. Hard to know when it ends.
                # So maybe just keeping them but labeling them is safer.
                clean_lines.append(line)
            
            # For now, let's leave it raw but add a system instruction to ignore them.
            
        booking_details_str = "No Booking Details Found."
        mpc_name_context = ""
        web_ctx = kb_context or ""
        gyg_context = ""
        internal_trips_context = ""
        
        # Default Metadata
        department = "SUPPORT"
        
        # --- CLASSIFY INQUIRY TYPE ---
        # This logic is critical for Operations/Notifications
        if not kind:
            # Simple keyword-based fallback if LLM classification wasn't done or failed
            msg_lower = latest_message_body.lower()
            if "cancel" in msg_lower or "refund" in msg_lower:
                kind = "CANCELLATION"
                department = "SUPPORT"
            elif "pickup" in msg_lower or "time" in msg_lower or "when" in msg_lower or "where" in msg_lower:
                kind = "PICKUP_QUERY"
                department = "OPERATIONS"
            elif "lost" in msg_lower or "left" in msg_lower or "forgot" in msg_lower or "missing" in msg_lower:
                kind = "LOST_ITEM"
                department = "OPERATIONS"
            elif "complain" in msg_lower or "issue" in msg_lower or "problem" in msg_lower or "bad" in msg_lower or "angry" in msg_lower:
                kind = "COMPLAINT"
                department = "QUALITY"
            elif "details" in msg_lower or "info" in msg_lower or "include" in msg_lower or "price" in msg_lower:
                kind = "TRIP_INFO_QUERY"
                department = "SALES"
            elif "update" in msg_lower or "change" in msg_lower or "room" in msg_lower or "hotel" in msg_lower:
                kind = "INFO_UPDATE"
                department = "OPERATIONS"
            elif "follow" in msg_lower or "status" in msg_lower or "check" in msg_lower:
                kind = "FOLLOW_UP"
                department = "SUPPORT"
            else:
                kind = "GENERAL"
                department = "SUPPORT"
        
        # --- SMART CLASSIFICATION INSTRUCTION ---
        # We also want the LLM to confirm/refine this in its response meta-data
        classification_instruction += """
        **INQUIRY CLASSIFICATION TASK**:
        - You MUST classify the user's intent into ONE of these categories:
          1. **CANCELLATION**: User wants to cancel or asks about refund.
          2. **PICKUP_QUERY**: Asking about pickup time, location, or driver.
          3. **COMPLAINT**: Expressing dissatisfaction, reporting an issue/problem.
          4. **TRIP_INFO_QUERY**: Asking about trip details, price, inclusions, or availability (Sales).
          5. **FOLLOW_UP**: Asking for status of a previous request.
          6. **INFO_UPDATE**: Providing new details (Room number, passport, etc.).
          7. **LOST_ITEM**: Reporting a lost, left, or missing item (e.g., phone, bag) on the bus or trip.
          8. **URGENT_ISSUE**: A critical problem requiring immediate intervention (e.g., stranded, medical, accident).
          9. **GENERAL**: Greeting, thanks, or unclear.
          10. **TEST_SCENARIO**: Testing the system.
          11. **OTHER**: Anything else.
        
        **LANGUAGE DETECTION**:
        - You MUST detect the language of the user's latest message.
        - **OUTPUT FORMAT**: You must append the following tags at the VERY END of your response (invisible to user):
          `[INTENT: CATEGORY]`
          `[DEPT: DEPARTMENT]`
          `[LANG: LanguageName]` (e.g., English, German, Arabic)
          `[TRANS: English translation of user message]`
        
        - **DEPARTMENTS**:
          - CANCELLATION -> SUPPORT
          - PICKUP_QUERY -> OPERATIONS
          - COMPLAINT -> QUALITY
          - TRIP_INFO_QUERY -> SALES
          - INFO_UPDATE -> OPERATIONS
          - LOST_ITEM -> OPERATIONS
          - URGENT_ISSUE -> QUALITY
          - FOLLOW_UP -> SUPPORT
          - GENERAL -> SUPPORT
        """

        if rec:
            import json
            # Use JSON dump for booking details
            booking_details_str = json.dumps(rec.get('fields', {}), indent=2, default=str)
            
            # --- MULTI-BOOKING CONTEXT ---
            if rec.get('other_related_bookings'):
                other_books = rec['other_related_bookings']
                booking_details_str += "\n\n=== [IMPORTANT] OTHER LINKED BOOKINGS FOUND ===\n"
                for i, ob in enumerate(other_books):
                    booking_details_str += f"\n-- Booking #{i+2} --\n"
                    booking_details_str += json.dumps(ob.get('fields', {}), indent=2, default=str)
                booking_details_str += "\n============================================\n"

        # Check Escalation State
        is_already_escalated = False
        if rec and rec.get("fields"):
             chat_status = self.get_field_value(rec["fields"], FieldIds.AI_CHAT_STATUS)
             if chat_status == "ESCALATED":
                 is_already_escalated = True
             elif chat_status == "RESOLVED":
                 is_already_escalated = False
             elif not chat_status and chat_log_raw:
                 if "[ESCALATED]" in chat_log_raw or "[Admin]" in chat_log_raw:
                     if "[RESOLVED]" not in chat_log_raw.split("[ESCALATED]")[-1]:
                         is_already_escalated = True
        
        # Determine Trip Type & Urgency & Past Status
        trip_name_lower = trip_name.lower() if trip_name else ""
        
        option_val = ""
        addons_text = ""
        addons_multi = []
        
        if rec and rec.get("fields"):
            option_val = self.get_field_value(rec["fields"], FieldIds.OPTION) or ""
            addons_text = self.get_field_value(rec["fields"], FieldIds.ADD_ONS_TEXT) or ""
            addons_multi = self.get_field_value(rec["fields"], FieldIds.ADD_ONS_MULTI) or []
            
        option_lower = str(option_val).lower()
        addons_combined = (str(addons_text) + " " + str(addons_multi)).lower()
        
        # Default: Assume Transfer is included unless proven otherwise
        is_transfer_trip = True
        
        # LOGIC:
        # A trip HAS transfer if ANY of the following is true:
        # 1. Option explicitly says "pickup", "transfer", "from hotel".
        # 2. Add-ons explicitly mention "transfer", "pickup", "transport".
        # 3. Trip Name implies guided tour with transport (e.g. "bus", "safari", "boat", "tour").
        #
        # A trip is NO TRANSFER (Ticket Only) if:
        # 1. Option explicitly says "ticket only", "no transfer", "meet at".
        # 2. AND Add-ons do NOT mention transfer.
        
        has_transfer_keywords = (
            "pickup" in option_lower or "transfer" in option_lower or "from hotel" in option_lower or 
            "transport" in option_lower or "with guide" in option_lower or "guided tour" in option_lower or
            "transfer" in addons_combined or "pickup" in addons_combined or "transport" in addons_combined
        )
        
        no_transfer_keywords = (
            "ticket only" in option_lower or "no transfer" in option_lower or 
            "meet at" in option_lower or "without transfer" in option_lower or 
            "entry ticket" in option_lower or "admission" in option_lower
        )
        
        if has_transfer_keywords:
            is_transfer_trip = True
        elif no_transfer_keywords:
            is_transfer_trip = False
        else:
            # Fallback to Trip Name Analysis if Option/Addons are neutral
            if 'qr' in trip_name_lower or 'ticket' in trip_name_lower or 'meeting point' in trip_name_lower or agency == 'Tiqets':
                is_transfer_trip = False
            else:
                # If it's a "Tour" or "Safari" or "Diving", it usually has transfer
                is_transfer_trip = True
            
        is_urgent_trip = False
        is_past_trip = False
        trip_date_obj = None
        
        if rec and rec.get("fields"):
             raw_date = self.get_field_value(rec["fields"], FieldIds.DATE_TRIP)
             if raw_date:
                 trip_date_obj, _ = self.get_corrected_trip_date(raw_date)
                 if trip_date_obj:
                     now_cairo = datetime.utcnow() + CAIRO_OFFSET
                     days_diff = (trip_date_obj - now_cairo.date()).days
                     
                     if days_diff < 0:
                         is_past_trip = True
                     elif days_diff <= 1: # Today or Tomorrow
                         is_urgent_trip = True

        # Past Trip Instruction
        # MODIFIED: Allow complaints/issues AND positive feedback for past trips
        past_trip_instruction = ""
        msg_lower = latest_message_body.lower()
        is_complaint = "issue" in msg_lower or "complaint" in msg_lower or "problem" in msg_lower or "refund" in msg_lower or "didn't show" in msg_lower or "contacted" in msg_lower
        
        # Check for positive feedback / review
        # Heuristic: "loved it", "great", "amazing", "wonderful", "enjoyed", "best", "thanks", "thank you"
        positive_keywords = ["loved it", "great", "amazing", "wonderful", "enjoyed", "best trip", "excellent", "perfect"]
        is_positive_review = any(pk in msg_lower for pk in positive_keywords) and len(latest_message_body) < 200 # Short message usually
        
        if is_past_trip:
             if is_complaint:
                 past_trip_instruction = f"""
                 **CRITICAL ALERT - PAST TRIP ISSUE**:
                 - The trip date ({trip_date_obj}) was in the past, and the user is reporting an ISSUE/COMPLAINT.
                 - **ACTION**: Acknowledge the issue professionally. Do NOT ask if they want to make a new booking.
                 - **SAY**: "I understand you are contacting us regarding an issue with the trip on {trip_date_obj}. I will escalate this to our operations team immediately to investigate what happened."
                 - Try to resolve if possible or assure escalation.
                 """
             elif is_positive_review:
                 # Check GYG Rating status to customize the ask
                 has_gyg_rating = False
                 if rec:
                     gyg_rating_val = self.get_field_value(rec.get("fields", {}), FieldIds.GYG_RATING)
                     if gyg_rating_val:
                         has_gyg_rating = True
                 
                 # Determine Review Platform based on Agency
                 review_ask = ""
                 if agency == "GetYourGuide":
                     if not has_gyg_rating:
                         review_ask = "- **REQUEST**: Please kindly ask them to leave a review on **GetYourGuide**."
                     else:
                         # Already rated on GYG, just say thanks. Do NOT ask for TripAdvisor/Google to avoid annoyance.
                         review_ask = "- **NOTE**: They already rated on GetYourGuide. Just thank them warmly. Do NOT ask for another review."
                 else:
                     # Standard ask for others
                     review_ask = "- **SUGGESTION**: Politely ask them to leave a review on TripAdvisor or Google if they haven't already."

                 past_trip_instruction = f"""
                 **CRITICAL ALERT - POSITIVE REVIEW (PAST TRIP)**:
                 - The user is sending POSITIVE FEEDBACK ("{latest_message_body}") about a past trip ({trip_date_obj}).
                 - **ACTION**: Do NOT ask "Are you inquiring about a past trip?".
                 - **SAY**: "Thank you so much! We are thrilled to hear you enjoyed your trip to {trip_name}. It was a pleasure having you with us!"
                 {review_ask}
                 - **SOFT SELL**: "We hope to see you again on your next visit to Egypt!"
                 """
             else:
                 past_trip_instruction = f"""
                 **CRITICAL ALERT - PAST TRIP**:
                 - The trip date ({trip_date_obj}) is in the PAST (Today is {now_cairo.strftime('%Y-%m-%d')}).
                 - **ACTION**: Do NOT provide pickup times or instructions as if the trip is upcoming.
                 - **SAY**: "I notice this booking is for a past date ({trip_date_obj}). Are you inquiring about a previous trip or would you like to make a new booking?"
                 """

        # Determine if Critical Info is Missing
        missing_critical_info = []
        
        # Initialize is_today variable safely
        is_today = False
        
        if rec and rec.get("fields"):
            f = rec["fields"]
            
            # Only check Hotel/Room if it is a Transfer Trip
            if is_transfer_trip:
                # Basic Requirement: Hotel Name is ALWAYS required
                if not self.get_field_value(f, FieldIds.HOTEL_NAME):
                    missing_critical_info.append("Hotel Name")
                
                # Room Number Requirement:
                # If trip is TODAY (days_diff == 0), Room Number is OPTIONAL (as per user request).
                # If trip is NOT Today, Room Number is REQUIRED.
                if trip_date_obj:
                     now_cairo = datetime.utcnow() + CAIRO_OFFSET
                     days_diff = (trip_date_obj - now_cairo.date()).days
                     if days_diff == 0:
                         is_today = True
                
                if not is_today:
                    if not self.get_field_value(f, FieldIds.ROOM_NUMBER):
                        missing_critical_info.append("Room Number")

        missing_info_instruction = ""
        if missing_critical_info:
            missing_str = " and ".join(missing_critical_info)
            missing_info_instruction = f"""
            **CRITICAL ALERT - MISSING DATA**:
            The Booking Record is MISSING: **{missing_str}**.
            - IF the user is asking for Pickup Time: **YOU MUST STOP**. Do NOT provide any time (even if found).
            - **ACTION**: Reply asking the user to provide their **{missing_str}** first.
            - Explain that we need this to schedule the transfer.
            """
        else:
            # Special Instruction for TODAY's trips without Room Number
            if is_transfer_trip and is_today and not self.get_field_value(f, FieldIds.ROOM_NUMBER):
                 missing_info_instruction = """
                 **URGENT TRIP ALERT (TODAY)**:
                 - The trip is TODAY. The Room Number is missing, BUT because it is today, we can proceed with just the Hotel Name.
                 - **ACTION**: If Pickup Time is available in the record, GIVE IT to the user.
                 - Do NOT ask for the Room Number now (it might delay them).
                 """

        attachment_instruction = ""
        if has_attachments:
            attachment_instruction = """
            **ATTACHMENT ALERT**: 
            There are documents attached to this email (e.g. Flight Tickets, Vouchers, Itinerary).
            - **ACTION**: You MUST mention in your reply: "I have attached your tickets/documents to this email."
            """
        else:
            attachment_instruction = """
            **NO ATTACHMENTS FOUND**:
            - There are NO documents attached to this record.
            - IF user asks for tickets:
              - **ACTION**: Check if the booking is confirmed.
              - **SAY**: "I am checking your ticket status. It seems the tickets are not yet generated/attached. I will notify our operations team to send them to you."
              - Start reply with `[ESCALATE]`.
            """
        
        # TICKET REQUEST SPECIFIC INSTRUCTION
        # Fixed NameError: 'kind' is not defined here yet. It is defined in process_unified_message but not passed here.
        # We should remove the 'kind' check or pass it as an argument.
        # For now, we will infer it from message body if needed, or rely on logic outside.
        
        # --- HUMAN AGENT / MANUAL REPLY DETECTION ---
        # If the last message in the chat log was from "Admin" or "System" (via Operations System),
        # we should instruct the AI to be aware of it.
        
        last_human_reply = ""
        if chat_log_raw:
             # Simple check for last non-AI, non-Customer line
             # We assume format: [Timestamp] [Role]: Message
             lines = chat_log_raw.split('\n')
             for line in reversed(lines):
                 if "[Admin]" in line or "[System]" in line:
                     last_human_reply = line
                     break
        
        human_agent_instruction = ""
        if last_human_reply:
             human_agent_instruction = f"""
             **HUMAN AGENT CONTEXT**:
             - A human agent (Admin) recently replied to this customer:
             - "{last_human_reply}"
             - **ACTION**: Ensure your reply is consistent with what the human agent just said. Do not contradict it.
             """

        escalation_context_instruction = ""
        if is_already_escalated:
             escalation_context_instruction = f"""
             **ESCALATION STATE DETECTED**:
             - This customer has ALREADY been escalated to the operations team for a PREVIOUS issue.
             - **CURRENT INTENT**: {kind}
             
             **ACTION LOGIC**:
             1. **IF USER IS ASKING ABOUT THE PREVIOUS ISSUE (FOLLOW_UP)**:
                - Do NOT ask for details again.
                - **SAY**: "I have forwarded your message to our operations team again to prioritize your request. We will contact you shortly."
                - Start reply with `[ESCALATE]`.
                
             2. **IF USER IS ASKING A NEW, UNRELATED QUESTION (e.g., TRIP_INFO_QUERY, PICKUP_QUERY)**:
                - **ANSWER** the new question normally using the sources below.
                - **ADD A NOTE**: At the end, gently remind them: "Regarding your previous request, our team is still working on it."
                - **DO NOT** start with `[ESCALATE]` unless this new question ALSO requires escalation.
             """
            
        # Urgency Instruction
        pickup_time_val = self.get_field_value(rec["fields"], FieldIds.PICKUP_TIME) if rec else None
        
        # Calculate Cairo Time for Context
        now_cairo = datetime.utcnow() + CAIRO_OFFSET
        now_cairo_str = now_cairo.strftime("%A, %d %B %Y, %I:%M %p")
        
        urgency_instruction = ""
        if is_urgent_trip and not pickup_time_val and is_transfer_trip:
             urgency_instruction = """
             **URGENT PICKUP ALERT**:
             - The trip is TODAY or TOMORROW.
             - Pickup Time is NOT SET in the system yet.
             - **ACTION**: IF the user asks for pickup time, You MUST start your reply with `[ESCALATE]`.
             - Tell the user: "I am checking with our operations team immediately to get your exact pickup time."
             """
        elif not is_urgent_trip and not pickup_time_val and is_transfer_trip:
             urgency_instruction = """
             **STANDARD PICKUP ALERT**:
             - The trip is in the future (more than 48h).
             - Pickup Time is NOT SET yet.
             - **ACTION**: IF the user asks for pickup time, Tell them: "Your confirmed pickup time will be sent to you via WhatsApp and Email the day before your trip, typically by 6:00 PM."
             """
        elif not is_transfer_trip:
             urgency_instruction = """
             **TICKET ONLY / NO TRANSFER ALERT**:
             - This trip appears to be a **Ticket Only** or **Meeting Point** option (based on Trip Name or Option field).
             - **ACTION**: Do NOT promise a hotel pickup time.
             - Tell the user to check their ticket/voucher for the meeting point location and time.
             - If they insist on pickup, explain that this specific booking option does not include hotel transfer.
             """

        # Extra Transfer Fee Logic
        extra_transfer_instruction = ""
        if rec and rec.get("fields"):
            f = rec["fields"]
            current_hotel = self.get_field_value(f, FieldIds.HOTEL_NAME)
            
            # Check if this hotel requires fee
            transfer_record = self.check_hotel_transfer_fee(current_hotel, trip_name)
            if transfer_record:
                # Check if Paid
                addons_text = self.get_field_value(f, FieldIds.ADD_ONS_TEXT) or ""
                addons_multi = self.get_field_value(f, FieldIds.ADD_ONS_MULTI) or []
                
                # Simple check: Does addons mention "transfer" or "extra"?
                is_paid = "transfer" in addons_text.lower() or "extra" in addons_text.lower()
                # Also check multi-select values (list of strings)
                if not is_paid and addons_multi:
                    if isinstance(addons_multi, list):
                        for item in addons_multi:
                             if "transfer" in str(item).lower() or "extra" in str(item).lower():
                                 is_paid = True
                                 break
                    elif isinstance(addons_multi, str):
                         if "transfer" in addons_multi.lower() or "extra" in addons_multi.lower():
                             is_paid = True

                if not is_paid:
                    extra_transfer_instruction = f"""
                    **EXTRA TRANSFER FEE ALERT**:
                    - The customer is staying at **{current_hotel}**, which is outside the standard pickup zone.
                    - **System Check**: The customer has NOT paid for this extra transfer yet.
                    - **ACTION**: 
                      - IF the user asks about pickup or confirms this hotel: Inform them politely: "Please note that {current_hotel} is in an extra transfer zone. Our operations team will check if any additional fee is required and contact you if needed."
                      - Do NOT confirm the pickup 100% without mentioning this potential check.
                    """


        # BUTTON MESSAGE INSTRUCTION
        button_msg_instruction = ""
        if "[BUTTON MESSAGE]" in latest_message_body:
             button_msg_instruction = """
             **BUTTON MESSAGE DETECTED**:
             - The user clicked a button from an automated message (e.g. "Confirm Pickup", "Talk to Agent").
             - **ACTION**: Treat the text after [BUTTON MESSAGE] as the user's intent.
             - Example: If text is "[BUTTON MESSAGE] Talk to Support", treat it as "I want to talk to support".
             - Do NOT say "I received your button message". Just act on it naturally.
             """

        # Add VIATOR Data Search Result
        source_viator_text = self.search_viator_local_db(latest_message_body)

        final_prompt = f"""You are a helpful customer service agent for FTS Travels.
            
**PERSONALIZATION:**
- You are speaking to **{customer_first_name}**. 
- **CRITICAL: NO GREETING IN EMAIL REPLY**:
- The system ALREADY adds "Dear {customer_first_name}," at the top of the email automatically.
- **DO NOT** start your message with "Hello", "Hi", "Dear", or "Welcome".
- **DO NOT** repeat the customer's name in the first sentence.
- **START DIRECTLY** with the body of your response.
- Example: Instead of "Hello Ahmed, I can help you...", say "I can certainly help you with..." directly.
- Exception: If the user message is very short (e.g. "Thanks"), you can be brief, but still avoid the double greeting.

**CRITICAL - LANGUAGE RULE:**
1. **DETECT THE LANGUAGE** of the User's latest message below ("{latest_message_body[:50]}...").
2. **YOU MUST START YOUR REPLY WITH**: `[LANGUAGE: English]` or `[LANGUAGE: Arabic]` etc. to confirm your detection.
3. **THEN REPLY IN THAT EXACT SAME LANGUAGE**.
4. **DO NOT** use the customer's name language or the booking data language to decide the reply language.
5. **Example**: If user asks in English -> Start with `[LANGUAGE: English]`, then Reply in English.
6. **VIOLATION OF THIS RULE IS A CRITICAL FAILURE.**

**CLASSIFIED INTENT:** {kind}
(Note: The system has pre-classified this intent based on keywords. If the user's message clearly contradicts this, you may adjust, but please prioritize this classification for routing purposes.)

User Question (DETECT LANGUAGE FROM HERE): "{latest_message_body}"

CURRENT DATE & TIME (CAIRO): {now_cairo_str}

SOURCE 0: PAST CONVERSATION MEMORY (This is the history of ALL previous interactions with this customer):
{past_conversations}

{classification_instruction}

**IMPORTANT INSTRUCTION FOR INTENT TAGGING:**
- If the system provided a CLASSIFIED INTENT above (e.g., LOST_ITEM), you SHOULD likely output that same intent in your final tag, unless it is completely wrong.
- For LOST_ITEM, ensure you append `[INTENT: LOST_ITEM][DEPT: OPERATIONS]` at the end.
- For URGENT_ISSUE, ensure you append `[INTENT: URGENT_ISSUE][DEPT: QUALITY]` at the end.

SOURCE 1: OFFICIAL BOOKING RECORD (Use this as the PRIMARY source of truth for times, locations, and inclusions):
{booking_details_str}
**TRIP NAME CORRECTION RULE**:
- The "Trip Name" in Source 1 might be a generic internal name (e.g. "Sharm El-Sheikh - Cairo Flight").
- OFFICIAL NAME FROM MPC DATABASE: {mpc_name_context}
- **ACTION**: You MUST use the **OFFICIAL NAME FROM MPC DATABASE** above when referring to the trip name in your response.
- Do NOT use the generic name from Source 1 if an Official Name is provided.

SOURCE 2: WEB SEARCH RESULTS (PRIORITY: Source of Truth for Updated Content & Policies):
{web_ctx}

SOURCE 2.5: GET YOUR GUIDE SUPPLIER DATA (OFFICIAL PARTNER DETAILS - HIGH PRIORITY):
{gyg_context}

SOURCE 3.3: VIATOR TRIPS CATALOG (New Partner Data - Trusted):
{source_viator_text}

**SPECIAL RULE FOR VIATOR CLIENTS**:
- IF the User mentions "Viator" or if the query is about a Viator booking:
- **USE SOURCE 3.3 (Viator Trips Catalog)** as the primary reference for trip details, description, and inclusions.
- Treat Viator trips as a distinct source.

SOURCE 3: INTERNAL TRIPS CATALOG (Secondary Source for general trip details):
{internal_trips_context}

SOURCE 3.2: HEADOUT TRIPS CATALOG (New Partner Trips - Trusted):
{self.headout_catalog_context}
**RESTRICTION FOR SOURCE 3.2**:
- ONLY use this source if the User is asking about a specific Headout trip or if the info is NOT found in SOURCE 1 or SOURCE 3.
- If the user asks about a general FTS trip, prioritize SOURCE 3 (Internal Catalog).

SOURCE 3.1: TRIPS DATABASE SCHEMA (Reference for field meanings):
{self.trips_schema_context}

SOURCE 4: INTERNAL KNOWLEDGE BASE (Trusted Internal Data):
{kb_context}

**SALES & INQUIRY GUIDANCE (CRITICAL FOR SALES)**:
- **GOAL**: You are a professional, persuasive, and empathetic travel consultant, NOT just an FAQ bot.
- **LEADERSHIP**: Do NOT just answer questions. LEAD the conversation. Always end with a clear next step or a relevant question to move the booking forward.
- **SUMMARIZATION**: Every 3-4 exchanges, briefly summarize what has been agreed upon (Dates, Pax, Interests) to show you are listening and to anchor the plan.
- **EXPERIENCE SELLING**: Don't just list features (e.g., "Lunch included"). Sell the EXPERIENCE (e.g., "You will enjoy a freshly prepared lunch with a view of the Pyramids").
- **AVOID GENERIC QUESTIONS**: Avoid "What are your preferences?". Instead, offer choices: "Do you prefer a relaxing historical tour or an adventure-packed day?" or "Would you like a hotel near the Nile or close to the Pyramids?".
- **TONE**: Be warm, human, and professional. Avoid overly robotic phrases like "Please do not hesitate to contact us". Use "I'm here to help you anytime!" or "Let's make this trip perfect for you."

INSTRUCTIONS:
1. **CRITICAL: LANGUAGE MATCHING**: 
   - Analyze the "User Question" text above.
   - If the User Question is in **English**, your entire reply MUST be in **English**.
   - If the User Question is in **Arabic**, your entire reply MUST be in **Arabic**.
   - **DO NOT** use the customer's name to guess the language. Even if the name is "Ahmady", if he writes in English, reply in English.
   - Do NOT mix languages unless necessary for names.

2. **SOURCE HIDING & TONE (CRITICAL)**:
   - **NEVER** mention "Source 1", "Source 2.5", "Get Your Guide Data", "Internal Catalog", or "Airtable" to the customer.
   - Speak as **FTS Travels** directly.
   - Instead of "According to Source 2", say: "Based on our records...", "Our system shows...", or simply state the fact.
   - **DO NOT** expose internal data structures or partner names unless relevant (e.g. "Your booking is confirmed with our partner").

3. **UNCERTAINTY & WAITING (STRICT)**:
   - **IF THE INFORMATION IS AMBIGUOUS, MISSING, OR CONFLICTING**:
   - **DO NOT GUESS**.
   - **DO NOT** say "It seems like..." or "Usually...".
   - **ACTION**: Tell the customer you need to confirm with the Operations Team.
   - **SAY**: "To ensure I give you 100% accurate information regarding [Topic], I will check with our operations team and get back to you shortly."
   - **ESCALATE**: If necessary, start reply with `[ESCALATE]` so a human sees it.

4. **MULTI-TURN CONTEXT AWARENESS (CRITICAL)**:
   - Check "SOURCE 0: PAST CONVERSATION MEMORY".
   - If your LAST message asked a specific question (e.g., "What is the name?", "What is the room number?"), and the user replies with a short phrase (e.g., "Ahmed", "101"), **YOU MUST LINK THEM**.
   - **Example**: If you asked "What is the new guest name?" and user says "Ahmed", assume "Ahmed" IS the new guest name. Do NOT ask "Do you mean Ahmed is the guest?". Just accept it and proceed.
   - **ACTION**: If you have collected all necessary info (Name + Age/Type), then **ESCALATE** immediately as per the request.

5. **LOGIC & REASONING**:
   {button_msg_instruction}
   {missing_info_instruction}
   {attachment_instruction}
   {past_trip_instruction}
   {urgency_instruction}
   {extra_transfer_instruction}
   {escalation_context_instruction}
   - Look at the "CLASSIFIED INTENT".
   {human_handover_instruction}
   - **CONTEXTUAL INTELLIGENCE (CRITICAL)**: 
     - You have access to "SOURCE 0: PAST CONVERSATION MEMORY". 
     - If the user previously mentioned "Cairo" or "Museum", and now says "Tomorrow, 2 people", YOU MUST COMBINE THESE FACTS.
     - **DO NOT** say "I don't know the trip name" if they just mentioned it in the previous message.
     - **DO NOT** be robotic (e.g., avoid "Based on the record", "I see from your question"). Speak naturally like a human agent.

   - **CRITICAL: MISSING BOOKING SCENARIO**:
     - IF "SOURCE 1" says "No Booking Details Found" (OR "No Confirmed Booking Found") AND the user is asking about specific booking details (Pickup, Ticket, Status, Cancellation):
     - **ACTION**: Do NOT invent details. Do NOT just apologize.
     - **SAY**: "I cannot find a booking linked to this email address. Could you please provide your **Booking Reference Number** or the **Phone Number** used during booking so I can look it up for you?"

   - **CRITICAL: CLAIMED BOOKING BUT NO RECORD (EXTERNAL/OTA)**:
     - IF "SOURCE 1" says "No Booking Details Found" (OR "No Confirmed Booking Found") BUT the user claims to have a booking (e.g., "I booked via Check24", "I have a reservation for tomorrow"):
     - **DO NOT** act as if the booking exists. **DO NOT** ask for operational details like "Room Number" or "Hotel Name" yet.
     - **ACTION**: You MUST verify the booking first.
     - **SAY**: "I cannot currently see a booking with these details in our system. To ensure I access the correct file, could you please provide your **Booking Reference Number** or the **Email Address** used for the booking?"

   - **HANDLING VIATOR BOOKINGS**:
     - **DATA SOURCE**: The system uses **Source 3.3: VIATOR TRIPS CATALOG** for Viator bookings.
     - **ACTION**: Answer questions about itinerary/inclusions using Source 3.3.
     - **DISCLAIMER**: If asked about specific booking ID or voucher issues, ask for the "Viator Booking Reference" to check with operations.
     - **NOTE**: Viator prices and inclusions are subject to change. Use the catalog as a reference.

   - **HANDLING HEADOUT BOOKINGS**:
     - **CHECK**: If 'Agency' is "Headout" (in Source 1).
     - **POLICY**: Headout bookings have strict cancellation/modification policies managed by the supplier.
     - **PRICING RULE (CRITICAL)**: When discussing Headout trip prices (Source 3.2), **NEVER** state the exact price as final. **ALWAYS** qualify it as "Approximate", "Estimated", or "Starting from around". (e.g., say "Approx. $23" instead of "$23").
     - **ACTION**: If the user asks for changes or cancellations, explain that we must coordinate with the supplier.
     - **INFO**: Use "SOURCE 3.2: HEADOUT TRIPS CATALOG" for trip details if available.
     - **SAY**: "As this is a Headout booking, any changes are subject to their specific supplier policies. I can check the details for you."

   - **HANDLING HUMAN AGENT REPLIES**:
     {human_agent_instruction}
     {learned_ctx}
   
   - **MISSING BOOKING / LEAD HANDLING**:
     {lead_instruction}
   
   - If **LOST_ITEM**: Empathize, ask for details (if not provided), and say we will contact the driver/operations immediately. Do NOT just give pickup time.
   - If **PICKUP_QUERY**: Check 'SOURCE 1'. If time/hotel is there, give it. If not, follow the ALERT instructions above.
   - If **INFO_UPDATE**: Acknowledge the information warmly (e.g., "Thank you for updating your details"). Confirm that we have received it. Do NOT escalate.
   - If **TRIP_INFO_QUERY** (New Booking / Inquiry):
     - **CONTEXT CHECK (CRITICAL)**: Check if the user is asking about a *NEW* trip (e.g., "I want to book Orange Bay", "Can I book another tour?") vs asking about the *EXISTING* booking.
     - **IF NEW BOOKING REQUEST**:
       - Ignore "SOURCE 1: OFFICIAL BOOKING RECORD" (as it refers to the old trip).
       - **CHECK SOURCE 2 (Internal Trips Catalog)**: Search for the destination/activity (e.g. "Orange Bay").
       - **PROPOSE A SOLUTION**: If found, offer it with price/details.
       - **DO NOT** say "I cannot see a booking". Say: "We can certainly arrange that for you! The Orange Bay trip includes..."
       - If multiple options exist, list them briefly.
     - **IF EXISTING BOOKING QUERY**: Use Source 1.

   - If **CANCELLATION**: 
     - **POLICY**: Free cancellation is allowed ONLY if requested at least **24 hours** before the trip start time.
     - **DATE CHECK (CRITICAL)**: Compare "Trip Date" (Source 1) vs "CURRENT DATE & TIME" above.
       - If Trip Date is in the **PAST**: Refund is IMPOSSIBLE. Say: "Unfortunately, the trip date has passed."
       - If Trip Date is **TODAY**: Refund is IMPOSSIBLE (Less than 24h). Say: "Cancellation is not possible less than 24 hours before the trip."
       - If Trip Date is **FUTURE**: Check 24h rule.
     - **SCENARIO A (Policy Question)**: If user asks "What is the policy?", Answer from the policy above. DO NOT ESCALATE.
     - **SCENARIO B (Cancellation Request)**: If user says "I want to cancel":
         - **ACTION 1 (RETAIN)**: Politely ask why. Try to solve.
         - **ACTION 2 (ESCALATE)**: Start reply with `[ESCALATE]`. Say: "I have forwarded your request to our operations team..."

   - If **COMPLAINT**: Apply CRISIS MANAGEMENT rules below.
   - If **TRIP_INFO**: Use SOURCE 1 & 2.

   - **PRESENTING BOOKING DETAILS (INTELLIGENT DISPLAY)**:
     - You have access to fields: "Selected Option", "Add-Ons Details", "Flight Departure (From)", "Flight Return (To)".
     - **WHEN TO SHOW**: ONLY if the user asks about trip details, flights, inclusions, or "what did I book?".
     - **HOW TO SHOW**:
       - **Flights**: If 'Flight Departure' is available (e.g. MS 07:00), say: "Your flight departs at 07:00 (MS)."
       - **Option**: Mention the specific option booked (e.g. "You selected the [Selected Option] package").
       - **Add-Ons**: Mention any add-ons found in "Add-Ons Details" or "Add-Ons (Operational)".
       - **NOTE**: For "Add-Ons (Operational)", these are already handled by operations. **DO NOT** ask the user to pay for them. Just confirm they are included.

6. **PRIMARY SOURCE**: Answer based strictly on the OFFICIAL BOOKING RECORD first.
7. **SECONDARY SOURCE**: If details are missing, use INTERNAL TRIPS CATALOG (Source 3).
   - **HEADOUT CATALOG (Source 3.2)**: Use this ONLY if the trip is not found in Source 3 or specifically identified as a Headout trip.
   - **CROSS-VERIFICATION (CRITICAL)**: 
     - Use "SOURCE 3: INTERNAL KNOWLEDGE BASE" (Historical Emails) to understand HOW to answer similar questions politely and accurately.
     - **COMPARE**: Check if the historical answer conflicts with "SOURCE 1" (Booking) or "SOURCE 2" (Catalog).
     - **RULE**: If Historical Email says "Lunch is included" but Catalog says "Lunch Excluded", TRUST THE CATALOG (Source 2).
     - **GOAL**: Combine the *tone/style* of past emails with the *facts* of the current catalog.

8. WEB SEARCH STRICTNESS: 
   - Only use if info is NOT in internal sources.
   - Must be 100% SURE.

9. INVESTIGATION & RETENTION (PRIORITY - DO NOT ESCALATE YET):
   - If the user reports a problem, is vague, or asks for something complex: **DO NOT ESCALATE IMMEDIATELY**.
   - **Step 1**: Try to understand the root cause. Ask 1-2 polite, clarifying questions to gather more details.
     - Example: "I want to ensure I help you correctly. Could you please specify which part of the itinerary you'd like to check?"
     - Example: "I'm sorry to hear about this. To assist you better, could you tell me exactly what went wrong?"
   - **Step 2**: Use the new details to check your sources (Booking Record, Knowledge Base) again.
   - **Step 3**: ONLY escalate if you have fully understood the problem and confirmed you truly cannot solve it.

10. WHEN TO ESCALATE (STRICT RULES):
   - **RULE A (Explicit Human Request)**: If user asks for "human", "agent", "support", or "manager" -> **ESCALATE**.
   - **RULE B (Action Required)**: If user asks to CHANGE data (Date, Room, Phone) -> **ESCALATE**.
     - **EXCEPTION**: If user provides MISSING DETAILS (Room Number, Passport, Full Name) for an existing booking:
       - **DO NOT ESCALATE**.
       - Instead, THANK the user and confirm the details are noted.
       - Start reply with `[UPDATE_DETAILS]`.
   - **RULE C (Unknown Info)**: ONLY escalate if the answer is NOT in Source 1, 2, or 3.
   - **DO NOT ESCALATE** for general questions if you can find the answer.
   - **SPECIAL RULE (TripAdvisor/Viator Emails)**: 
     - If the email is a proxy (e.g., @expmessaging.tripadvisor.com) AND the body contains "Booking Reference" or system text without a clear user question:
     - **DO NOT ESCALATE**. Just confirm receipt or provide booking details if found.
     - Often these are just notifications. If no question is asked, do not create a support ticket.
     - **NOTE ON LINKS**: If the email contains links like `<https://www.viator.com/...>`, treat them as part of the signature or system text, NOT as a user query.



11. **COMPLAINT & ESCALATION PROTOCOL (STRICT GOVERNANCE)**:
    - **ROLE**: You are a professional support assistant. PROTECT the company legally and operationally.
    - **TRIGGER**: Angry user, Fraud report, Service failure, Extra charges.
    
    - **CORE RULES (DO NOT BREAK)**:
      1. **NEVER admit financial/legal liability** (Avoid: "We made a mistake", "We failed", "Our fault").
      2. **NEVER promise refunds** immediately. Use: "We will review the case and process a refund if applicable."
      3. **OTA BOOKINGS (CRITICAL)**: 
         - **CHECK THE 'Agency' FIELD IN SOURCE 1**: If it says "GetYourGuide", "Viator", "Headout", "Expedia", or anything other than "FTS Travels" or "Direct":
         - State clearly: "As this booking was made via [Agency Name], pricing and inclusions are governed by their platform terms."
         - "We will cooperate fully with them to investigate and support your case."
      
    - **REQUIRED RESPONSE STRUCTURE**:
      1. **Empathy (Neutral & Professional)**: "I am sorry to hear that your experience did not meet expectations." (Do NOT over-apologize like "I am terribly sorry for our failure").
      2. **Investigation**: "I have opened an investigation ticket to review the booking details and coordinate with the relevant team."
      3. **Evidence**: Ask for photos/receipts to **customer.service@ftstravels.com**.
      4. **Timeline**: "We will provide an update within **48-72 business hours**."
      5. **Closing**: "We appreciate you taking the time to share your feedback with us. It helps us improve."
      
    - **RESTRICTIONS**:
      - Do NOT use "High Priority" unless the user is threatening legal action or public reviews.
      - Do NOT mention "Local Partners" in a way that shifts blame. Say "Our Operations Team". 
         - **ONLY IF** the user explicitly threatens a negative review or says "I will rate you 1 star":
         - Say: "May I kindly ask you to hold off on leaving a public review until we complete our investigation? We are committed to resolving this fairly."
    - **RESTRICTIONS**: 
      - **DO NOT** mention "Local Partners" or specific external entities unless you are 100% sure. Just say "Our Operations Team".
      - **DO NOT** promise a refund immediately. Say "If the investigation confirms the error, we will process a refund."

12. **RESTRICTIONS**: 
    - **DO NOT** mention or generate any "personalized portal" links (e.g., ftstravels.net/?booking=...). 
    - **DO NOT** invent dashboard links. Only use links present in the official booking record.

13. **ALCOHOL POLICY (STRICT)**:
    - **IF USER ASKS ABOUT ALCOHOL**:
      - Reply CLEARLY: "We do not serve or sell alcoholic beverages on our trips."
      - Do NOT apologize for this policy.
    - **IF USER DOES NOT ASK**:
      - Do NOT mention alcohol at all. Do NOT say "Alcohol is not included". Just list what IS included (Water, Soft Drinks, etc.).

14. **NO HALLUCINATION RULE (STRICT)**:
    - **IF USER ASKS ABOUT SPECIFIC GEAR/ITEM (e.g., Wetsuit, Lunch, Towel)**:
      - **CHECK SOURCE 2 & 3 FIRST**.
      - IF the info is NOT explicitly there: **DO NOT INVENT IT**.
      - **DO NOT SAY** "It is available for rent" unless you see "Available for rent" in the data.
      - **DO NOT SAY** "It is not included" unless you see "Not included" or are 100% sure based on standard inclusions.
      - **SAFE REPLY**: "I will verify this detail with our operations team to ensure I give you the correct information regarding [ITEM], and I will get back to you as soon as possible."

**FINAL CHECK**: Ensure your reply language matches the User Question language EXACTLY.
"""
        response = self.query_ai(final_prompt)
        
        # CLEANUP: Remove [LANGUAGE: ...] tag if present
        if "[LANGUAGE:" in response:
            # We keep everything AFTER the language tag
            # Example: "[LANGUAGE: English]\nDear Customer..."
            parts = response.split("]", 1)
            if len(parts) > 1:
                response = parts[1].strip()
        
        # Append Department & Intent Tags for internal use
        return f"{response}\n[DEPT: {department}] [INTENT: {kind}]"

    def parse_chat_log_to_history_list(self, chat_log_text):
        """
        Parse the text-based chat log back into a structured list for the intervention checker.
        Format: [YYYY-MM-DD HH:MM:SS] [Source - Sender]: Message
        """
        history_list = []
        if not chat_log_text:
            return history_list
            
        # Regex to capture timestamp and sender
        # Matches: [2023-10-20 15:30:00] [WhatsApp - Human Agent]: Hello...
        pattern = re.compile(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[(.*?)\]: (.*)')
        
        lines = chat_log_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            match = pattern.match(line)
            if match:
                date_str, sender_info, body = match.groups()
                
                # Determine sender type
                sender_lower = sender_info.lower()
                is_ai = "ai" in sender_lower or "system" in sender_lower
                
                # Construct mock message object similar to Gmail API
                msg = {
                    'date': date_str, # Keep as string, check_human_intervention will parse it if format matches
                    'sender': sender_info,
                    'body': body,
                    'is_ai': is_ai
                }
                history_list.append(msg)
                
        return history_list

    def check_human_intervention(self, history, customer_email):
        """
        Check if a human agent has intervened in the thread recently.
        Returns: (is_intervened, reason)
        """
        HUMAN_PAUSE_WINDOW_HOURS = 1
        # Enhanced Signature Detection:
        # FIX: Removed generic footers (address/website) that caused False Positives with Human Agents.
        # Added specific disclaimer text found in the AI templates.
        AI_SIGNATURES = [
            "FTS Travels AI Assistant", 
            "مساعد FTS Travels الذكي",
            "Our Smart Assistant may make mistakes", # Specific AI Disclaimer from screenshot
            "Note: Our Smart Assistant",             # Robust partial match
            
            # --- AUTOMATED SYSTEM TEMPLATES (NOT HUMAN) ---
            "Proceed to Payment",                    # Payment Button
            "Download Invoice",                      # Invoice Link
            "Your trip is confirmed!",               # Confirmation Template
            "Booking Confirmation Payment",          # Automated Subject/Header
            "View conversation in Management Center" # Viator/OTA Automated Footer
        ]
        
        # Iterate backwards, skipping the last message (which is the new customer message)
        # For WhatsApp (parsed from log), the last message IS the new user message we just logged.
        
        if not history:
            return False, ""

        # ... (rest of logic) ...
        # We need to adapt the date parsing because Gmail uses RFC 2822 but Log uses ISO
        
        from dateutil import parser # Use dateutil for robust parsing if available, else custom
        
        for i in range(len(history) - 1, -1, -1):
            msg = history[i]
            sender = msg.get('sender', '').lower()
            body = msg.get('body', '')
            
            # Skip the customer's own messages
            if customer_email and customer_email.lower() in sender:
                 continue
            if "user" in sender or "guest" in sender:
                 continue
                
            # Check if it is AI
            is_ai = False
            # Check explicit flag (from our parser)
            if msg.get('is_ai'):
                is_ai = True
            
            # Check signatures
            if any(sig in body for sig in AI_SIGNATURES):
                is_ai = True
                
            # Check Sender Name
            if "ai_learning" in sender or "system" in sender:
                is_ai = True
            
            # Treat OTA notifications as System messages (Safe to continue, not Human Intervention)
            ota_senders = ["viator", "headout", "getyourguide", "expedia", "tripadvisor", "booking.com"]
            if any(ota in sender for ota in ota_senders):
                is_ai = True

            if not is_ai:
                # It's a Human Message! Check time.
                try:
                    # Handle different date formats
                    date_val = msg['date']
                    msg_dt = None
                    try:
                        # Try standard Email format
                        from email.utils import parsedate_to_datetime
                        msg_dt = parsedate_to_datetime(date_val)
                    except:
                        # Try ISO format (from Chat Log)
                        try:
                            msg_dt = datetime.strptime(date_val, "%Y-%m-%d %H:%M:%S")
                        except:
                            pass
                    
                    if msg_dt:
                        # Make naive datetime aware if needed (assume Cairo/UTC+2 if naive)
                        if msg_dt.tzinfo is None:
                            # Assume server time (which is roughly local)
                            msg_dt = msg_dt.replace(tzinfo=None) # Compare naive to naive
                        else:
                            # If msg_dt is aware, make it naive or convert both to aware
                            # Easiest: Convert to naive local time by dropping tz info
                            msg_dt = msg_dt.replace(tzinfo=None)
                            
                        # Use UTC+2 (Cairo) as "Now" because logs are in Cairo time
                        # CAIRO_OFFSET is 2 hours
                        now = datetime.utcnow() + timedelta(hours=2)
                        diff = now - msg_dt
                        
                        # Fix negative time issue (due to small clock drift or timezone miscalculation)
                        total_seconds = diff.total_seconds()
                        if total_seconds < 0:
                            total_seconds = 0
                        
                        if total_seconds < HUMAN_PAUSE_WINDOW_HOURS * 3600:
                             return True, f"Human agent replied {total_seconds/60:.0f} mins ago."
                except Exception as e:
                    # logging.warning(f"Date parsing error in intervention check: {e}")
                    pass # Ignore parsing errors to keep logs clean
                    
        return False, ""

    def classify_supplier_email_type(self, body, subject):
        """
        Uses AI to classify the supplier email into specific categories.
        """
        prompt = f"""
        Analyze this email from a Travel Supplier (like Viator, Headout, GYG).
        Classify it into ONE of the following categories:

        1. BOOKING_CONFIRMATION: A standard new booking notification or receipt. No questions from customer.
        2. CANCELLATION: A notification that a booking was canceled.
        3. CUSTOMER_INQUIRY: The email contains a specific question or message WRITTEN BY THE CUSTOMER/GUEST that needs a reply.
        4. ADDITIONAL_INFO: The email contains new details provided by the customer (e.g., "Here is my pickup location", "My flight is...", "Passport details").
        5. OTHER: System notifications, marketing, or unclear content.

        Email Subject: {subject}
        Email Body (Excerpt):
        {body[:3000]}

        Reply with ONLY the Category Name (e.g., BOOKING_CONFIRMATION).
        """
        
        try:
            response = self.query_ai(prompt, system_role="analyzer").strip().upper()
            # Cleanup
            valid_types = ['BOOKING_CONFIRMATION', 'CANCELLATION', 'CUSTOMER_INQUIRY', 'ADDITIONAL_INFO', 'OTHER']
            for vt in valid_types:
                if vt in response:
                    return vt
            return "OTHER"
        except Exception as e:
            logging.error(f"Error classifying supplier email: {e}")
            return "OTHER"

    def detect_inquiry_in_supplier_email(self, body, subject):
        """
        Detect if a supplier email contains a specific customer inquiry or additional info
        that requires AI attention, rather than just being a standard booking receipt.
        """
        # 1. Check for explicit message blocks often used by OTAs
        inquiry_indicators = [
            "Customer message:", 
            "Message from customer:", 
            "Special Request:", 
            "User question:",
            "Guest has a question",
            "sent a message"
        ]
        
        for indicator in inquiry_indicators:
            if indicator.lower() in body.lower():
                return True
                
        # 2. Use AI to be sure (Lightweight check)
        # Only if body length is reasonable to avoid huge token usage on standard templates
        if len(body) < 10000:
            prompt = f"""
            Analyze this email from a travel supplier.
            Does it contain a SPECIFIC QUESTION, SPECIAL REQUEST, or MESSAGE from the customer/guest?
            Or is it just a standard automated booking confirmation/cancellation/update notification?
            
            Reply with ONLY "YES" if there is a specific user inquiry/request.
            Reply with "NO" if it is just a standard system notification.
            
            Email Subject: {subject}
            Email Body (Excerpt):
            {body[:2000]}...
            """
            response = self.query_ai(prompt, system_role="analyzer")
            if "YES" in response.upper():
                return True
                
        return False

    def analyze_email_relevance(self, sender, subject, body):
        """
        Uses AI to decide if an email requires processing or should be ignored.
        Filters out: Newsletters, Spam, Auto-Replies, System Notifications (e.g. Tawk.to, Google Play).
        """
        # 1. Quick Check for obvious spam keywords in subject
        spam_keywords = ["newsletter", "marketing", "promotion", "subscribe", "webinar", "sale", "off", "% off"]
        if any(k in subject.lower() for k in spam_keywords):
             logging.info(f"Ignored by keyword match: {subject}")
             return False, "Spam Keyword Match"

        # 2. AI Analysis
        prompt = f"""
        Act as an Email Filter for a Travel Agency AI.
        Analyze this incoming email and decide if it should be PROCESSED (Replied to or Saved) or IGNORED.

        Sender: {sender}
        Subject: {subject}
        Body (Excerpt):
        {body[:1000]}

        CRITERIA FOR "IGNORE":
        - Marketing, Newsletters, Promotions, Webinars.
        - Automated System Notifications that do NOT require action (e.g., "New login", "Privacy Policy Update", "Google Play Update").
        - Chat Transcripts (e.g., from tawk.to) unless they explicitly ask for a follow-up via email.
        - Out of Office / Auto-Replies.
        - Spam or Phishing.

        CRITERIA FOR "PROCESS":
        - Direct emails from Real Customers (Questions, Complaints, Updates).
        - New Booking Confirmations from Suppliers (Viator, GYG, Headout).
        - Operational updates requiring action.
        - Leads/Inquiries.

        OUTPUT FORMAT:
        Reply with exactly one word: "PROCESS" or "IGNORE".
        """
        
        try:
            response = self.query_ai(prompt, system_role="analyzer").strip().upper()
            if "PROCESS" in response:
                return True, "AI decided to Process"
            else:
                return False, "AI decided to Ignore (Marketing/System/Spam)"
        except Exception as e:
            logging.warning(f"Relevance Analysis Failed: {e}. Defaulting to PROCESS.")
            return True, "Error in Analysis (Default Process)"

    def check_if_supplier_email(self, sender, subject, body):
        """Check if email is a supplier booking notification."""
        # STRICT CHECK: Sender must match the official supplier domains.
        # This prevents customer emails (who might quote a reference number) from being skipped.
        
        sender = sender.lower()
        
        supplier_domains = {
            'Headout': ['headout.com', 'hello@headout.com'],
            'GetYourGuide': ['getyourguide.com', 'info@getyourguide.com', 'reply.getyourguide.com'],
            'Viator': ['viator.com', 'info@viator.com', 'expmessaging.tripadvisor.com', 'tripadvisor.com', 'customer.care@viator.com'],
            'Tiqets': ['tiqets.com', 'info@tiqets.com']
        }
        
        for agency, domains in supplier_domains.items():
            for domain in domains:
                if domain in sender:
                    return agency
                    
        return None

    def process_supplier_booking(self, agency_name, subject, body, thread_id):
        """Process a supplier booking email (Parse -> Save -> No Reply)."""
        logging.info(f"Processing Supplier Booking from {agency_name}")
        
        prompt = f"""
        Extract booking information from this {agency_name} email.
        
        FIELD DEFINITIONS:
        reference_number: Booking reference or order number
        real_product_name: Full product/tour name exactly as written
        tour_name: Simplified tour name
        tour_option: Tour option/ticket type
        date_trip: Visit date in ISO format (YYYY-MM-DDTHH:MM:SS.sssZ)
        main_Customer: Customer full name
        email: Customer email
        phone: Customer phone
        Adult: Number of adults (integer)
        Child: Number of children (integer)
        Infant: Number of infants (integer)
        Total price USD: Total price in USD (number only)
        Pickup location: Hotel/pickup address
        cancellation_status: 'Active', 'Canceled', or 'Changed'
        destination: City name (e.g. Cairo, Hurghada)
        
        RULES:
        1. Return ONLY valid JSON.
        2. Omit missing fields.
        3. If destination is missing, default to 'Cairo'.
        4. real_product_name should be the FULL tour name.
        
        EMAIL CONTENT:
        {body[:15000]}
        """
        
        try:
            result_json = self.query_ai(prompt, system_role="analyzer")
            # Cleanup JSON
            if "```json" in result_json:
                result_json = result_json.split("```json")[1].split("```")[0]
            elif "```" in result_json:
                result_json = result_json.split("```")[1].split("```")[0]
            
            extracted_data = json.loads(result_json.strip())
            
            # Save to Airtable
            self.save_supplier_booking(extracted_data, agency_name)
            
            return True
        except Exception as e:
            logging.error(f"Error processing supplier booking: {e}")
            return False

    def save_supplier_booking(self, data, agency):
        """Save extracted supplier booking data to Airtable."""
        ref_number = data.get('reference_number')
        if not ref_number:
            logging.warning("No reference number found in extracted data.")
            return

        # Map to Airtable Fields
        # We use FieldIds from airtable_fields.py
        fields = {}
        
        mapping = {
            'reference_number': FieldIds.BOOKING_NR,
            'real_product_name': FieldIds.REAL_PRODUCT_NAME,
            'tour_name': FieldIds.TRIP_NAME,
            'tour_option': FieldIds.OPTION,
            'date_trip': FieldIds.DATE_TRIP,
            'main_Customer': FieldIds.CUSTOMER_NAME,
            'phone': FieldIds.CUSTOMER_PHONE,
            'Adult': FieldIds.ADT,
            'Child': FieldIds.CHD,
            'Infant': FieldIds.INF,
            'Total price USD': FieldIds.TOTAL_PRICE_USD,
            'Pickup location': FieldIds.HOTEL_NAME,
            'cancellation_status': FieldIds.BOOKING_STATUS,
            'destination': FieldIds.DES
        }
        
        for json_key, field_id in mapping.items():
            if data.get(json_key):
                val = data[json_key]
                # SPECIAL HANDLING: PHONE NUMBERS
                if field_id == FieldIds.CUSTOMER_PHONE:
                    val = self.clean_phone_for_whatsapp(val)
                
                fields[field_id] = val

        # Handle Email specifically (avoid proxy emails for Personal Email field)
        extracted_email = data.get('email', '').lower()
        proxy_domains = ['expmessaging.tripadvisor.com', 'reply.getyourguide.com']
        is_proxy_email = any(pd in extracted_email for pd in proxy_domains)
        
        # User Logic: Do NOT save the email if it is a proxy email.
        # "Don't save the sender email if the proxy exists"
        if data.get('email') and not is_proxy_email:
             fields[FieldIds.CUSTOMER_EMAIL] = data['email']
        elif is_proxy_email:
             logging.info(f"Skipping saving proxy email to Customer Email field: {extracted_email}")
             # Ensure we wipe it if it was accidentally set
             if FieldIds.CUSTOMER_EMAIL in fields:
                 del fields[FieldIds.CUSTOMER_EMAIL]
        
        # Add Agency
        fields[FieldIds.AGENCY] = agency

        # Check for existing record
        existing_rec = self.find_booking_by_number(ref_number)
        
        if existing_rec:
            # Update Existing
            logging.info(f"Updating existing booking {ref_number}")
            
            # Protect existing fields (don't overwrite if not empty)
            protected_fields = [
                FieldIds.TRIP_NAME, FieldIds.DES, FieldIds.CUSTOMER_EMAIL, 
                FieldIds.CUSTOMER_PHONE, FieldIds.ADT, FieldIds.CHD, 
                FieldIds.REAL_PRODUCT_NAME, FieldIds.CUSTOMER_NAME
            ]
            
            existing_fields = existing_rec.get('fields', {})
            fields_to_update = {}
            
            for k, v in fields.items():
                # logic: if existing field has value, do not overwrite unless it's a status update?
                # The JS code says: protectExistingFields.
                if k in protected_fields and existing_fields.get(k):
                     continue # Skip
                fields_to_update[k] = v
            
            if fields_to_update:
                self.table.update(existing_rec['id'], fields_to_update)
                logging.info(f"Booking {ref_number} updated.")
        else:
            # Create New
            logging.info(f"Creating new booking {ref_number}")
            self.table.create(fields)
            logging.info(f"Booking {ref_number} created.")

    def process_unified_message(self, sender_identifier, message_body, history_text, source="Email", subject=None, thread_id=None, history_list=None):
        """
        Unified logic for processing messages from Email or WhatsApp.
        Returns a dict with processing results.
        """
        # --- FIX: Include Subject in Search Text for Booking Numbers ---
        # The history_text usually contains only the body. We need the subject too for regex extraction.
        if subject:
            full_search_text = f"Subject: {subject}\n\n{history_text}"
        else:
            full_search_text = history_text
        # -------------------------------------------------------------

        # Extract email/contact info
        customer_email = None
        contact_phone = None
        
        if source == "WhatsApp":
            contact_phone = sender_identifier
            # Clean phone if needed (remove spaces, etc)
            if contact_phone:
                contact_phone = str(contact_phone).replace(' ', '').replace('-', '').replace('+', '')
        else:
            customer_email = sender_identifier
            if '<' in sender_identifier and '>' in sender_identifier:
                customer_email = sender_identifier.split('<')[1].split('>')[0]
        
        # --- IGNORE INTERNAL EMAILS & SPECIFIC DOMAINS (Only for Email source or if email detected) ---
        if customer_email and "@" in customer_email:
            ignored_domains = [
                "ftstravels.com", "egymonuments.com", "mailchimp.com",
                "noreply-apps-scripts-notifications@google.com", "mail.clickup.com",
                "penniestosave.com", "mail.beehiiv.com", "stripe.com", "amazonses.com", "tawk.to", "aemktng.shutterstock.com", "tawk.to",
                "excursionmania.com", "waleed@maximrestaurants.com",
                "us2.make.com", "noreply@trip.com", "businessprofile-noreply@google.com"
            ]
            if any(d in customer_email.lower() for d in ignored_domains):
                logging.info(f"Skipping ignored domain email from {customer_email}")
                return None
        
        # --- AI PRE-ANALYSIS FILTER ---
        # Skip filter for WhatsApp messages (Direct messages are almost always relevant)
        # Robust check: Check source string AND if sender looks like a phone number
        is_whatsapp_source = source and source.lower() == "whatsapp"
        is_tawkto_source = source and source.lower() == "tawk.to"
        is_phone_sender = sender_identifier and (str(sender_identifier).isdigit() or str(sender_identifier).startswith('+'))
        
        if is_whatsapp_source or is_phone_sender or is_tawkto_source:
            should_process = True
            reason = f"{source} Source (Always Process)"
        else:
            should_process, reason = self.analyze_email_relevance(sender_identifier, subject or "Message", message_body)
        
        if not should_process:
            logging.info(f"Skipping message from {customer_email}: {reason}")
            return None
            
        # Update Session Cache with User Message
        self.update_session_memory(customer_email, message_body, role="user")
        
        # 1. Extract Data via AI (Always Extract even if human active)
        extracted_data = self.extract_booking_data_using_ai(history_text, sender_email=customer_email)
        
        # 2. Extract contacts
        extracted_phone = extracted_data.get('Customer Phone')
        if not contact_phone and extracted_phone:
             contact_phone = extracted_phone
        
        if not contact_phone:
             extracted_contacts = self.extract_contact_from_text(history_text, message_body)
             contact_phone = extracted_contacts.get("phone")
        
        # 3. Identify Booking Record
        booking_record = self.find_booking_strictly(
            full_search_text, 
            sender_email=customer_email, 
            sender_phone=contact_phone,
            ai_extracted_data=extracted_data
        )

        # --- MULTIPLE BOOKING DISAMBIGUATION LOGIC ---
        if booking_record and booking_record.get('other_related_bookings'):
            try:
                # 1. Gather all candidates (Main + Others)
                all_records = [booking_record] + booking_record['other_related_bookings']
                
                # 2. Filter: Only Future or Recent Past (last 3 days) to be relevant
                active_records = []
                now_cairo = datetime.utcnow() + CAIRO_OFFSET
                
                for rec in all_records:
                    d_str = self.get_field_value(rec['fields'], FieldIds.DATE_TRIP)
                    d_obj, _ = self.get_corrected_trip_date(d_str)
                    if d_obj:
                        diff = (d_obj - now_cairo.date()).days
                        # Include: Future (diff >= 0) OR Recent Past (diff >= -2)
                        if diff >= -2: 
                            rec['_parsed_date'] = d_obj
                            rec['_parsed_date_str'] = d_obj.strftime("%A, %d %B")
                            active_records.append(rec)
                
                # Only if we have multiple *active/relevant* bookings do we need to clarify
                if len(active_records) > 1:
                    logging.info(f"Multiple active bookings found ({len(active_records)}). Attempting disambiguation...")
                    
                    # 3. Keyword Matching (Smart Guess)
                    msg_lower = message_body.lower()
                    matched_records = []
                    
                    for rec in active_records:
                        trip_name = self.get_field_value(rec['fields'], FieldIds.TRIP_NAME) or ""
                        # Tokenize trip name (remove common words)
                        # e.g. "Luxor by Bus" -> "luxor"
                        trip_name_clean = trip_name.lower()
                        for stop_word in ["hurghada", "trip", "tour", "excursion", "ticket", "details", "booking", "day", "with", "from", "and"]:
                            trip_name_clean = trip_name_clean.replace(stop_word, "")
                        
                        tokens = [t for t in trip_name_clean.split() if len(t) > 3]
                        
                        # Check if ANY specific token is in user message
                        # e.g. User says "when is luxor?" -> matches "Luxor"
                        if any(t in msg_lower for t in tokens):
                            matched_records.append(rec)
                            
                    if len(matched_records) == 1:
                        # SUCCESS: Disambiguated!
                        booking_record = matched_records[0]
                        logging.info(f"Smart Disambiguation: Selected booking {booking_record['id']} based on message keywords.")
                        
                    elif len(matched_records) == 0:
                        # FAIL: Ambiguous -> Ask User
                        # Only ask if the user is actually asking a question (length > 3)
                        if len(message_body) > 3:
                            options_text = ""
                            for i, rec in enumerate(active_records, 1):
                                t_name = self.get_field_value(rec['fields'], FieldIds.TRIP_NAME)
                                d_str = rec['_parsed_date_str']
                                options_text += f"{i}. {t_name} ({d_str})\n"
                            
                            clarification_msg = (
                                f"I see you have multiple upcoming trips. Which one are you referring to?\n\n"
                                f"{options_text}\n"
                                f"Please reply with the number or trip name."
                            )
                            
                            logging.info("Ambiguous booking reference. Asking user for clarification.")
                            
                            # Return immediately to stop further processing and send this reply
                            return {
                                "response_text": clarification_msg,
                                "booking_record": booking_record, 
                                "customer_name": extracted_data.get('Customer Name', 'Guest'),
                                "inquiry_intent": "CLARIFICATION_REQUEST",
                                "attachments": [],
                                "was_escalated": False,
                                "escalation_dept": "SUPPORT"
                            }
            except Exception as e:
                logging.error(f"Error in Disambiguation Logic: {e}")
        # ---------------------------------------------

        # 4. Update with AI extracted data
        if booking_record:
            # Check for new critical details in email body
            # Specifically Room Number or Pickup Point updates
            new_room_number = extracted_data.get('Room Number')
            new_hotel_name = extracted_data.get('Hotel Name')
            
            updates = {}
            if new_room_number and str(new_room_number).lower() not in ["none", "n/a", "unknown"]:
                # Check if current is empty or different
                current_room = self.get_field_value(booking_record.get('fields', {}), FieldIds.ROOM_NUMBER)
                if not current_room or str(current_room).strip() == "":
                    updates[FieldIds.ROOM_NUMBER] = new_room_number
                    logging.info(f"Detected new Room Number: {new_room_number}")
            
            if new_hotel_name and str(new_hotel_name).lower() not in ["none", "n/a", "unknown"]:
                current_hotel = self.get_field_value(booking_record.get('fields', {}), FieldIds.HOTEL_NAME)
                if not current_hotel or str(current_hotel).strip() == "":
                     updates[FieldIds.HOTEL_NAME] = new_hotel_name
                     logging.info(f"Detected new Hotel Name: {new_hotel_name}")

            if updates:
                self.update_booking_record(booking_record['id'], updates, table_name=booking_record.get('table_name'))
                logging.info(f"Updated booking {booking_record['id']} with new extracted details: {updates}")

            self.update_booking_from_extracted_data(booking_record, extracted_data)

            # --- SPECIAL LOGIC: WhatsApp Email Update (No Inquiry) ---
            if source == "WhatsApp":
                # Check for email in message
                email_candidates = self.extract_emails_regex(message_body)
                if email_candidates:
                    email_in_msg = email_candidates[0]
                    # Check if message is essentially JUST the email (plus simple greeting)
                    # Remove email
                    clean_msg = message_body.replace(email_in_msg, "").strip()
                    # Remove common filler
                    clean_msg = re.sub(r'(?i)^(hi|hello|hey|my email is|email|here is|thanks|thank you|ok|please|update)\W*', '', clean_msg)
                    
                    # If remaining text is very short (< 10 chars), assume it's an update with no inquiry
                    if len(clean_msg) < 10:
                        logging.info(f"Detected Email Update via WhatsApp (No Inquiry): {email_in_msg}")
                        try:
                            self.update_booking_record(booking_record['id'], {FieldIds.CUSTOMER_PERSONAL_EMAIL: email_in_msg}, table_name=booking_record.get('table_name'))
                            # If human is active, we just update and return None? No, user might expect reply.
                            # But standard logic below will handle reply if needed.
                        except Exception as e:
                            logging.error(f"Failed to update email from WhatsApp: {e}")
            # ---------------------------------------------------------

        # Determine Customer Name (Smart Extraction)
        customer_name = "Guest"
        
        # 1. Try from Booking Record
        if booking_record:
            db_name = self.get_field_value(booking_record.get('fields', {}), FieldIds.CUSTOMER_NAME)
            if db_name:
                customer_name = db_name
        
        # 2. Try from AI Extraction (if DB is empty or still "Guest")
        if customer_name == "Guest" or not customer_name:
             ai_name = extracted_data.get('Customer Name')
             if ai_name:
                 customer_name = ai_name
                 
        # 3. Validate Name (Smart Check for Company/Generic Names)
        # If the name looks like a company or generic placeholder, revert to "Guest"
        if customer_name:
            name_clean = str(customer_name).strip()
            name_lower = name_clean.lower()
            
            # Blocklist of keywords that indicate non-human or generic
            company_keywords = [
                "viator", "expedia", "getyourguide", "gyg", "tripadvisor", "booking.com", 
                "tours", "travels", "travel", "agency", "limited", "ltd", "inc", "corp",
                "service", "support", "team", "reservation", "guest", "customer", "client",
                "unknown", "not provided", "n/a", "sir", "madam"
            ]
            
            is_invalid = False
            for kw in company_keywords:
                # Check if keyword is in the name (e.g. "Viator Customer Service")
                # OR if the name IS the keyword (e.g. "Guest")
                if kw in name_lower:
                    is_invalid = True
                    break
            
            if is_invalid:
                customer_name = "Guest"
            else:
                customer_name = name_clean

        # Create Lead record if needed
        if not booking_record and customer_email:
            # If we haven't found a valid name yet via AI, try sender email
            if customer_name == "Guest":
                if '<' in sender_identifier:
                    potential_name = sender_identifier.split('<')[0].strip().replace('"', '')
                    if '@' not in potential_name:
                         customer_name = potential_name
                elif '@' not in sender_identifier:
                    # Rare case where sender_identifier is just a name?
                    pass
            
            logging.info(f"No booking found for {customer_email}. Creating new Lead record.")
            booking_record = self.create_lead_record(customer_email, customer_name, message_body)
        
        # --- LOG USER MESSAGE IMMEDIATELY ---
        if booking_record:
            try:
                self.append_to_chat_log(
                    booking_record['id'], 
                    message_body, 
                    sender="User", 
                    source=source, 
                    table_name=booking_record.get('table_name')
                )
            except Exception as e:
                 logging.warning(f"Could not log user message for {booking_record['id']}: {e}")

        # CHECK HUMAN INTERVENTION (Pause AI if needed)
        # MOVED AFTER LOGGING AND EXTRACTION
        
        # If no structured history (e.g. WhatsApp), try to parse from Airtable Log
        if not history_list and booking_record:
            chat_log_db = self.get_field_value(booking_record.get('fields', {}), FieldIds.AI_CHAT_LOG) or ""
            history_list = self.parse_chat_log_to_history_list(chat_log_db)
            
        is_human_active, reason = self.check_human_intervention(history_list or [], customer_email or "unknown")
        if is_human_active:
            logging.info(f"Skipping thread/message {thread_id} (AI Paused): {reason}")
            # We already updated data and logged message. Now we just stop generating response.
            return None
        
        # Attachments Logic

        # Attachments Logic
        processed_attachments = []
        has_attachments = False
        if booking_record:
            fields_data = booking_record.get('fields', {})
            if fields_data:
                processed_attachments = self._get_valid_attachments(fields_data)
                has_attachments = len(processed_attachments) > 0

        kb_context_stub = self.get_kb_context(message_body)
        
        msg_lower = message_body.lower()
        user_wants_tickets = "ticket" in msg_lower and ("send" in msg_lower or "where" in msg_lower or "need" in msg_lower)
        is_pickup_query = "pickup" in msg_lower or "time" in msg_lower
        should_attach = has_attachments and (user_wants_tickets or is_pickup_query)
        
        # --- SMART MEMORY CONTEXT ---
        chat_log_db = ""
        if booking_record:
            chat_log_db = self.get_field_value(booking_record.get('fields', {}), FieldIds.AI_CHAT_LOG) or ""
        
        # --- HANDLE TEMPLATE BUTTON CLICKS (AUTOMATION) ---
        msg_normalized = message_body.strip().lower()
        system_instruction_override = None
        
        if "confirm pickup" in msg_normalized:
            system_instruction_override = "SYSTEM INSTRUCTION: The user clicked 'Confirm Pickup'. They have confirmed their pickup time. Reply by thanking them and confirming the schedule is locked. Do not ask for more info unless critical."
            
        elif "it was great!" in msg_normalized or "it was great" in msg_normalized: # Handle punctuation
            # Determine logic based on Provider and Rating
            is_external_agency = False
            agency_name = ""
            has_gyg_rating = False
            
            if booking_record:
                fields = booking_record.get('fields', {})
                # Get Agency
                agency_val = self.get_field_value(fields, FieldIds.AGENCY)
                if isinstance(agency_val, list):
                     agency_val = agency_val[0] if agency_val else ""
                agency_name = str(agency_val)
                
                # Check if FTS (Direct) or External
                # If agency is empty, assume direct or unknown -> Standard logic
                if agency_name and "fts" not in agency_name.lower():
                    is_external_agency = True
                
                # Get GYG Rating (Check if already rated)
                rating_val = self.get_field_value(fields, FieldIds.GYG_RATING)
                if rating_val: # If not None and not empty
                    has_gyg_rating = True

            if is_external_agency:
                if not has_gyg_rating:
                    system_instruction_override = f"SYSTEM INSTRUCTION: The user clicked 'It was great!' (Positive Feedback) via {agency_name}. Thank them warmly. Ask them to please leave a 5-star review on {agency_name} if they haven't already. Do NOT try to sell them another trip directly. Instead, suggest they can book with us again on {agency_name} by searching for our company name."
                else:
                    system_instruction_override = f"SYSTEM INSTRUCTION: The user clicked 'It was great!' (Positive Feedback) via {agency_name}. Thank them warmly for their kind words! Do NOT ask for a review (they already rated). Do NOT try to sell them another trip directly. Suggest they can book with us again on {agency_name} in the future."
            else:
                 # FTS / Direct / Default
                 system_instruction_override = "SYSTEM INSTRUCTION: The user clicked 'It was great!' (Positive Feedback). Thank them warmly. Ask if they would be willing to leave a 5-star review. You can also suggest they plan another trip with us!"
            
        elif "i had issues" in msg_normalized:
             system_instruction_override = "SYSTEM INSTRUCTION: The user clicked 'I had issues'. IMMEDIATE ACTION REQUIRED. Apologize sincerely for the bad experience. State that you are escalating this to the Quality Manager immediately. YOU MUST APPEND '[ESCALATE]' to your response."
        
        elif "send details now" in msg_normalized:
             system_instruction_override = "SYSTEM INSTRUCTION: The user clicked 'Send Details Now' (Automated response). This means they have likely received our request for details. Acknowledge this by saying: 'Thank you. Please reply with the requested details (like Hotel Name or Room Number) here, and we will update your booking immediately.' If they have already attached details, confirm receipt."
             
        elif "confirm i have paid" in msg_normalized:
             # Payment Confirmation Logic
             logging.info("Detected Payment Confirmation Click.")
             if booking_record:
                 inv_status = self.get_field_value(booking_record.get('fields', {}), FieldIds.INVOICE_STATUS)
                 logging.info(f"Invoice Status: {inv_status}")
                 
                 if inv_status == "Done" or inv_status == "Paid" or inv_status == "succeeded":
                     system_instruction_override = "SYSTEM INSTRUCTION: The user clicked 'Confirm I have paid'. Our system shows Invoice Status is 'Done'. Reply: 'Payment confirmed! Thank you. We have received your payment and your booking is secure. We will send your final voucher shortly.'"
                 else:
                     # Still Pending
                     system_instruction_override = "SYSTEM INSTRUCTION: The user clicked 'Confirm I have paid', but our system shows the payment is still Pending. Reply: 'Thank you for the update. We are currently verifying the transaction with our bank. Once confirmed (usually within minutes), we will send you the final confirmation. If you have a receipt, feel free to share it here.'"
             else:
                 system_instruction_override = "SYSTEM INSTRUCTION: The user clicked 'Confirm I have paid'. Acknowledge the notification and state that we are checking the status."

        elif "can't pay" in msg_normalized or "cannot pay" in msg_normalized or "payment fails" in msg_normalized or "payment failed" in msg_normalized or "pay link" in msg_normalized or "unable to pay" in msg_normalized or "cant pay" in msg_normalized:
             # Payment Issue Logic
             logging.info("Detected Payment Issue in User Message.")
             if booking_record:
                 inv_status = self.get_field_value(booking_record.get('fields', {}), FieldIds.INVOICE_STATUS)
                 logging.info(f"Invoice Status: {inv_status}")
                 
                 if inv_status == "succeeded":
                     system_instruction_override = "SYSTEM INSTRUCTION: The user is reporting payment issues, but our system shows the invoice status is 'succeeded'. Inform the user that the payment has already been received successfully. If they believe this is an error, ask for a screenshot."
                 else:
                     # Trigger Invoice Generation
                     gen_url = self.get_field_value(booking_record.get('fields', {}), FieldIds.GENERATE_INVOICE)
                     logging.info(f"Generate Invoice URL found: {gen_url}")
                     
                     if gen_url and str(gen_url).startswith("http"):
                         try:
                             logging.info(f"Triggering Invoice Generation Webhook: {gen_url}")
                             # Fire and forget? Or wait? 5s timeout is fine.
                             requests.get(str(gen_url).strip(), timeout=5)
                             system_instruction_override = "SYSTEM INSTRUCTION: The user reported payment issues. I have automatically triggered the system to generate a NEW invoice link. Inform the user: 'I have generated a new invoice link for you. You will receive it via email/WhatsApp shortly. Please try the new link.' Do NOT ask them to wait for a human."
                         except Exception as e:
                             logging.error(f"Failed to trigger invoice webhook: {e}")
                             system_instruction_override = "SYSTEM INSTRUCTION: The user reported payment issues. I tried to generate a new invoice but failed. Please [ESCALATE] to Operations."
                     else:
                         logging.warning("No Generate Invoice URL found in booking record.")
                         system_instruction_override = "SYSTEM INSTRUCTION: The user reported payment issues, but I could not find the invoice generation link. Please [ESCALATE] to Operations to send a manual invoice."
             else:
                 logging.warning("Payment issue detected but NO booking record found.")


        full_smart_history = self.get_session_memory(customer_email, chat_log_db)
        if len(full_smart_history) < 50: 
             full_smart_history = history_text
        
        full_conversation_history = f"""
        FULL CONVERSATION HISTORY (Review Carefully):
        {history_text}
        
        PREVIOUS SYSTEM LOGS:
        {full_smart_history}
        """
        
        if system_instruction_override:
            full_conversation_history += f"\n\n{system_instruction_override}\n"

        response_text = self.generate_smart_reply(
            history_text=full_conversation_history, 
            kb_context=kb_context_stub, 
            latest_message_body=message_body,
            booking_record=booking_record
        )
        
        # Update Session Cache with AI Reply
        self.update_session_memory(customer_email, response_text, role="assistant")
        
        # Extract Department & Intent
        escalation_dept = "SUPPORT"
        inquiry_intent = "OTHER"

        # Independent Extraction of Tags (Robust to order)
        if "[INTENT:" in response_text:
            try:
                parts = response_text.split("[INTENT:")
                # Take the part after [INTENT: and before the next closing bracket
                val_part = parts[1].split("]")[0].strip()
                inquiry_intent = val_part
                # Remove tag from text
                response_text = response_text.replace(f"[INTENT:{val_part}]", "").replace(f"[INTENT: {val_part}]", "").strip()
            except Exception as e:
                logging.warning(f"Error parsing INTENT tag: {e}")

        if "[DEPT:" in response_text:
            try:
                parts = response_text.split("[DEPT:")
                val_part = parts[1].split("]")[0].strip()
                escalation_dept = val_part
                # Remove tag from text
                response_text = response_text.replace(f"[DEPT:{val_part}]", "").replace(f"[DEPT: {val_part}]", "").strip()
            except Exception as e:
                logging.warning(f"Error parsing DEPT tag: {e}")

        # Remove [LANG: ...] and [TRANS: ...] tags | إزالة علامات اللغة والترجمة
        try:
            # استخدام Regex مع DOTALL لإزالة العلامات حتى لو كانت متعددة الأسطر
            response_text = re.sub(r'\[LANG:.*?\]', '', response_text, flags=re.IGNORECASE | re.DOTALL).strip()
            response_text = re.sub(r'\[TRANS:.*?\]', '', response_text, flags=re.IGNORECASE | re.DOTALL).strip()
            # إزالة علامات القسم والنية النهائية لضمان نظافة النص تماماً
            response_text = re.sub(r'\[DEPT:.*?\]', '', response_text, flags=re.IGNORECASE).strip()
            response_text = re.sub(r'\[INTENT:.*?\]', '', response_text, flags=re.IGNORECASE).strip()
        except Exception as e:
            logging.warning(f"Error removing LANG/TRANS tags: {e}")
                
        # Fallback: If no DEPT tag but intent is known, map it
        if escalation_dept == "SUPPORT" and inquiry_intent != "OTHER":
            if inquiry_intent in ["PICKUP_QUERY", "INFO_UPDATE", "LOST_ITEM"]:
                escalation_dept = "OPERATIONS"
            elif inquiry_intent in ["COMPLAINT", "URGENT_ISSUE"]:
                escalation_dept = "QUALITY"
            elif inquiry_intent in ["TRIP_INFO_QUERY"]:
                escalation_dept = "SALES"

        # Check for Escalation or Details Update
        was_escalated = False
        if "[ESCALATE]" in response_text:
            was_escalated = True
            logging.info(f"Response requires escalation to {escalation_dept}.")
            response_text = response_text.replace("[ESCALATE]", "").strip()
            
            fields_for_ops = booking_record.get('fields', {}) if booking_record else {}
            other_contacts = None
            if not booking_record:
                 other_contacts = self.extract_contact_from_text(history_text, message_body)
            self.notify_operations(fields_for_ops, message_body, response_text, sender_email=customer_email, other_contacts=other_contacts, department=escalation_dept)
        
        if "[UPDATE_DETAILS]" in response_text:
            logging.info("Message contains new details. Notifying Operations.")
            response_text = response_text.replace("[UPDATE_DETAILS]", "").strip()
            fields_for_ops = booking_record.get('fields', {}) if booking_record else {}
            self.notify_operations(fields_for_ops, message_body, "Customer provided new details. Please update Airtable.", sender_email=customer_email, department="OPERATIONS")

        # Log Proposed Reply (Learning)
        if booking_record:
             try:
                 self.log_proposed_reply_for_learning(booking_record['id'], response_text, table_name=booking_record.get('table_name'))
             except Exception as e:
                 logging.warning(f"Could not log proposed reply for learning: {e}")

        return {
            "response_text": response_text,
            "booking_record": booking_record,
            "attachments": processed_attachments if should_attach else [],
            "was_escalated": was_escalated,
            "escalation_dept": escalation_dept,
            "inquiry_intent": inquiry_intent,
            "customer_name": customer_name,
            "customer_email": customer_email
        }

    def process_whatsapp_message(self, sender_phone, message_body, sender_name, phone_id=None, timestamp=None):
        """
        Handle incoming WhatsApp message.
        Learning Only: Does not send reply, but logs and updates system state.
        """
        location = "Unknown"
        if phone_id == "565029450024439":
            location = "Hurghada/Cairo"
        elif phone_id == "566664693192786":
            location = "Sharm"
            
        logging.info(f"Processing WhatsApp message from {sender_name} ({sender_phone}) for {location}")
        
        # Determine Message Time
        msg_time = datetime.now()
        if timestamp:
            try:
                # WhatsApp timestamp is usually unix timestamp string
                msg_time = datetime.fromtimestamp(int(timestamp))
            except:
                pass
        
        # Check for Stale Messages (e.g. Server was down/sleeping)
        # If message is older than 1 hour, we log it but do NOT generate a new draft/response to avoid confusion
        time_diff = datetime.now() - msg_time
        if time_diff.total_seconds() > 3600: # 1 Hour
             logging.warning(f"STALE MESSAGE DETECTED: Message from {sender_name} is {time_diff.total_seconds()/3600:.1f} hours old. Skipping AI processing.")
             # We can still log it to history if needed, but for now we skip to avoid the "Late Reply" issue.
             return

        history_text = f"[{msg_time.strftime('%Y-%m-%d %H:%M:%S')}] {sender_name} (via WhatsApp {location}): {message_body}"
        
        # Call Unified Processor
        # Note: We are reverting the lock mechanism as requested.
        # Original simple call:
        result = self.process_unified_message(
            sender_identifier=sender_phone,
            message_body=message_body,
            history_text=history_text,
            source="WhatsApp",
            subject=f"WhatsApp Message ({location})"
        )
        
        if result:
            logging.info(f"WhatsApp processing complete. AI Response (Learning Mode - Not Sent): {result['response_text']}")
            
            # --- FIX: Update Inquiry Type for WhatsApp ---
            if result.get('booking_record') and result.get('inquiry_intent'):
                booking_record = result['booking_record']
                inquiry_intent = result['inquiry_intent']
                
                try:
                    self.update_booking_record(
                        booking_record['id'], 
                        {FieldIds.INQUIRY_TYPE: inquiry_intent}, 
                        table_name=booking_record.get('table_name')
                    )
                    logging.info(f"Updated Inquiry Type for WhatsApp message: {inquiry_intent}")
                except Exception as e:
                    logging.error(f"Failed to update Inquiry Type for WhatsApp: {e}")
                    # Fallback to Note
                    try:
                        current_note = self.get_field_value(booking_record.get('fields', {}), FieldIds.NOTE) or ""
                        if f"[Inquiry: {inquiry_intent}]" not in current_note:
                            new_note = f"{current_note}\n[Inquiry: {inquiry_intent}]".strip()
                            self.update_booking_record(booking_record['id'], {FieldIds.NOTE: new_note}, table_name=booking_record.get('table_name'))
                    except:
                        pass
                        
                # --- MAKE WEBHOOK NOTIFICATION (For Driver Delay / Waiting Issues) - WHATSAPP VERSION ---
                try:
                    # Check keywords
                    msg_lower = message_body.lower()
                    is_waiting_issue = "ready" in msg_lower or "waiting" in msg_lower or "where" in msg_lower or "late" in msg_lower or "arrive" in msg_lower
                    
                    if is_waiting_issue:
                        # Check Pickup Time
                        pickup_time_str = self.get_field_value(booking_record.get('fields', {}), FieldIds.PICKUP_TIME)
                        if pickup_time_str:
                            now_cairo = datetime.utcnow() + CAIRO_OFFSET
                            
                            try:
                                # Normalize time string
                                # Support 24h (HH:MM) and 12h (HH:MM AM/PM)
                                pt_obj = None
                                try:
                                    pt_obj = datetime.strptime(pickup_time_str, "%H:%M").time()
                                except:
                                    try:
                                        pt_obj = datetime.strptime(pickup_time_str, "%I:%M %p").time()
                                    except:
                                        # Try without leading zero or space
                                        pt_obj = datetime.strptime(pickup_time_str, "%I:%M%p").time()
                                
                                if pt_obj:
                                    now_time = now_cairo.time()
                                    if now_time >= pt_obj:
                                        # TRIGGER WEBHOOK
                                        webhook_url = "https://hook.us2.make.com/hh1j7h7gbc3g1crf0gf6p9ve5darktqw"
                                        
                                            # Use a simpler customer name for payload if available
                                        customer_name_payload = result.get('customer_name', "Guest")
                                        
                                        payload = {
                                            "booking_id": booking_record['id'],
                                            "customer_name": customer_name_payload,
                                            "pickup_time": pickup_time_str,
                                            "user_message": message_body,
                                            "source": "WhatsApp",
                                            "timestamp": now_cairo.strftime("%Y-%m-%d %H:%M:%S"),
                                            "booking_data": booking_record.get('fields', {})
                                        }
                                        
                                        import requests
                                        requests.post(webhook_url, json=payload, timeout=2)
                                        logging.info(f"Triggered Driver Alert Webhook (WhatsApp) for {booking_record['id']}")
                                    
                            except Exception as e:
                                logging.warning(f"Time parsing failed for webhook check (WhatsApp): {e}")

                except Exception as e:
                    logging.error(f"Error in Webhook Logic (WhatsApp): {e}")
                # ---------------------------------------------------------------------

    def run_webhook_server(self):
        app = Flask(__name__)
        
        @app.route('/webhook', methods=['GET'])
        def verify_webhook():
            mode = request.args.get('hub.mode')
            token = request.args.get('hub.verify_token')
            challenge = request.args.get('hub.challenge')
            VERIFY_TOKEN = self.config.get('whatsapp', {}).get('verify_token', 'EAALCJ9i07dIBQe5BnokFM5gUCDXSFTfj8p98kfBFXhsHa0BDDZCeiXIQLZCWy0CgaOaGPvZCV4yzolGCLkLpcD1H5oOpLbYS3yWGXZBt5yRjxrFkHlqsOfTsxRgj8XNMsd5HetMz0SSBZB9GDgZBUU2BSR33BHllKKZAS7WBLquUQmTewslv8ZCOxMkWdvY8QQZDZD')
            if mode and token:
                if mode == 'subscribe' and token == VERIFY_TOKEN:
                    return challenge, 200
                else:
                    return 'Forbidden', 403
            return 'Hello World', 200

        @app.route('/webhook', methods=['POST'])
        def webhook():
            try:
                # --- DEBUGGING & PAYLOAD INSPECTION ---
                # Log the content type to help debug Form vs JSON issues
                logging.info(f"Webhook received. Content-Type: {request.content_type}")
                
                is_kommo = False
                kommo_data = {}

                # 1. Check Form Data for Kommo (Standard)
                if request.form and 'message[add][0][id]' in request.form:
                    # ... (Existing Form Data Logic) ...
                    is_kommo = True
                    kommo_data = {
                        'id': request.form.get('message[add][0][id]'),
                        'text': request.form.get('message[add][0][text]'),
                        'type': request.form.get('message[add][0][type]'),
                        'chat_id': request.form.get('message[add][0][chat_id]')
                    }
                
                # 2. Check JSON Data for Kommo (Alternative)
                elif request.is_json:
                    try:
                        json_data = request.get_json(silent=True) or {}
                        
                        # FORCE LOGGING TO SEE STRUCTURE (Temporary Debug)
                        logging.info(f"DEBUG: Full JSON Payload: {json_data}")
                        
                        # Check for structure: {'message': {'add': [{'id': ...}]}}
                        if 'message' in json_data and 'add' in json_data['message']:
                             adds = json_data['message']['add']
                             if isinstance(adds, list) and len(adds) > 0:
                                 item = adds[0]
                                 if 'id' in item:
                                     is_kommo = True
                                     kommo_data = {
                                         'id': item.get('id'),
                                         'text': item.get('text'),
                                         'type': item.get('type'),
                                         'chat_id': item.get('chat_id')
                                     }
                        # Also check account[id] usually present in Kommo
                        elif 'account' in json_data and 'id' in json_data['account']:
                             # It might be a different event structure
                             # logging.info(f"Kommo Event Detected (Structure 2): {json_data.keys()}")
                             # Check for 'message' key directly
                             if 'message' in json_data and 'add' in json_data['message']:
                                 adds = json_data['message']['add']
                                 if isinstance(adds, list) and len(adds) > 0:
                                     item = adds[0]
                                     is_kommo = True
                                     kommo_data = {
                                         'id': item.get('id'),
                                         'text': item.get('text'),
                                         'type': item.get('type'),
                                         'chat_id': item.get('chat_id')
                                     }
                             # Also check for 'leads' structure with notes/messages
                             elif 'leads' in json_data:
                                 # Sometimes Kommo sends message as a note on a lead
                                 pass
                             
                    except Exception as e:
                        logging.warning(f"Error checking for Kommo JSON: {e}")

                if is_kommo:
                    # It is Kommo!
                    msg_id = kommo_data.get('id')
                    msg_text = kommo_data.get('text')
                    msg_type = kommo_data.get('type') # 'out' = agent reply, 'in' = user
                    chat_id = kommo_data.get('chat_id') # Usually phone
                    
                    if msg_type == 'out':
                        logging.info(f"Received Kommo Agent Reply: {msg_text} to {chat_id}")
                        # Treat as Human Echo
                        # We need to find the booking record to log it
                        # Attempt to find booking by phone (chat_id)
                        
                        # Normalize phone
                        norm_phone = self.normalize_phone_for_search(chat_id)
                        
                        # Find record
                        booking_record = self.find_booking_by_phone(norm_phone)
                        
                        if booking_record:
                             try:
                                 self.append_to_chat_log(
                                     booking_record['id'], 
                                     msg_text, 
                                     sender="Human Agent", 
                                     source="Kommo", 
                                     table_name=booking_record.get('table_name')
                                 )
                                 logging.info(f"Logged Kommo Agent Reply for {booking_record['id']}")
                             except Exception as e:
                                 logging.error(f"Failed to log Kommo Agent Reply: {e}")
                        else:
                            logging.warning(f"Could not find booking for Kommo echo: {chat_id}")
                            
                    return 'OK', 200

                # Assume WhatsApp if not Kommo
                data = request.get_json(silent=True)
                if not data:
                    logging.warning("Webhook received non-JSON data that is not Kommo.")
                    return 'Bad Request', 400
                
                # Check structure for Meta Cloud API
                if 'entry' not in data or not data.get('entry'):
                    # Not a standard Meta payload (and not Kommo form-data or json)
                    logging.warning(f"Unknown JSON payload structure: {data.keys()}")
                    return 'OK', 200 # Return 200 to acknowledge and stop retries

                # logging.info(f"WhatsApp Webhook received: {data}") # Reduce noise
                entry = data.get('entry', [])[0]
                changes = entry.get('changes', [])[0]
                value = changes.get('value', {})
                
                phone_id = value.get('metadata', {}).get('phone_number_id')
                messages = value.get('messages', [])
                
                if messages:
                    # Iterate through ALL messages in the batch, not just the first one
                    for msg in messages:
                        # --- CHECK FOR ECHO (Agent Reply) ---
                        # According to Meta docs for 'smb_message_echoes' or 'message_echoes',
                        # the message object usually contains 'is_echo': True (for Instagram/Messenger) 
                        # OR for WhatsApp, it might be inferred if the 'from' matches the business ID (less common in Cloud API).
                        # However, typical structure for Cloud API Echoes isn't always standard 'messages' list.
                        # BUT assuming it comes in 'messages' list:
                        
                        # Check if it's a system message or echo
                        # 1. 'from' is the customer phone (Standard User Message)
                        # 2. If we subscribed to 'message_echoes', we might get messages where we are the sender.
                        
                        # Let's inspect for 'metadata' or specific flags if we could. 
                        # Since we don't have the exact payload example, we'll implement a robust check.
                        
                        # NOTE: In standard Cloud API, outgoing messages don't usually come back to webhook unless explicitly subscribed to specific echo fields.
                        # If 'from' == phone_id (Our Business ID), then it is US replying.
                        
                        sender_id = msg.get('from')
                        is_echo = False
                        
                        # Check logic: If sender_id matches our phone_id (Business ID), it's an echo.
                        # phone_id might be different from sender_id if using WABA ID vs Phone ID.
                        # Usually sender_id (from) is the Phone Number ID of the sender.
                        
                        if sender_id and phone_id and str(sender_id) == str(phone_id):
                            is_echo = True
                            
                        # Also check explicit 'is_echo' flag (Requested by User)
                        if msg.get('is_echo') or (value.get('metadata', {}).get('display_phone_number') == sender_id):
                            is_echo = True
                            
                        if is_echo:
                             # THIS IS AN AGENT REPLY (Human or System)
                             recipient_id = msg.get('to') # The customer phone
                             
                             # Extract body based on type
                             echo_type = msg.get('type')
                             echo_body = ""
                             
                             if echo_type == 'text':
                                 echo_body = msg.get('text', {}).get('body', '')
                             elif echo_type == 'template':
                                 template_name = msg.get('template', {}).get('name', 'Unknown')
                                 echo_body = f"[Sent Template: {template_name}]"
                             elif echo_type == 'image':
                                 caption = msg.get('image', {}).get('caption', '')
                                 echo_body = f"[Sent Image] {caption}".strip()
                             elif echo_type == 'document':
                                 caption = msg.get('document', {}).get('caption', '')
                                 filename = msg.get('document', {}).get('filename', '')
                                 echo_body = f"[Sent Document: {filename}] {caption}".strip()
                             elif echo_type == 'interactive':
                                 # Interactive messages from Agent are usually List or Button messages sent to user
                                 interactive = msg.get('interactive', {})
                                 int_type = interactive.get('type')
                                 if int_type == 'button': # Sending a button message
                                     text_body = interactive.get('body', {}).get('text', '')
                                     echo_body = f"[Sent Interactive Button] {text_body}"
                                 else:
                                     echo_body = f"[Sent Interactive Message: {int_type}]"
                             else:
                                 echo_body = f"[Sent Message: {echo_type}]"
                             
                             if recipient_id and echo_body:
                                 logging.info(f"Captured Agent Reply (Echo) to {recipient_id}: {echo_body}")
                                 
                                 try:
                                     # Find booking by Recipient (Customer)
                                     # We need to clean the recipient id first? usually it is just digits
                                     rec = self.find_booking_by_contact(phone=recipient_id)
                                     
                                     if rec:
                                         self.append_to_chat_log(
                                             rec['id'], 
                                             echo_body, 
                                             sender="Human Agent", 
                                             source="WhatsApp_Echo", 
                                             table_name=rec.get('table_name')
                                         )
                                         logging.info(f"Logged Human Agent Reply for {rec['id']}")
                                 except Exception as ex:
                                     logging.error(f"Failed to log Agent Reply: {ex}")
                                     
                        else:
                            # STANDARD USER MESSAGE
                            sender_phone = msg.get('from')
                            sender_name = value.get('contacts', [{}])[0].get('profile', {}).get('name', 'Unknown')
                            timestamp = msg.get('timestamp') # Extract timestamp
                            
                            # Extract message body based on type (Text, Button, Interactive)
                            msg_type = msg.get('type')
                            msg_body = ""
                            
                            if msg_type == 'text':
                                msg_body = msg.get('text', {}).get('body', '')
                            elif msg_type == 'button':
                                msg_body = msg.get('button', {}).get('text', '')
                                logging.info(f"Received Button Reply from {sender_name}: {msg_body}")
                            elif msg_type == 'interactive':
                                interactive = msg.get('interactive', {})
                                int_type = interactive.get('type')
                                if int_type == 'button_reply':
                                    msg_body = interactive.get('button_reply', {}).get('title', '')
                                    logging.info(f"Received Interactive Button Reply from {sender_name}: {msg_body}")
                                elif int_type == 'list_reply':
                                    msg_body = interactive.get('list_reply', {}).get('title', '')
                                    logging.info(f"Received List Reply from {sender_name}: {msg_body}")
                            
                            if msg_body:
                                # Process each message in the batch individually
                                self.process_whatsapp_message(sender_phone, msg_body, sender_name, phone_id, timestamp=timestamp)
                            else:
                                logging.warning(f"Unhandled message type or empty body from {sender_phone}: {msg_type}")
                
                # --- NEW: HANDLE MESSAGE ECHOES (Agent Replies) ---
                # Based on user sample: smb_message_echoes (v24.0)
                # Field: "smb_message_echoes" (or similar)
                # Value structure: { messaging_product, metadata, message_echoes: [...] }
                
                # Check if this change is for 'message_echoes' or 'smb_message_echoes'
                field_name = changes.get('field', '')
                
                if field_name in ['message_echoes', 'smb_message_echoes']:
                     # This IS an echo payload!
                     echoes = value.get('message_echoes', [])
                     if echoes:
                         for echo in echoes:
                             # Extract data
                             recipient_id = echo.get('to') # The customer phone
                             echo_type = echo.get('type')
                             echo_body = ""
                             
                             if echo_type == 'text':
                                 echo_body = echo.get('text', {}).get('body', '')
                             elif echo_type == 'template':
                                 template_name = echo.get('template', {}).get('name', 'Unknown')
                                 echo_body = f"[Sent Template: {template_name}]"
                             elif echo_type == 'image':
                                 caption = echo.get('image', {}).get('caption', '')
                                 echo_body = f"[Sent Image] {caption}".strip()
                             else:
                                 echo_body = f"[Sent Message: {echo_type}]"
                                 
                             if recipient_id and echo_body:
                                 logging.info(f"Captured Agent Reply (Echo via {field_name}) to {recipient_id}: {echo_body}")
                                 
                                 try:
                                     rec = self.find_booking_by_contact(phone=recipient_id)
                                     if rec:
                                         self.append_to_chat_log(
                                             rec['id'], 
                                             echo_body, 
                                             sender="Human Agent", 
                                             source="WhatsApp_Echo", 
                                             table_name=rec.get('table_name')
                                         )
                                         logging.info(f"Logged Human Agent Reply for {rec['id']}")
                                 except Exception as ex:
                                     logging.error(f"Failed to log Echo Reply: {ex}")
                     return 'OK', 200

                statuses = value.get('statuses', [])
                if statuses:
                    # Message Status Update (Sent, Delivered, Read)
                    logging.info(f"DEBUG: Received Status Update: {statuses}")
                    pass

            except Exception as e:
                logging.error(f"Error processing webhook: {e}")
                import traceback
                traceback.print_exc()
            return 'EVENT_RECEIVED', 200

        # Endpoint to serve OpenAPI Specification
        @app.route('/openapi.json', methods=['GET'])
        def serve_openapi_spec():
            from flask import send_from_directory
            import os
            return send_from_directory(os.getcwd(), 'openapi.json')

        # Tawk.to Webhook Endpoint
        @app.route('/tawkto-webhook', methods=['POST'])
        def tawkto_webhook():
            try:
                data = request.json
                # --- LOGGING RAW PAYLOAD FOR DEBUGGING ---
                print("\n=== INCOMING TAWK.TO PAYLOAD ===")
                import json
                print(json.dumps(data, indent=2))
                print("==================================\n")
                # ----------------------------------------
                
                event_type = data.get('event')
                
                # We process chat messages from visitors (both 'chat:message' and 'chat:start')
                if event_type in ['chat:message', 'chat:start']:
                    message_data = data.get('message', {})
                    visitor_data = data.get('visitor', {})
                    
                    sender_type = message_data.get('sender', {}).get('type')
                    
                    # Ignore messages from agents or system to avoid loops
                    if sender_type == 'visitor':
                        msg_body = message_data.get('text')
                        sender_name = visitor_data.get('name', 'Guest')
                        sender_email = visitor_data.get('email')
                        sender_phone = visitor_data.get('phone') # Extract phone if available
                        chat_id = data.get('chatId')
                        
                        # Identifier: Prefer Email, then Phone, then Chat ID
                        sender_identifier = sender_email if sender_email else (sender_phone if sender_phone else f"tawk_{chat_id}")
                        
                        logging.info(f"Processing Tawk.to message from {sender_name} ({sender_identifier})")
                        
                        history_text = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {sender_name} (via Tawk.to): {msg_body}"
                        
                        # Call Unified Processor
                        # For Tawk.to, we want to ensure we ALWAYS reply and treat it as a potential lead.
                        # The system prompt has been updated to handle Tawk.to visitors strictly.
                        
                        result = self.process_unified_message(
                            sender_identifier=sender_identifier,
                            message_body=msg_body,
                            history_text=history_text,
                            source="Tawk.to",
                            subject=f"Tawk.to Chat from {sender_name}"
                        )
                        
                        if result:
                            response_text = result['response_text']
                            logging.info(f"Tawk.to Response generated: {response_text}")
                            
                            # --- SEND NOTIFICATION TO SALES TEAM (MAKE.COM) ---
                            def send_sales_notification():
                                try:
                                    sales_webhook_url = "https://hook.us2.make.com/bso4hyqvegkvi849enujxafqqtcxmasp"
                                    
                                    # Detect Language (Basic heuristic or passed from AI result)
                                    # Assuming result has 'language_code' or we infer it.
                                    # For now, let's use a simple langdetect if available, or just send the text for Make to process.
                                    # Better: Ask AI to output language in the unified result.
                                    
                                    payload = {
                                        "source": "Tawk.to",
                                        "sender_name": sender_name,
                                        "sender_email": sender_email,
                                        "sender_phone": sender_phone,
                                        "chat_id": chat_id,
                                        "message": msg_body,
                                        "ai_response": response_text,
                                        "timestamp": datetime.now().isoformat(),
                                        "intent": result.get('inquiry_intent'),
                                        "department": result.get('escalation_dept'),
                                        "was_escalated": result.get('was_escalated'),
                                        # New Fields for Translation
                                        "customer_language": result.get('detected_language', 'Unknown'),
                                        "message_english_translation": result.get('english_translation', msg_body) # AI should provide this
                                    }
                                    requests.post(sales_webhook_url, json=payload)
                                    logging.info(f"Notification sent to Sales Team Webhook for {sender_name}")
                                except Exception as wh_err:
                                    logging.error(f"Failed to send Sales Notification: {wh_err}")

                            # Run in a separate thread to avoid blocking the response
                            threading.Thread(target=send_sales_notification).start()
                            # --------------------------------------------------

                            # Return response in JSON compatible with MCP and OpenAPI
                            # NOTE: Standard Tawk.to Webhooks (Admin -> Webhooks) are ONE-WAY and ignore this response.
                            # This only works if using an OpenAPI/MCP connector or Client-side bridge.
                            return jsonify({
                                "reply": response_text, # Standard field for Tawk.to MCP
                                "message": response_text, # Fallback
                                "text": response_text, # Fallback
                                "data": {
                                    "content": response_text # Another common variation
                                },
                                "status": "success"
                            }), 200
                        
                return jsonify({"status": "ignored"}), 200
                
            except Exception as e:
                logging.error(f"Error processing Tawk.to webhook: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        port = self.config.get('whatsapp', {}).get('port', 5001)
        # host='0.0.0.0' makes the server accessible externally
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

    def process_incoming_emails(self):
        """
        Check for new emails (Channel: Email)
        """
        logging.info("Checking for new emails...")
        
        email_config = self.config.get('email', {})
        labels_config = email_config.get('labels', {})
        search_label_name = labels_config.get('search_label')
        processed_label_name = labels_config.get('processed_label')
        
        if not search_label_name or not processed_label_name:
            logging.error("Email labels not configured properly.")
            return

        # Get Label IDs
        search_label_id = self.gmail_service.get_label_id_by_name(search_label_name)
        processed_label_id = self.gmail_service.get_label_id_by_name(processed_label_name)
        
        # Get Sharm Label ID
        sharm_label_name = labels_config.get('sharm_label')
        sharm_label_id = None
        if sharm_label_name:
            sharm_label_id = self.gmail_service.get_label_id_by_name(sharm_label_name)
        
        if not search_label_id and not sharm_label_id:
            logging.warning(f"Search labels not found in Gmail.")
            # Continue if Inbox search is enabled, otherwise return
            if not email_config.get('settings', {}).get('search_in_inbox', False):
                return
            
        # Get unread threads
        threads = []
        
        # 1. Search Configured Label
        if search_label_id:
             # Add newer_than:2d to filter out old emails from the search result itself
             label_threads = self.gmail_service.get_unread_threads(search_label_id, max_results=500, query_q="newer_than:2d")
             threads.extend(label_threads)

        # 1.5 Search Sharm Label
        if sharm_label_id:
             logging.info(f"Searching '{sharm_label_name}' for unread emails...")
             # Add newer_than:2d to filter out old emails from the search result itself
             sharm_threads = self.gmail_service.get_unread_threads(sharm_label_id, max_results=500, query_q="newer_than:2d")
             # Deduplicate
             existing_ids = {t['id'] for t in threads}
             for t in sharm_threads:
                 if t['id'] not in existing_ids:
                     threads.append(t)

             
        # 2. Search Inbox (if enabled)
        if email_config.get('settings', {}).get('search_in_inbox', False):
             logging.info("Searching INBOX for unread emails...")
             # Add newer_than:2d to filter out old emails from the search result itself
             inbox_threads = self.gmail_service.get_unread_threads('INBOX', max_results=500, query_q="newer_than:2d")
             
             # Deduplicate
             existing_ids = {t['id'] for t in threads}
             for t in inbox_threads:
                 if t['id'] not in existing_ids:
                     threads.append(t)

        # SORT THREADS: Oldest to Newest (based on historyId)
        # This ensures we process older messages first if multiple are waiting.
        if threads:
            threads.sort(key=lambda x: int(x.get('historyId', 0)))
        
        if not threads:
            logging.info("No new emails found.")
            return

        kb_context_stub = ""

        for thread in threads:
            try:
                thread_id = thread['id']
                # Get full thread history for context
                history = self.gmail_service.get_thread_history(thread_id)
                
                if not history:
                    continue
                
                # Latest message is the last one in the list
                latest_msg = history[-1]
                
                # --- NEW EMAIL CHECK: Skip Old Emails ---
                # Check if the email is older than X hours (e.g. 24 hours) to avoid replying to ancient history
                # This is a safety check.
                try:
                    msg_date_str = latest_msg.get('date')
                    # Parse date (Format: "Tue, 15 Nov 2024 10:00:00 +0200" or similar)
                    # We use dateutil.parser if available or simple check
                    from email.utils import parsedate_to_datetime
                    msg_dt = parsedate_to_datetime(msg_date_str)
                    
                    if msg_dt.tzinfo:
                        now_aware = datetime.now(msg_dt.tzinfo)
                        diff = now_aware - msg_dt
                    else:
                        diff = datetime.utcnow() - msg_dt

                    # If email is older than 24 hours, skip it (Mark as processed only?)
                    # Or just ignore it. Let's Mark as Processed to stop it from appearing again.
                    if diff.total_seconds() > 24 * 3600:
                        logging.warning(f"Skipping old email from {latest_msg.get('sender')} (Date: {msg_date_str}). Too old to process.")
                        
                        # Remove labels so we don't fetch it again
                        remove_labels_list = []
                        if search_label_id: remove_labels_list.append(search_label_id)
                        if sharm_label_id: remove_labels_list.append(sharm_label_id)
                        
                        self.gmail_service.modify_thread_labels(thread_id, remove_labels=remove_labels_list)
                        continue

                except Exception as e:
                    logging.warning(f"Date parsing failed for email check: {e}. Processing anyway.")

                sender = latest_msg['sender']
                subject = latest_msg.get('subject', 'No Subject') 
                
                body = latest_msg['body']
                
                logging.info(f"Processing email from {sender}")
                
                # --- SPECIAL IGNORE: GetYourGuide Reviews ---
                # "You have a new review on GetYourGuide"
                if "new review on getyourguide" in subject.lower():
                    logging.info("Skipping GetYourGuide Review Notification.")
                    # Mark as processed to remove from queue
                    remove_labels_list = []
                    if search_label_id: remove_labels_list.append(search_label_id)
                    if sharm_label_id: remove_labels_list.append(sharm_label_id)
                    
                    self.gmail_service.modify_thread_labels(thread_id, remove_labels=remove_labels_list)
                    continue

                # --- SPECIAL IGNORE: Prevent Infinite Loop from GYG Auto-Forwards ---
                if "your activity provider sent you a message" in body.lower():
                    logging.info("Skipping GYG Auto-Forward of our own reply to prevent infinite loop.")
                    remove_labels_list = []
                    if search_label_id: remove_labels_list.append(search_label_id)
                    if sharm_label_id: remove_labels_list.append(sharm_label_id)
                    
                    # Add processed label so it doesn't get picked up again
                    self.gmail_service.modify_thread_labels(thread_id, add_labels=[processed_label_id] if processed_label_id else [], remove_labels=remove_labels_list)
                    continue

                # --- CHECK FOR SUPPLIER BOOKING EMAIL ---
                supplier_agency = self.check_if_supplier_email(sender, subject, body)
                if supplier_agency:
                    # --- AUTO-CONFIRM RECEIPT FOR GETYOURGUIDE ---
                    if supplier_agency == 'GetYourGuide':
                         try:
                             # Regex to find "Confirm receipt" link
                             # Matches: Confirm receipt (http...) from HTML conversion or Confirm receipt ... http...
                             # We use DOTALL to match across newlines if needed, but usually it's close.
                             confirm_match = re.search(r"Confirm receipt.*?((?:https?://|www\.)[^\s\)]+)", body, re.IGNORECASE | re.DOTALL)
                             if confirm_match:
                                 confirm_url = confirm_match.group(1)
                                 # Clean URL if it has trailing characters
                                 confirm_url = confirm_url.rstrip(').,;') 
                                 
                                 logging.info(f"Found GetYourGuide 'Confirm receipt' link: {confirm_url}")
                                 requests.get(confirm_url, timeout=10)
                                 logging.info("Successfully clicked 'Confirm receipt'.")
                         except Exception as e:
                             logging.warning(f"Failed to process GetYourGuide confirm receipt: {e}")
                    # ---------------------------------------------

                    # NEW LOGIC: Use AI to classify the email type completely
                    # Types: 'BOOKING_CONFIRMATION', 'CANCELLATION', 'CUSTOMER_INQUIRY', 'ADDITIONAL_INFO', 'OTHER'
                    
                    classification = self.classify_supplier_email_type(body, subject)
                    logging.info(f"Supplier Email Classified as: {classification}")

                    if classification in ['BOOKING_CONFIRMATION', 'CANCELLATION']:
                        logging.info(f"Skipping Supplier Booking Notification from {supplier_agency} (handled by legacy system).")
                        # --- MARK AS PROCESSED TO AVOID LOOP ---
                        # Remove both search labels to be safe
                        remove_labels_list = []
                        if search_label_id: remove_labels_list.append(search_label_id)
                        if sharm_label_id: remove_labels_list.append(sharm_label_id)
                        
                        self.gmail_service.modify_thread_labels(thread_id, add_labels=[processed_label_id] if processed_label_id else [], remove_labels=remove_labels_list)
                        continue
                    elif classification in ['CUSTOMER_INQUIRY', 'ADDITIONAL_INFO']:
                        logging.info(f"Supplier email from {supplier_agency} contains {classification}. Processing as User Message.")
                        # Treat as normal user message, proceed.
                    else:
                        # Fallback for 'OTHER' - Skip to be safe, or process if you want AI to handle edge cases
                        logging.info(f"Skipping Supplier Email (Type: {classification}) from {supplier_agency}.")
                        # --- MARK AS PROCESSED TO AVOID LOOP ---
                        # Remove both search labels to be safe
                        remove_labels_list = []
                        if search_label_id: remove_labels_list.append(search_label_id)
                        if sharm_label_id: remove_labels_list.append(sharm_label_id)
                        
                        self.gmail_service.modify_thread_labels(thread_id, add_labels=[processed_label_id] if processed_label_id else [], remove_labels=remove_labels_list)
                        continue
                # ----------------------------------------
                
                # Format History String
                history_text = "Conversation History:\n"
                for msg in history:
                    history_text += f"[{msg['date']}] {msg['sender']}: {msg['body']}\n---\n"

                # Call Unified Processor
                result = self.process_unified_message(
                    sender_identifier=sender,
                    message_body=body,
                    history_text=history_text,
                    source="Email",
                    subject=subject,
                    thread_id=thread_id,
                    history_list=history
                )
                
                if not result:
                    # --- MARK AS PROCESSED TO AVOID LOOP ---
                    if processed_label_id:
                        self.gmail_service.modify_thread_labels(thread_id, add_labels=[processed_label_id], remove_labels=[search_label_id])
                    continue
                    
                # Extract results
                response_text = result['response_text']
                booking_record = result['booking_record']
                final_attachments = result['attachments']
                customer_name = result['customer_name']
                customer_email = result['customer_email']
                was_escalated = result['was_escalated']
                escalation_dept = result['escalation_dept']
                inquiry_intent = result['inquiry_intent']
                
                # Check Processing Limit
                processed_count = locals().get('processed_count', 0) + 1
                locals()['processed_count'] = processed_count
                
                max_emails = email_config.get('settings', {}).get('max_emails_per_run', 1)
                
                # --- MAKE WEBHOOK NOTIFICATION (For Driver Delay / Waiting Issues) ---
                # Logic: If user says "ready", "waiting", "where is driver" AND pickup time is passed/now
                # We send a webhook to Make.com to trigger manual intervention/alert
                
                if booking_record:
                    try:
                        # Check keywords
                        msg_lower = body.lower()
                        is_waiting_issue = "ready" in msg_lower or "waiting" in msg_lower or "where" in msg_lower or "late" in msg_lower or "arrive" in msg_lower
                        
                        if is_waiting_issue:
                            # Check Pickup Time
                            pickup_time_str = self.get_field_value(booking_record.get('fields', {}), FieldIds.PICKUP_TIME)
                            if pickup_time_str:
                                # Parse Pickup Time (Assume HH:MM format in Cairo time)
                                # We need to compare with Current Cairo Time
                                now_cairo = datetime.utcnow() + CAIRO_OFFSET
                                current_time_str = now_cairo.strftime("%H:%M")
                                
                                # Simple string comparison for HH:MM usually works if format is same (24h)
                                # Better: Parse objects
                                try:
                                    # Normalize pickup time string (e.g. "03:30" or "3:30 AM")
                                    # This is tricky without a robust parser, but let's try basic split
                                    # If Airtable sends "03:30", it's 24h.
                                    
                                    # Let's just send the webhook if it's "close" to the time (e.g. same day)
                                    # For safety, we just send it if the keywords match. The Webhook scenario in Make.com can filter further if needed.
                                    # But user requested: "If time passed or equal".
                                    
                                    # Assuming pickup_time_str is like "03:30" (24h) OR "04:00 AM" (12h)
                                    pt_obj = None
                                    try:
                                        # Try 24h format first
                                        pt_obj = datetime.strptime(pickup_time_str, "%H:%M").time()
                                    except:
                                        try:
                                            # Try 12h format
                                            pt_obj = datetime.strptime(pickup_time_str, "%I:%M %p").time()
                                        except:
                                            # Try without leading zero 12h
                                            pt_obj = datetime.strptime(pickup_time_str, "%I:%M%p").time()
                                    
                                    if pt_obj:
                                        now_time = now_cairo.time()
                                        
                                        # Handle Midnight Crossover (e.g. Pickup 00:30, Now 23:50 -> False. Pickup 00:30, Now 00:35 -> True)
                                        # But simple time comparison works for same day.
                                        
                                        if now_time >= pt_obj:
                                            # TRIGGER WEBHOOK
                                            webhook_url = "https://hook.us2.make.com/hh1j7h7gbc3g1crf0gf6p9ve5darktqw"
                                            payload = {
                                                "booking_id": booking_record['id'],
                                                "customer_name": customer_name,
                                                "pickup_time": pickup_time_str,
                                                "user_message": body,
                                                "timestamp": now_cairo.strftime("%Y-%m-%d %H:%M:%S"),
                                                "booking_data": booking_record.get('fields', {})
                                            }
                                            # Send async (fire and forget) or sync with short timeout
                                            try:
                                                import requests
                                                requests.post(webhook_url, json=payload, timeout=2)
                                                logging.info(f"Triggered Driver Alert Webhook for {booking_record['id']}")
                                            except Exception as w_err:
                                                logging.warning(f"Failed to trigger webhook: {w_err}")
                                            
                                except Exception as e:
                                    logging.warning(f"Time parsing failed for webhook check: {e}")

                    except Exception as e:
                        logging.error(f"Error in Webhook Logic: {e}")
                # ---------------------------------------------------------------------

                # Send Reply
                reply_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject
                last_msg_id = latest_msg['id']
                
                # --- DRAFT MODE CHECK (EMAIL) ---
                is_draft_mode = self.config.get('email', {}).get('settings', {}).get('draft_mode', False)
                
                if is_draft_mode:
                    logging.info(f"Draft Mode ON: Creating draft for {customer_email} instead of sending.")
                    
                    # Create Draft
                    html_content = email_templates.generate_standard_email_template(
                        content=response_text.replace('\n', '<br>'),
                        title=reply_subject,
                        customer_name=customer_name
                    )
                    
                    draft = self.gmail_service.create_draft(
                        customer_email, 
                        reply_subject, 
                        html_content, 
                        thread_id=thread_id,
                        in_reply_to_message_id=last_msg_id,
                        attachments=final_attachments
                    )
                    
                    if draft:
                        email_sent_success = True # Treat as success for flow continuity
                        
                        # Log as PROPOSED_DRAFT
                        self.log_proposed_reply_for_learning(
                            booking_record['id'] if booking_record else "unknown", 
                            response_text, 
                            table_name=booking_record.get('table_name') if booking_record else None
                        )
                    else:
                        email_sent_success = False
                else:
                    # LIVE MODE - SEND EMAIL
                    html_content = email_templates.generate_standard_email_template(
                        content=response_text.replace('\n', '<br>'),
                        title=reply_subject,
                        customer_name=customer_name
                    )
                    
                    email_sent_success = self.send_email(
                        customer_email, 
                        reply_subject, 
                        html_content, 
                        thread_id=thread_id,
                        in_reply_to_message_id=last_msg_id,
                        attachments=final_attachments
                    )

                # 4. Update Chat Log in Airtable (State Tracking)
                if email_sent_success and booking_record:
                     updates_status = {}
                     if was_escalated:
                         updates_status[FieldIds.AI_CHAT_STATUS] = "ESCALATED"
                         updates_status[FieldIds.ESCALATION_DEPT] = escalation_dept
                     else:
                         current_status = self.get_field_value(booking_record.get('fields', {}), FieldIds.AI_CHAT_STATUS)
                         if current_status == "RESOLVED":
                              updates_status[FieldIds.AI_CHAT_STATUS] = None
                
                if processed_count >= max_emails:
                    logging.info(f"Reached max emails per run limit ({max_emails}). Stopping batch.")
                    return

                # Separate Try/Except Blocks
                try:
                     # 1. Update Inquiry Type
                    try:
                        self.update_booking_record(booking_record['id'], {FieldIds.INQUIRY_TYPE: inquiry_intent}, table_name=booking_record.get('table_name'))
                    except Exception as e:
                        logging.warning(f"Could not update Inquiry Type: {e}")
                        # Fallback: Append to Note if Inquiry Type field is missing
                        try:
                            current_note = self.get_field_value(booking_record.get('fields', {}), FieldIds.NOTE) or ""
                            # Avoid duplicate tagging
                            if f"[Inquiry: {inquiry_intent}]" not in current_note:
                                new_note = f"{current_note}\n[Inquiry: {inquiry_intent}]".strip()
                                self.update_booking_record(booking_record['id'], {FieldIds.NOTE: new_note}, table_name=booking_record.get('table_name'))
                                logging.info(f"Fallback: Updated Note with Inquiry Type: {inquiry_intent}")
                        except Exception as ex:
                            logging.warning(f"Fallback to Note failed: {ex}")

                    # 2. Update Status
                    if updates_status:
                        # Split updates to handle failures individually
                        for field, value in updates_status.items():
                            try:
                                self.update_booking_record(booking_record['id'], {field: value}, table_name=booking_record.get('table_name'))
                            except Exception as e:
                                logging.warning(f"Could not update {field}: {e}")
                                # Fallback for Escalation Dept
                                if field == FieldIds.ESCALATION_DEPT:
                                    try:
                                        current_note = self.get_field_value(booking_record.get('fields', {}), FieldIds.NOTE) or ""
                                        if f"[Dept: {value}]" not in current_note:
                                            new_note = f"{current_note}\n[Dept: {value}]".strip()
                                            self.update_booking_record(booking_record['id'], {FieldIds.NOTE: new_note}, table_name=booking_record.get('table_name'))
                                            logging.info(f"Fallback: Updated Note with Dept: {value}")
                                    except Exception:
                                        pass

                    # 3. Log AI Reply (Using Unified Helper)
                    is_draft_mode = self.config.get('email', {}).get('settings', {}).get('draft_mode', False)
                    
                    if not is_draft_mode:
                        try:
                            self.append_to_chat_log(
                                booking_record['id'], 
                                response_text, 
                                sender="AI", 
                                source="System", 
                                table_name=booking_record.get('table_name')
                            )
                        except Exception as e:
                             logging.warning(f"Could not log AI reply to Chat Log: {e}")
                    else:
                        logging.info("Draft Mode: Skipping duplicate log of AI reply (already logged as PROPOSED_DRAFT).")

                except Exception as e:
                     logging.error(f"Failed to update Airtable after email: {e}")
                
                # 4. Move to Processed & Add Star
                add_labels = []
                if processed_label_id:
                    add_labels.append(processed_label_id)
                
                # Add Star 
                add_labels.append('STARRED')

                # Remove both search labels to be safe
                remove_labels_list = []
                if search_label_id:
                    remove_labels_list.append(search_label_id)
                if sharm_label_id:
                    remove_labels_list.append(sharm_label_id)

                self.gmail_service.modify_thread_labels(
                    thread_id, 
                    add_labels=add_labels, 
                    remove_labels=remove_labels_list
                )
                    
            except Exception as e:
                logging.error(f"Error processing thread {thread['id']}: {e}")

    def run(self):
        logging.info("AI Agent Service Started.")
        print("AI Agent is running... Press Ctrl+C to stop.")
        
        # Start Webhook Server in a separate thread
        try:
            # IMPORTANT: Thread must NOT be daemon to ensure it stays alive and handles requests properly
            # However, for the main loop to work, daemon=True is standard pattern if main thread loops forever.
            # The issue might be that Flask needs to bind to 0.0.0.0 properly for external access
            webhook_thread = threading.Thread(target=self.run_webhook_server, daemon=True)
            webhook_thread.start()
            logging.info("Webhook Server (WhatsApp/Tawk.to) started on port 5001.")
        except Exception as e:
            logging.error(f"Failed to start Webhook Server: {e}")
        
        # Schedule tasks
        schedule.every(2).minutes.do(self.process_new_bookings) 
        schedule.every(2).minutes.do(self.process_incoming_emails)
        schedule.every(10).minutes.do(self.learn_from_human_edits)
        
        # Run immediately on startup
        print("Running initial check...")
        # self.process_incoming_emails() # Commented out to focus on Webhook debug first
        
        while True:
            next_run = schedule.next_run()
            if next_run:
                now = datetime.now()
                delta = next_run - now
                seconds_left = max(0, int(delta.total_seconds()))
                print(f"\r⏳ Next check in: {seconds_left} seconds...   ", end="", flush=True)
            
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    agent = AIAgent()
    agent.run()
        
