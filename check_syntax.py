import os
os.chdir(r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version")
with open('ai_agent.py', 'r', encoding='utf-8') as f:
    source = f.read()
try:
    compile(source, 'ai_agent.py', 'exec')
    print('OK: ai_agent.py syntax is valid')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')
