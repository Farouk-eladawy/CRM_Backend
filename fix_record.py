import sys

with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('self.get_airtable_record_by_id(record_id, department="general")', 'self._get_record_from_any_table(record_id)')
content = content.replace('self.get_airtable_record_by_id(cached_match.get("record_id"), department="general")', 'self._get_record_from_any_table(cached_match.get("record_id"))')

with open('ai_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
