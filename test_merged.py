import chat_db
import json

msgs = chat_db.get_messages('b253ebb2-d413-405b-b5c4-4b5981a0361c', merge_by_record=True)
print("Merged Messages count:", len(msgs))
for m in msgs:
    print(f"[{m['timestamp']}] {m['sender_type']}: {m['text'][:50]}...")
