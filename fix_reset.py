with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('session_state["recent_turns"] = []', '# session_state["recent_turns"] = []')

with open('ai_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('SUCCESS disabled clearing of recent_turns')
