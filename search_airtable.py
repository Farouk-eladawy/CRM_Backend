import sys
import os
from ai_agent import AIAgent

try:
    agent = AIAgent()
    print("\n--- Searching Main Table for Celine ---")
    records = agent.table.all()
    for r in records:
        fields = r.get('fields', {})
        name = str(fields.get('Customer Name', '')).lower()
        if 'brissonnet' in name:
            print(f"Record ID: {r.get('id')} | Fields: {fields}")
except Exception as e:
    print("Error:", e)
