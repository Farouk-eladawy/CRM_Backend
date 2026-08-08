import os
import json
import uuid
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from runtime.pi_brain.background_task_engine import BackgroundTaskEngine

def test_develop_new_capability():
    print("🚀 Starting test for develop_new_capability...")
    
    # 1. Setup user directory
    user_key = "test_user"
    user_dir = os.path.join("runtime", "pi_brain", "users", user_key)
    outbox_dir = os.path.join(user_dir, "bridge", "outbox")
    inbox_dir = os.path.join(user_dir, "bridge", "inbox")
    
    os.makedirs(outbox_dir, exist_ok=True)
    os.makedirs(inbox_dir, exist_ok=True)
    
    # 2. Create test manifest
    manifest_id = f"man_test_{uuid.uuid4().hex[:8]}"
    manifest_path = os.path.join(outbox_dir, f"{manifest_id}.json")
    
    python_code = """
def handle_get_server_time(payload, actor_name):
    import datetime
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return {
        "status": "success",
        "message": f"Server time is {current_time}"
    }
"""

    manifest_data = {
        "manifest_id": manifest_id,
        "intent": "test_develop_capability",
        "actions": [
            {
                "type": "develop_new_capability",
                "payload": {
                    "tool_name": "get_server_time",
                    "tool_description": "Returns the current server time",
                    "parameters_schema": {
                        "properties": {},
                        "required": []
                    },
                    "python_code": python_code.strip()
                }
            }
        ]
    }
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Created test manifest: {manifest_path}")
    
    # 3. Process outbox
    print("🔄 Processing outbox...")
    engine = BackgroundTaskEngine()
    engine.process_outbox(user_dir)
    
    # 4. Check results
    result_path = os.path.join(inbox_dir, f"result_{manifest_id}.json")
    if os.path.exists(result_path):
        with open(result_path, "r", encoding="utf-8") as f:
            result_data = json.load(f)
        print(f"✅ Found result in inbox: {result_path}")
        print(json.dumps(result_data, indent=2, ensure_ascii=False))
        
        # 5. Check if schema and handler were created
        schema_path = os.path.join("runtime", "pi_brain", "schemas", "get_server_time_schema.json")
        handler_path = os.path.join("runtime", "pi_brain", "dynamic_handlers", "get_server_time.py")
        
        print("\n🔍 Checking generated files:")
        if os.path.exists(schema_path):
            print(f"✅ Schema created: {schema_path}")
        else:
            print(f"❌ Schema missing: {schema_path}")
            
        if os.path.exists(handler_path):
            print(f"✅ Handler created: {handler_path}")
        else:
            print(f"❌ Handler missing: {handler_path}")
    else:
        print(f"❌ Result file not found in inbox: {result_path}")

if __name__ == "__main__":
    test_develop_new_capability()
