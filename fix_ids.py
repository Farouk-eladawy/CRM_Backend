import re

with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace occurrences where phone_number_ids is initialized from waba_ids
# But ONLY when it's literally assigning to phone_number_ids
# We will do this via regex

new_content = re.sub(
    r'(phone_number_ids\s*=\s*(?:.*?)get\([\'"])(waba_ids)([\'"](?:.*?)\))',
    r'\g<1>phone_number_ids\g<3>',
    content
)

# Also check for .get('phone_number_ids', {}) or .get('waba_ids', {})
new_content = re.sub(
    r'\.get\([\'"]phone_number_ids[\'"],\s*\{\}\)\s*or\s*(?:.*?)\.get\([\'"]waba_ids[\'"],\s*\{\}\)',
    r'.get(\'phone_number_ids\', {})',
    new_content
)

with open('ai_agent.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Replacement complete.")
