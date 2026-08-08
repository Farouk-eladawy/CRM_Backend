import json
import logging
from airtable_fields import FieldIds, ID_TO_READABLE_NAME
from pyairtable import Api
from sales_performance_service import SalesPerformanceService
import os

logging.basicConfig(level=logging.INFO)

def load_config_manual():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

config = load_config_manual()
api_key = config['airtable']['api_key']
base_id = config['airtable']['base_id']
main_table = config['airtable']['tables']['main_list']

api = Api(api_key)

# 2. Initialize Service
service = SalesPerformanceService(api, base_id, main_table, config)

# 3. We'll test getting KPIs for the current month or recent data without strict filters first to see actual data
filters = {
    # 'month': '2026-06' # Let's fetch some recent data without filtering by month to ensure we get something
}

# Modifying the service slightly for this test script to expose raw rows
# We will do a direct call to simulate the service fetching but keep the raw data

fields_to_fetch = [
    FieldIds.CREATE_DATE, FieldIds.DATE_TRIP, FieldIds.BOOKING_STATUS,
    FieldIds.INVOICE_STATUS, FieldIds.CURRENCY, FieldIds.TOTAL_PRICE_EUR,
    FieldIds.TOTAL_PRICE_USD, FieldIds.TOTAL_PRICE_GBP, FieldIds.AMOUNT,
    FieldIds.NET_RATE, FieldIds.PAYMENT_METHOD, FieldIds.COLLECTING_ON_DATE_TRIP,
    FieldIds.TRIP_NAME, FieldIds.CUSTOMER_COUNTRY, FieldIds.CREATED_BY,
    FieldIds.BOOKING_NR
]

print("Fetching records from Airtable (Max 100 for testing)...")
table = api.table(base_id, main_table)
raw_records = table.all(fields=fields_to_fetch, max_records=100)

print(f"Fetched {len(raw_records)} records.")

kpi_result = service._calculate_kpis(raw_records)

# Hide sensitive data from raw records for display
safe_records = []
for r in raw_records[:5]:
    safe_r = {"id": r["id"], "fields": {}}
    for k, v in r["fields"].items():
        if k in [FieldIds.BOOKING_NR]:
            safe_r["fields"][ID_TO_READABLE_NAME.get(k, k)] = f"***{str(v)[-3:]}" if v else None
        elif k == FieldIds.CREATED_BY:
            safe_r["fields"]["Created By"] = {"email": "***@fts.com", "name": v.get("name", "Unknown")} if isinstance(v, dict) else v
        else:
            safe_r["fields"][ID_TO_READABLE_NAME.get(k, k)] = v
    safe_records.append(safe_r)

output = {
    "source_records_count": len(raw_records),
    "sample_raw_records": safe_records,
    "kpi_result": kpi_result
}

with open('test_kpi_output.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("Test complete. Results saved to test_kpi_output.json")
