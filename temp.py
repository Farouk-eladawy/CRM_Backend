import sys
path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\frontend_dashboard\new_frontend_dashboard\src\App.tsx"
with open(path, encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'setChats' in l:
        print(f"{i}: {l.strip()}")
