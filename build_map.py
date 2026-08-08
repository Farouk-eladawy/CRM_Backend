import json
import csv
import os

# Field Rules
RULES = {
    "Financial": ["price", "amount", "cost", "net rate", "refund"],
    "Contact": ["phone", "email", "name", "customer"],
    "Status": ["status", "confirmed", "cancel", "check"],
    "System": ["id", "created", "modified", "formula", "rollup", "lookup", "button"],
    "Logistics": ["pickup", "driver", "guide", "hotel", "room", "location", "map"],
    "Trip": ["trip", "date", "pax", "adult", "child", "infant"]
}

def classify_field(name, type_):
    name_lower = name.lower()
    type_lower = type_.lower()
    
    # Default
    category = "General"
    owner = "Human/System"
    criticality = "Low"
    
    # 1. Determine Category
    for cat, keywords in RULES.items():
        if any(k in name_lower for k in keywords):
            category = cat
            break
            
    # 2. Determine Owner & Criticality
    if category == "Financial":
        owner = "Finance Team"
        criticality = "High"
    elif category == "System" or type_lower in ['formula', 'rollup', 'createdby', 'lastmodifiedby', 'button']:
        owner = "System Automation"
        criticality = "Medium" # Changes here are usually syncs
    elif category == "Status":
        owner = "Operations"
        criticality = "High" # Workflow triggers
    elif category == "Contact":
        owner = "Sales/Customer"
        criticality = "Medium"
        
    return {
        "id": "", # Will be filled from CSV
        "name": name,
        "type": type_,
        "category": category,
        "owner": owner,
        "criticality": criticality,
        "description": f"{category} field likely managed by {owner}."
    }

def main():
    csv_path = "Airtable Fields.csv"
    json_path = "ecosystem_map.json"
    
    ecosystem = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            field_name = row['name']
            field_type = row['type']
            field_id = row['id']
            
            info = classify_field(field_name, field_type)
            info['id'] = field_id
            
            # Map by Field Name (easier for AI to read)
            ecosystem[field_name] = info
            
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(ecosystem, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Generated ecosystem_map.json with {len(ecosystem)} fields.")

if __name__ == "__main__":
    main()
