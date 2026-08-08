import json
import os
import shutil

# File paths
MANUAL_FILE = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Viator_data.json"
BOKUN_FILE = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Viator_data_bokun.json"
OUTPUT_FILE = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Viator_data.json" # Overwriting target
BACKUP_FILE = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Viator_data_backup.json"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def merge_datasets():
    print("Loading datasets...")
    manual_data = load_json(MANUAL_FILE)
    bokun_data = load_json(BOKUN_FILE)
    
    print(f"Manual tours: {len(manual_data)}")
    print(f"Bokun tours: {len(bokun_data)}")
    
    # Create a map of manual tours for quick lookup
    # Using product_code as the unique identifier
    manual_map = {}
    for tour in manual_data:
        code = tour.get('tour_info', {}).get('product_code')
        if code:
            manual_map[code] = tour
            
    merged_list = []
    
    # 1. Add all manual tours first (Priority)
    merged_list.extend(manual_data)
    
    # 2. Add Bokun tours ONLY if they don't exist in manual data
    added_count = 0
    for tour in bokun_data:
        code = tour.get('tour_info', {}).get('product_code')
        
        if not code:
            # If no code, we can't reliably dedup, but let's add it if it looks valid
            # Or skip? Safer to skip or log. Bokun data should have codes.
            print(f"Warning: Bokun tour missing product_code: {tour.get('tour_info', {}).get('title')}")
            continue
            
        if code not in manual_map:
            merged_list.append(tour)
            added_count += 1
        else:
            # Debug: print what we are skipping to confirm
            # print(f"Skipping Bokun version of {code} (Manual version exists)")
            pass
            
    print(f"Merged successfully.")
    print(f"Total tours in merged file: {len(merged_list)}")
    print(f"New tours added from Bokun: {added_count}")
    
    # Backup existing file
    if os.path.exists(MANUAL_FILE):
        shutil.copy2(MANUAL_FILE, BACKUP_FILE)
        print(f"Backup created at {BACKUP_FILE}")
        
    # Save merged file
    save_json(merged_list, OUTPUT_FILE)
    print(f"Saved merged data to {OUTPUT_FILE}")

if __name__ == "__main__":
    merge_datasets()
