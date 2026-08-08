import re

file_path = "ai_agent.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace specific self.table.get calls with self._get_record_from_any_table
content = re.sub(
    r"self\.table\.get\(conv_dict\['airtable_record_id'\]\)",
    r"self._get_record_from_any_table(conv_dict['airtable_record_id'])",
    content
)

content = re.sub(
    r"self\.table\.get\(conv\['airtable_record_id'\]\)",
    r"self._get_record_from_any_table(conv['airtable_record_id'])",
    content
)

content = re.sub(
    r"self\.table\.get\(existing_airtable_id\)",
    r"self._get_record_from_any_table(existing_airtable_id)",
    content
)

content = re.sub(
    r"self\.table\.get\(record_id_to_save\)",
    r"self._get_record_from_any_table(record_id_to_save)",
    content
)

# Fix find_booking_strictly to use department for religious
# We need to change the call in sync_orphan_chats
# Let's find sync_orphan_chats block

content = re.sub(
    r"booking_record = self\.find_booking_strictly\(\s*history_text,\s*sender_email=customer_email,\s*sender_phone=contact_phone,\s*ai_extracted_data=extracted_data\s*\)",
    r"booking_record = self.find_booking_strictly(\n                    history_text, \n                    sender_email=customer_email, \n                    sender_phone=contact_phone,\n                    ai_extracted_data=extracted_data,\n                    department=conv.get('location')\n                )",
    content
)

# And fix db_location in sync_orphan_chats
old_db_location_code = """                        db_location = self._derive_chat_location_from_fields(
                            booking_record.get('fields', {}),
                            fallback_location="Unknown",
                        )"""

new_db_location_code = """                        db_location = self._derive_chat_location_from_fields(
                            booking_record.get('fields', {}),
                            fallback_location=conv.get('location', "Unknown"),
                            receiving_phone_id=conv.get('receiving_phone_id')
                        )"""

content = content.replace(old_db_location_code, new_db_location_code)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Replaced!")
