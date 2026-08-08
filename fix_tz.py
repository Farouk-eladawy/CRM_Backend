import re

with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix timezone.utc where it should be datetime.timezone.utc
content = content.replace('datetime.datetime.now(timezone.utc)', 'datetime.datetime.now(datetime.timezone.utc)')
content = content.replace('_dt.datetime.now(timezone.utc)', '_dt.datetime.now(_dt.timezone.utc)')

with open('ai_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed timezone references")
