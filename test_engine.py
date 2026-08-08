import json
import os
import sys

sys.path.append(os.getcwd())
from runtime.pi_brain.background_task_engine import BackgroundTaskEngine

outbox_dir = os.path.join('runtime', 'pi_brain', 'users', 'u_ahmady', 'bridge', 'outbox')
os.makedirs(outbox_dir, exist_ok=True)
manifest_path = os.path.join(outbox_dir, 'man_test_cap_01.json')
manifest_data = {
  'manifest_id': 'man_test_cap_01',
  'timestamp': '2026-07-12T10:00:00Z',
  'user_id': 'u_ahmady',
  'actions': [
    {
      'action_type': 'develop_new_capability',
      'payload': {
        'tool_name': 'get_server_time',
        'tool_description': 'Returns the current server date and time.',
        'parameters_schema': {},
        'python_code': 'import datetime\n\ndef handle_get_server_time(payload, user_id):\n    now = datetime.datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")\n    return {\n        \"status\": \"executed\",\n        \"message\": f\"The current server time is {now}\"\n    }\n'
      }
    }
  ]
}
with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(manifest_data, f)

engine = BackgroundTaskEngine()
# Process the user directory directly since process_outbox expects user_dir
engine.process_outbox(os.path.join('runtime', 'pi_brain', 'users', 'u_ahmady'))

inbox_dir = os.path.join('runtime', 'pi_brain', 'users', 'u_ahmady', 'bridge', 'inbox')
result_path = os.path.join(inbox_dir, 'result_man_test_cap_01.json')
if os.path.exists(result_path):
    with open(result_path, 'r', encoding='utf-8') as f:
        print('--- RESULT FROM INBOX ---')
        print(f.read())
else:
    print('Result not found!')

print('--- CREATED FILES ---')
print('Schema exists:', os.path.exists(os.path.join('runtime', 'pi_brain', 'schemas', 'get_server_time_schema.json')))
print('Handler exists:', os.path.exists(os.path.join('runtime', 'pi_brain', 'dynamic_handlers', 'get_server_time.py')))
