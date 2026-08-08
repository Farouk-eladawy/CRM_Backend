from ai_agent import AIAgent
import unified_booking_communications
from airtable_fields import FieldIds, ID_TO_READABLE_NAME

agent = AIAgent()
print("Running unified booking communications for Sharm View...")

booking_field = ID_TO_READABLE_NAME.get(FieldIds.BOOKING_NR, "Booking NR")
formula = f"{{{booking_field}}}='GYGBLHLRZQWL'"

original_all = agent.table.all
def mocked_all(*args, **kwargs):
    if kwargs.get('view') == '30Min Pickup Time Sharm':
        return original_all(formula=formula)
    return []

agent.table.all = mocked_all

res = unified_booking_communications.run(agent)
print("Result:")
import pprint
pprint.pprint(res)
