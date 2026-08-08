import json
import os

FILE_PATH = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Viator_data.json"

# قائمة أكواد الرحلات المحسنة التي قمنا بإدخالها
OPTIMIZED_CODES = {
    "14976P141",
    "14976P140",
    "14976P139",
    "14976P138",
    "14976P135",
    "14976P3",
    "14976P7",
    "14976P133",
    "14976P131"
}

def filter_tours():
    if not os.path.exists(FILE_PATH):
        print("❌ File not found!")
        return

    try:
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        initial_count = len(data)
        
        # تصفية الرحلات: الاحتفاظ فقط بالرحلات الموجودة في القائمة
        filtered_data = [
            trip for trip in data 
            if trip.get('tour_info', {}).get('product_code') in OPTIMIZED_CODES
        ]
        
        final_count = len(filtered_data)
        removed_count = initial_count - final_count
        
        # حفظ الملف المحدث
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Operation Complete:")
        print(f"   - Initial tours: {initial_count}")
        print(f"   - Removed (Unoptimized): {removed_count}")
        print(f"   - Kept (Optimized): {final_count}")
        print(f"   - Kept Codes: {[t['tour_info']['product_code'] for t in filtered_data]}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    filter_tours()
