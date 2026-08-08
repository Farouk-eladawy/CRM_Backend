import chat_db
import json

res = chat_db.get_conversations_page(
    limit=200, 
    offset=0, 
    location='Hurghada/Cairo', 
    include_unknown=1,
    exclude_source='Facebook'
)
print("Total returned:", len(res['items']))
found = [c for c in res['items'] if 'GYGWZAR7W72F' in str(c.values())]
print("Found GYGWZAR7W72F:", len(found))
if found:
    print(found[0]['chat_id'], found[0]['booking_number'], found[0]['location'])
