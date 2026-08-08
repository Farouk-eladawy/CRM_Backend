import re

with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace datetime.utcnow()
content = re.sub(r'\bdatetime\.utcnow\(\)', 'datetime.now(timezone.utc).replace(tzinfo=None)', content)

# Replace datetime.datetime.utcnow()
content = re.sub(r'\bdatetime\.datetime\.utcnow\(\)', 'datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)', content)

# Replace _dt.datetime.utcnow()
content = re.sub(r'\b_dt\.datetime\.utcnow\(\)', '_dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)', content)

with open('ai_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replaced utcnow in ai_agent.py")
