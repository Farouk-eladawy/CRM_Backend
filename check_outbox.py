import os
import glob
import json

def check_outbox():
    base_dir = "runtime/pi_brain/users"
    if not os.path.exists(base_dir):
        return
    for user_dir in os.listdir(base_dir):
        outbox_dir = os.path.join(base_dir, user_dir, "bridge", "outbox")
        if os.path.exists(outbox_dir):
            files = glob.glob(os.path.join(outbox_dir, "*.json"))
            for f in files:
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        print(f"User: {user_dir}, Pending file: {f}, Action: {data.get('action_type')}")
                except Exception as e:
                    print(f"Error reading {f}: {e}")

check_outbox()
