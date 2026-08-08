import re

with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''                    knowledge_context = (
                        "=== SYSTEM KNOWLEDGE BASE ===\\n"
                        f"{full_context.get('system_rules', '')}\\n\\n"
                        f"{full_context.get('dynamic_knowledge', '')}\\n\\n"
                        "=== OPERATIONAL PATTERNS ===\\n"
                        f"{json.dumps(full_context.get('user_patterns', {}), ensure_ascii=False)}\\n\\n"
                        f"{schemas_str}"
                    )'''

new_block = '''                    knowledge_context = (
                        "=== SYSTEM KNOWLEDGE BASE ===\\n"
                        f"{full_context.get('system_rules', '')}\\n\\n"
                        f"{full_context.get('dynamic_knowledge', '')}\\n\\n"
                        "=== DATABASE SCHEMA (AIRTABLE) ===\\n"
                        "- Bookings: Base 'main', Table 'List' (Fields: 'trip name', 'Real Product Name', 'Booking Nr.', etc.)\\n"
                        "- Catalog (MPC): Base 'main', Table 'MPC' (Contains Trip Names and their 'Product ID')\\n"
                        "- Website Trips: Base 'trips', Table 'Trips' (Contains trips specific to the company's website)\\n"
                        "IMPORTANT: If the user asks to query trips or data and it is AMBIGUOUS which table they mean, use 'internal_reply' to ASK THEM FIRST before executing 'query_records'. For example, if they ask for 'trip list', ask if they mean booked trips (List) or the catalog (MPC) or the site trips.\\n\\n"
                        "=== OPERATIONAL PATTERNS ===\\n"
                        f"{json.dumps(full_context.get('user_patterns', {}), ensure_ascii=False)}\\n\\n"
                        f"{schemas_str}"
                    )'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('ai_agent.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS')
else:
    print('FAILED to find exact block. Let us use regex.')
    # Fallback regex
    regex_pattern = r'knowledge_context\s*=\s*\(\s*"=== SYSTEM KNOWLEDGE BASE ===\\n".*?f"\{schemas_str\}"\s*\)'
    if re.search(regex_pattern, content, re.DOTALL):
        content = re.sub(regex_pattern, new_block, content, flags=re.DOTALL)
        with open('ai_agent.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('SUCCESS via regex')
    else:
        print('FAILED via regex too')
