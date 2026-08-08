with open('runtime/pi_brain/background_task_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('elif action_type == "query_records":')
print(content[idx:idx+3000])
