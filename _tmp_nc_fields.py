import json
p = r"runtime/pi_brain/users/pi_agent/airtable_schema_context.json"
data = json.load(open(p, encoding="utf-8"))

def walk(obj):
    if isinstance(obj, dict):
        if obj.get("table_name") == "Nile_Crystal_Booking":
            names = [f.get("field_name") for f in obj.get("fields") or []]
            keys = ["phone", "email", "chat", "whats", "book", "name", "location", "log"]
            for n in names:
                low = (n or "").lower()
                if any(k in low for k in keys):
                    print(n)
            return True
        for v in obj.values():
            if walk(v):
                return True
    elif isinstance(obj, list):
        for v in obj:
            if walk(v):
                return True
    return False

walk(data)
