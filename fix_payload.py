with open('runtime/pi_brain/background_task_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'elif action_type == "develop_new_capability":\n            try:\n                tool_name = payload.get("tool_name", "unknown_tool")',
    'elif action_type == "develop_new_capability":\n            try:\n                payload = action.get("payload", {})\n                tool_name = payload.get("tool_name", "unknown_tool")'
)

with open('runtime/pi_brain/background_task_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("SUCCESS fixed payload")
