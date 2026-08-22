"""One-off: run transport sync preview for a date range (no Flask server required)."""
import json
import sys
from datetime import date, timedelta

# Tomorrow relative to run date
tomorrow = (date.today() + timedelta(days=1)).isoformat()

print(f"Preview date_trip = {tomorrow}")

from ai_agent import AIAgent
from transport_sync import TransportAirtableSync

agent = AIAgent()
syncer = TransportAirtableSync(agent)
result = syncer.run(
    dry_run=True,
    max_records=50,
    date_from=tomorrow,
    date_to=tomorrow,
)
print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
