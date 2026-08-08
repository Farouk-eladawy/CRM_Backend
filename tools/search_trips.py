import sys
import json
import os
from pyairtable import Api

# --- Configuration: File Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = {
    "headout": os.path.join(BASE_DIR, 'Headout_data.json'),
    "gyg": os.path.join(BASE_DIR, 'Get_Your_Guide_data.json'),
    "viator": os.path.join(BASE_DIR, 'Viator_data.json')
}

# --- Configuration: Airtable (FTS Internal) ---
AIRTABLE_API_KEY = "patCrmPawToySTEuL.74d62c60d604c76e0c5ba3ca9975895fb07314c917fc458a37b81a4642ffcae3"
AIRTABLE_TRIPS_BASE_ID = "apphGHAvy5IhAWVw9"
AIRTABLE_TRIPS_TABLE = "Trips"

def load_json_file(filepath):
    """Safely load a JSON file."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and 'tours' in data:
                return data['tours']
            elif isinstance(data, list):
                return data
            return []
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return []

def search_airtable(query):
    """Search FTS Internal Trips in Airtable."""
    try:
        api = Api(AIRTABLE_API_KEY)
        table = api.table(AIRTABLE_TRIPS_BASE_ID, AIRTABLE_TRIPS_TABLE)
        
        # Using a simple formula to search in 'Name' field (adjust field name if needed)
        # Note: This assumes the primary field is 'Name' or 'Trip Name'
        # We fetch all for simplicity in this script, but in prod use formula="{Name}='...'"
        records = table.all() 
        
        results = []
        query_lower = query.lower()
        
        for record in records:
            fields = record.get('fields', {})
            # Adjust these keys based on your actual Airtable columns
            name = fields.get('Name') or fields.get('Trip Name') or "Unknown Trip"
            price = fields.get('Price') or fields.get('Adult Price') or "N/A"
            description = fields.get('Description') or fields.get('Notes') or ""
            
            if query_lower in str(name).lower() or query_lower in str(description).lower():
                results.append(f"📍 [FTS INTERNAL] {name}\n   💰 Price: {price}\n   📝 Notes: {description}\n")
                
        return results
    except Exception as e:
        print(f"Error searching Airtable: {e}")
        return []

def format_trip(trip, source):
    """Format trip details into a readable string."""
    title = trip.get('title') or trip.get('name') or "Unknown Title"
    url = trip.get('url') or trip.get('productUrl') or "N/A"
    price = trip.get('price_from') or trip.get('price') or trip.get('fromPrice') or "N/A"
    
    duration = trip.get('duration')
    if isinstance(duration, dict):
        duration = duration.get('standard') or str(duration)
    if not duration:
        duration = "N/A"

    return f"📍 [{source.upper()}] {title}\n   💰 Price: {price} | ⏳ Duration: {duration}\n   🔗 Link: {url}\n"

def search_trips(query, provider_filter=None):
    query = query.lower()
    results = []
    
    # Decide which providers to search
    providers_to_search = list(FILES.keys()) # Copy keys
    search_internal = True
    
    if provider_filter:
        provider_filter = provider_filter.lower()
        if "viator" in provider_filter:
            providers_to_search = ["viator"]
            search_internal = False
        elif "headout" in provider_filter:
            providers_to_search = ["headout"]
            search_internal = False
        elif "guide" in provider_filter or "gyg" in provider_filter:
            providers_to_search = ["gyg"]
            search_internal = False
        elif "fts" in provider_filter or "internal" in provider_filter:
            providers_to_search = [] # Skip external
            search_internal = True

    print(f"🔎 Searching for '{query}'...")

    # 1. Search External Files
    for source in providers_to_search:
        trips = load_json_file(FILES[source])
        for trip in trips:
            title = str(trip.get('title') or trip.get('name') or "").lower()
            desc = str(trip.get('short_description') or "").lower()
            if query in title or query in desc:
                results.append(format_trip(trip, source))

    # 2. Search Internal Airtable (if applicable)
    if search_internal:
        print("   (Including FTS Internal Database search...)")
        internal_results = search_airtable(query)
        results.extend(internal_results)

    if results:
        print(f"\n✅ Found {len(results)} matches:\n")
        print("\n".join(results[:7]))
    else:
        print(f"\n❌ No trips found for '{query}'.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search_trips.py <query> [provider]")
        sys.exit(1)
        
    query_arg = sys.argv[1]
    provider_arg = sys.argv[2] if len(sys.argv) > 2 else None
    
    search_trips(query_arg, provider_arg)
