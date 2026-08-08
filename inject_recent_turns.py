import re

with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r'"=== CONVERSATION HISTORY \(RECENT TURNS\) ===\\n"\s*f"\{chr\(10\)\.join\(\[f\'\{t\.get\(\\\'role\\\'\, \\\'user\\\'\)\}: \{t\.get\(\\\'text\\\'\, \\\'\\\'\)\}\' for t in case_snapshot\.get\(\\\'recent_turns\\\'\, \[\]\)\]\)\}\\n\\n"'

new_block = '''"=== CONVERSATION HISTORY (RECENT TURNS) ===\\n"
                      f"{chr(10).join(case_snapshot.get('internal_session_lines', []))}\\n\\n"'''

if re.search(pattern, content):
    content = re.sub(pattern, new_block, content)
    with open('ai_agent.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS')
else:
    print('FAILED to find regex pattern.')
