import re

with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''                    knowledge_context = (
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

new_block = '''                    knowledge_context = (
                        "=== SYSTEM KNOWLEDGE BASE ===\\n"
                        f"{full_context.get('system_rules', '')}\\n\\n"
                        f"{full_context.get('dynamic_knowledge', '')}\\n\\n"
                        "=== DATABASE SCHEMA (AIRTABLE) ===\\n"
                        "- Bookings: Base 'main', Table 'List' (Contains ACTUAL booked trips).\\n"
                        "  * Fields: 'trip name', 'Real Product Name', 'Booking Nr.', 'Booking Status', 'Date Trip' (Date of execution/travel), 'Created Date' (Date the booking was made).\\n"
                        "- Catalog (MPC): Base 'main', Table 'MPC' (Contains ALL available trips and their 'Product ID').\\n"
                        "- Website Trips: Base 'trips', Table 'Trips' (Contains trips specific to the company's website).\\n\\n"
                        "=== CRITICAL ORCHESTRATION RULES ===\\n"
                        "You are a super-smart orchestrator. You MUST NOT execute blind queries if the request is ambiguous or lacks parameters.\\n"
                        "1. TABLE AMBIGUITY: If the user asks for 'trips', ASK THEM: 'هل تقصد رحلات الحجوزات الفعلية أم الكتالوج (MPC) أم رحلات الموقع؟'\\n"
                        "2. DATE AMBIGUITY: If the user asks for bookings 'today', ASK THEM: 'هل تقصد الحجوزات التي تم إنشاؤها اليوم (Created Date) أم الحجوزات التي سيتم تنفيذها اليوم (Date Trip)؟'\\n"
                        "3. INCOMPLETE INFO: If the user asks a broad question, present them with numbered options (e.g. 1. Show active bookings, 2. Show by agency) using 'internal_reply' BEFORE doing any data fetching.\\n\\n"
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
    print('FAILED to find exact block.')
