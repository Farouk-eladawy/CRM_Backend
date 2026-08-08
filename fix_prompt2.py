with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

rules = '''                          "=== SELF-EXPANDING CAPABILITIES (CRITICAL) ===\\n"
                          "1. If the user asks for a capability or action you do NOT currently have (e.g., you check ALL AVAILABLE ACTION SCHEMAS and none match), YOU MUST auto-generate it.\\n"
                          "2. To auto-generate, use the develop_new_capability schema. Provide the Python code and JSON schema for the new tool.\\n"
                          "3. DO NOT DUPLICATE TOOLS: If a tool already exists that can do the job (even partially), DO NOT create a new one. Use the existing one.\\n"
                          "4. SYSTEM SAFETY: When generating Python code, DO NOT modify core system files, DO NOT drop databases, and DO NOT interfere with the customer-facing frontend or OpenClaw_Core.py.\\n\\n"
'''

old_context = "3. INCOMPLETE INFO: If the user asks a broad question, present them with numbered options (e.g. 1. Show active bookings, 2. Show by agency) using 'internal_reply' BEFORE doing any data fetching.\\n\\n\""

new_context = old_context + "\n" + rules

if old_context in content:
    content = content.replace(old_context, new_context)
    with open('ai_agent.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS updated ai_agent.py rules")
else:
    print("FAILED to find rules block")
