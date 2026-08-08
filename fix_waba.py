import sys

with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("get('phone_number_ids', {})", "get('waba_ids', {})")
content = content.replace("get(\"phone_number_ids\")", "get(\"waba_ids\")")

with open('ai_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replaced successfully")
