from ai_agent import AIAgent
from airtable_fields import FieldIds, ID_TO_READABLE_NAME

agent = AIAgent()
booking_field = ID_TO_READABLE_NAME.get(FieldIds.BOOKING_NR, "Booking NR")
formula = f"{{{booking_field}}}='GYGBLHLRZQWL'"
try:
    records = agent.table.all(formula=formula)
    if records:
        fields = records[0]['fields']
        print(f"Booking Status: {fields.get(ID_TO_READABLE_NAME.get(FieldIds.BOOKING_STATUS))}")
        print(f"Phone: {fields.get(ID_TO_READABLE_NAME.get(FieldIds.CUSTOMER_PHONE))}")
        print(f"Whatsapp Pickup Time2: {fields.get('Whatsapp Pickup Time2')}")
        print(f"Email: {fields.get(ID_TO_READABLE_NAME.get(FieldIds.CUSTOMER_PERSONAL_EMAIL))}")
        import pprint
        print("All Fields:")
        pprint.pprint(fields)
    else:
        print("Record not found")
except Exception as e:
    print("Error:", e)
