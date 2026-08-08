import logging
from collections import defaultdict
from typing import Dict, Any, List
from datetime import datetime
from airtable_fields import FieldIds, ID_TO_READABLE_NAME

class SalesPerformanceService:
    def __init__(self, airtable_api, base_id, main_table_name, config=None):
        self.api = airtable_api
        self.base_id = base_id
        self.main_table_name = main_table_name
        self.table = self.api.table(self.base_id, self.main_table_name)
        self.config = config or {}

    def get_kpis(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch bookings based on filters and calculate KPIs.
        filters can include:
        - date_type: 'Created Date' or 'Date Trip'
        - month: YYYY-MM
        - employee_email: str
        - currency: str
        - booking_status: str
        - invoice_status: str
        - payment_method: str
        - trip_name: str
        - customer_country: str
        """
        # Build Airtable Formula based on filters
        formulas = []
        
        # Date Filter
        date_type = filters.get('date_type', 'Created Date')
        month = filters.get('month') # Format: YYYY-MM
        
        if month:
            date_field = FieldIds.CREATE_DATE if date_type == 'Created Date' else FieldIds.DATE_TRIP
            # Airtable formula for month matching: DATETIME_FORMAT({Field}, 'YYYY-MM') = '2026-06'
            # Note: Airtable formulas use actual field names, so we need to map FieldId to Name if we use string formula, 
            # but pyairtable might need actual names. Let's use the actual names from ID_TO_READABLE_NAME or just search in python.
            # To be safe and avoid Airtable formula complex syntax errors, we can fetch a broader range or use basic formula.
            # Let's fetch using a formula for the date.
            field_name = ID_TO_READABLE_NAME.get(date_field, "Create Date  " if date_type == 'Created Date' else "Date Trip")
            formulas.append(f"DATETIME_FORMAT({{{field_name}}}, 'YYYY-MM') = '{month}'")

        if filters.get('employee_email'):
            email = filters['employee_email']
            # Use the 'Created By' field which is the actual Airtable user field
            created_by_field = ID_TO_READABLE_NAME.get(FieldIds.CREATED_BY, "Created By")
            # Search by employee name/username in the Created By field
            formulas.append(f"SEARCH('{email}', {{{created_by_field}}})")
        else:
            # If "All Employees" is selected, restrict to ONLY sales users.
            # Sales users usernames: 'bassant', 'nadeen', 'ahmedsaad'
            created_by_field = ID_TO_READABLE_NAME.get(FieldIds.CREATED_BY, "Created By")
            formulas.append(f"OR(SEARCH('bassant', {{{created_by_field}}}), SEARCH('nadeen', {{{created_by_field}}}), SEARCH('ahmedsaad', {{{created_by_field}}}))")

        if filters.get('booking_status'):
            status_name = ID_TO_READABLE_NAME.get(FieldIds.BOOKING_STATUS, "Booking Status")
            formulas.append(f"{{{status_name}}} = '{filters['booking_status']}'")

        if filters.get('invoice_status'):
            inv_status_name = ID_TO_READABLE_NAME.get(FieldIds.INVOICE_STATUS, "Invoice Status")
            formulas.append(f"{{{inv_status_name}}} = '{filters['invoice_status']}'")

        if filters.get('payment_method'):
            pay_method_name = ID_TO_READABLE_NAME.get(FieldIds.PAYMENT_METHOD, "Payment Method")
            formulas.append(f"{{{pay_method_name}}} = '{filters['payment_method']}'")

        if filters.get('currency'):
            currency_name = ID_TO_READABLE_NAME.get(FieldIds.CURRENCY, "Currency")
            formulas.append(f"{{{currency_name}}} = '{filters['currency']}'")

        formula = f"AND({','.join(formulas)})" if len(formulas) > 1 else (formulas[0] if formulas else None)
        
        # Fields to fetch to optimize payload
        fields_to_fetch = [
            FieldIds.CREATE_DATE, FieldIds.DATE_TRIP, FieldIds.BOOKING_STATUS,
            FieldIds.INVOICE_STATUS, FieldIds.CURRENCY, FieldIds.TOTAL_PRICE_EUR,
            FieldIds.TOTAL_PRICE_USD, FieldIds.TOTAL_PRICE_GBP, FieldIds.AMOUNT,
            FieldIds.NET_RATE, FieldIds.PAYMENT_METHOD, FieldIds.COLLECTING_ON_DATE_TRIP,
            FieldIds.TRIP_NAME, FieldIds.CUSTOMER_COUNTRY, FieldIds.CREATED_BY,
            FieldIds.BOOKING_NR
        ]

        # Determine view if required based on user roles or just base filter
        # In FTS system, usually Sales users have specific views or they just filter by Created By.
        # If we need a specific view to ensure we only get valid records, we can pass it here.
        # But for now, we rely on the `formula` to fetch all relevant records efficiently.
        # If `filters.get('view')` is provided, we can use it.
        view = filters.get('view')
        
        try:
            if view:
                records = self.table.all(formula=formula, fields=fields_to_fetch, view=view)
            else:
                records = self.table.all(formula=formula, fields=fields_to_fetch)
        except Exception as e:
            logging.error(f"Error fetching records for Sales Performance: {e}")
            records = []

        return self._calculate_kpis(records)

    def _calculate_kpis(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        def normalize_country_value(value: Any) -> str:
            if isinstance(value, dict):
                value = value.get("value") or value.get("country") or value.get("name") or ""
            elif isinstance(value, str):
                stripped = value.strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    try:
                        import ast
                        parsed_value = ast.literal_eval(stripped)
                        if isinstance(parsed_value, dict):
                            value = parsed_value.get("value") or parsed_value.get("country") or parsed_value.get("name") or ""
                        else:
                            value = stripped
                    except Exception:
                        value = stripped
                else:
                    value = stripped

            country = str(value or "").strip()
            if not country:
                return ""

            invalid_markers = {
                "unknown",
                "country not found",
                "loading",
                "generated",
                "n/a",
                "none",
                "null",
            }
            return "" if country.lower() in invalid_markers else country

        summary = {
            "total_bookings": len(records),
            "confirmed_bookings": 0,
            "canceled_bookings": 0,
            "pending_bookings": 0,
            "cancellation_rate": 0,
            "invoices": {
                "paid_count": 0,
                "pending_count": 0
            },
            "financials": {
                "total_sales_by_currency": defaultdict(float),
                "paid_amount_by_currency": defaultdict(float),
                "pending_amount_by_currency": defaultdict(float),
                "outstanding_collection_by_currency": defaultdict(float),
                "total_net_rate_raw_by_currency": defaultdict(float)
            }
        }

        breakdowns = {
            "booking_status_raw": defaultdict(int),
            "invoice_status_breakdown": defaultdict(int),
            "currency_breakdown": defaultdict(int),
            "payment_method_amounts": defaultdict(lambda: defaultdict(float)),
            "top_trips": defaultdict(int),
            "top_countries": defaultdict(int)
        }

        # Status Mappings
        CONFIRMED_STATUSES = {"Confirmed", "Paid", "Done", "Completed", "Active", "Unknown", ""}
        CANCELED_STATUSES = {"Canceled", "Cancelled", "Refunded", "No Show"}
        PENDING_STATUSES = {"Pending", "On Request", "Waiting", "Hold"}
        
        INVOICE_PAID_STATUSES = {"succeeded", "paid", "invoice_success"}
        INVOICE_PENDING_STATUSES = {"Pending", "unpaid"}

        for record in records:
            fields = record.get('fields', {})
            
            # Helper to get field value safely (defined per record to use closure on fields)
            def get_field_val(field_id, default="Unknown"):
                name = ID_TO_READABLE_NAME.get(field_id, field_id)
                val = fields.get(name, default)
                if isinstance(val, list) and len(val) > 0:
                    return val[0]
                return val

            # 1. Booking Status Mapping
            raw_status = get_field_val(FieldIds.BOOKING_STATUS, "Unknown")
            # Treat empty/unknown status as Confirmed
            if not raw_status or raw_status == "Unknown":
                raw_status = "Confirmed"
                
            breakdowns["booking_status_raw"][raw_status] += 1
            
            if raw_status in CONFIRMED_STATUSES:
                summary["confirmed_bookings"] += 1
            elif raw_status in CANCELED_STATUSES:
                summary["canceled_bookings"] += 1
            elif raw_status in PENDING_STATUSES:
                summary["pending_bookings"] += 1

            # 2. Currency
            currency = get_field_val(FieldIds.CURRENCY, "UNKNOWN")
            breakdowns["currency_breakdown"][currency] += 1

            # 3. Invoice Status Mapping
            raw_invoice_status = get_field_val(FieldIds.INVOICE_STATUS, "Unknown")
            breakdowns["invoice_status_breakdown"][raw_invoice_status] += 1
            
            is_invoice_paid = raw_invoice_status in INVOICE_PAID_STATUSES
            is_invoice_pending = raw_invoice_status in INVOICE_PENDING_STATUSES
            
            if is_invoice_paid:
                summary["invoices"]["paid_count"] += 1
            elif is_invoice_pending:
                summary["invoices"]["pending_count"] += 1

            # 4. Financials
            sales_value = 0.0
            if currency == "EUR":
                sales_value = float(get_field_val(FieldIds.TOTAL_PRICE_EUR, 0))
            elif currency == "USD":
                sales_value = float(get_field_val(FieldIds.TOTAL_PRICE_USD, 0))
            elif currency == "GBP":
                sales_value = float(get_field_val(FieldIds.TOTAL_PRICE_GBP, 0))
            
            amount_field = float(get_field_val(FieldIds.AMOUNT, 0))
            
            if sales_value == 0 and amount_field > 0:
                sales_value = amount_field
                
            summary["financials"]["total_sales_by_currency"][currency] += sales_value

            if is_invoice_paid:
                summary["financials"]["paid_amount_by_currency"][currency] += amount_field
            elif is_invoice_pending:
                summary["financials"]["pending_amount_by_currency"][currency] += amount_field if amount_field > 0 else sales_value

            outstanding = float(get_field_val(FieldIds.COLLECTING_ON_DATE_TRIP, 0))
            if outstanding > 0:
                summary["financials"]["outstanding_collection_by_currency"][currency] += outstanding

            net_rate_raw = str(get_field_val(FieldIds.NET_RATE, "0"))
            try:
                import re
                clean_net = re.sub(r'[^\d.]', '', net_rate_raw)
                net_rate = float(clean_net) if clean_net else 0.0
            except:
                net_rate = 0.0

            if net_rate > 0:
                summary["financials"]["total_net_rate_raw_by_currency"][currency] += net_rate

            # 5. Breakdowns
            payment_method = get_field_val(FieldIds.PAYMENT_METHOD, "Unknown")
            breakdowns["payment_method_amounts"][payment_method][currency] += amount_field if amount_field > 0 else sales_value

            trip_name = get_field_val(FieldIds.TRIP_NAME, "Unknown")
            if trip_name:
                breakdowns["top_trips"][trip_name] += 1

            customer_country = normalize_country_value(get_field_val(FieldIds.CUSTOMER_COUNTRY, ""))
            if customer_country:
                breakdowns["top_countries"][customer_country] += 1

        # Final Calculations
        if summary["total_bookings"] > 0:
            summary["cancellation_rate"] = round((summary["canceled_bookings"] / summary["total_bookings"]) * 100, 2)

        # Convert defaultdicts to regular dicts for JSON serialization
        summary["financials"] = {k: dict(v) for k, v in summary["financials"].items()}
        breakdowns["booking_status_raw"] = dict(breakdowns["booking_status_raw"])
        breakdowns["invoice_status_breakdown"] = dict(breakdowns["invoice_status_breakdown"])
        breakdowns["currency_breakdown"] = dict(breakdowns["currency_breakdown"])
        breakdowns["payment_method_amounts"] = {k: dict(v) for k, v in breakdowns["payment_method_amounts"].items()}
        breakdowns["top_trips"] = dict(sorted(breakdowns["top_trips"].items(), key=lambda item: item[1], reverse=True)[:10])
        breakdowns["top_countries"] = dict(sorted(breakdowns["top_countries"].items(), key=lambda item: item[1], reverse=True)[:10])

        return {
            "summary": summary,
            "breakdowns": breakdowns
        }
