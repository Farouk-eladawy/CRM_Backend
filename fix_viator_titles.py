import json
import re

FILE_PATH = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Viator_data.json"

def fix_titles():
    try:
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        fixed_count = 0
        for trip in data:
            current_title = trip['tour_info']['title']
            url = trip['tour_info']['url']
            
            if current_title == "Unknown Title" or not current_title:
                # Extract from URL
                # url structure: .../tours/Location/TITLE-SLUG/d...
                try:
                    # Find part between location and product code ID
                    # e.g. /tours/Luxor/Private-Full-Day-Luxor-Tour.../d826...
                    parts = url.split('/')
                    # Usually the slug is at index 5 (0:https, 1:"", 2:www.viator.com, 3:tours, 4:Location, 5:Slug)
                    if len(parts) > 5:
                        slug = parts[5]
                        # Replace hyphens with spaces and Title Case
                        new_title = slug.replace('-', ' ').title()
                        trip['tour_info']['title'] = new_title
                        trip['overview']['description'] = f"Experience the {new_title}. Provided by FTS Travels."
                        fixed_count += 1
                except:
                    pass
                    
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Fixed {fixed_count} titles from URLs.")
        
    except Exception as e:
        print(f"Error fixing titles: {e}")

if __name__ == "__main__":
    fix_titles()
