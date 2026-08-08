import json

schema = {
  "type": "query_records",
  "description": "استعلام وجلب بيانات من جداول Airtable المختلفة (Bookings List, Catalog MPC, Website Trips). يجب التأكد من المستخدم عن نوع الجدول ونوع التاريخ قبل الاستخدام.",
  "target_record": "all",
  "requires_approval": False,
  "payload": {
    "target_table": "string (MUST be one of: 'Bookings_List', 'Catalog_MPC', 'Website_Trips')",
    "date_type": "string (If applicable. e.g., 'Created Date', 'Date Trip')",
    "date_value": "string (e.g., 'today', 'tomorrow', '2026-07-12')",
    "agency_filter": "string (e.g., 'GYG', 'Tiqets')",
    "status_filter": "string (e.g., 'Active', 'Confirmed', 'Canceled')"
  }
}

with open('runtime/pi_brain/schemas/query_records_schema.json', 'w', encoding='utf-8') as f:
    json.dump(schema, f, ensure_ascii=False, indent=2)
print("SUCCESS updated schema")
