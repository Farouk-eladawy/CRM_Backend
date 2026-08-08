import sys
import os
import sqlite3
from ai_agent import AIAgent

agent = AIAgent()

lead_record_id = 'rec24GsBsxGZFQU4l'
target_booking_id = 'reclOt3GzIxr1zd8X'
personal_email = 'celinebrissonnet@orange.fr'
chat_id = 'a0644a9a-75f1-44f8-ba5a-64ce86ea44e6'

print("1. Updating Airtable Booking Record with Personal Email...")
try:
    agent.update_booking_record(target_booking_id, {'Customer personal email': personal_email})
    print("Success.")
except Exception as e:
    print("Failed to update Airtable:", e)

print("2. Updating Local Chat DB to link conversation to the real booking...")
try:
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("UPDATE conversations SET airtable_record_id = ? WHERE chat_id = ?", (target_booking_id, chat_id))
    conn.commit()
    conn.close()
    print("Success.")
except Exception as e:
    print("Failed to update DB:", e)

print("3. Deleting the duplicate Lead Record from Airtable...")
try:
    agent.leads_table.delete(lead_record_id)
    print("Success.")
except Exception as e:
    print("Failed to delete lead:", e)

print("Done.")
