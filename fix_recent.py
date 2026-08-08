import re

with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I will find the EXACT string I injected previously and replace it.
target_str = """                      "=== CONVERSATION HISTORY (RECENT TURNS) ===\\n"
                      f"{chr(10).join([f'{t.get(\\'role\\', \\'user\\')}: {t.get(\\'text\\', \\'\\')}' for t in case_snapshot.get(\\'recent_turns\\', [])])}\\n\\n"
                      "=== PRIMARY USER REQUEST (CRITICAL PRIORITY) ===\\n"
                      f"USER SAID: \\"{user_request}\\"\\n\\n"
                      "YOUR SOLE OBJECTIVE IS TO FULFILL THIS SPECIFIC USER REQUEST.\\n"
                      "IMPORTANT: If the USER SAID is a short answer (like \\'Yes\\', \\'The first one\\', \\'Today\\', etc.), YOU MUST use the CONVERSATION HISTORY above to understand what they are replying to.\\n"'''"""

# Actually, let's just use string replace for a simpler substring:
old_substr = "chr(10).join([f'{t.get(\\'role\\', \\'user\\')}: {t.get(\\'text\\', \\'\\')}' for t in case_snapshot.get(\\'recent_turns\\', [])])"
new_substr = "chr(10).join(case_snapshot.get('internal_session_lines', []))"

if old_substr in content:
    content = content.replace(old_substr, new_substr)
    with open('ai_agent.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS replaced recent_turns')
else:
    print('FAILED old_substr not found')
