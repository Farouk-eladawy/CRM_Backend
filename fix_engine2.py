import re

with open('runtime/pi_brain/background_task_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block_start = 'elif action_type == "query_records":'
old_block_end = 'elif action_type == "update_records":'

idx1 = content.find(old_block_start)
idx2 = content.find(old_block_end, idx1)

if idx2 == -1:
    idx2 = content.find('else:', idx1)

new_block = '''elif action_type == "query_records":
                        payload = action.get("payload", {})
                        target_table = payload.get("target_table", "Bookings_List")
                        date_type = payload.get("date_type", "")
                        date_value = payload.get("date_value", "")
                        agency_filter = payload.get("agency_filter", "")
                        status_filter = payload.get("status_filter", "")

                        api_key = self.airtable_config.get("api_key")
                        base_id = self.airtable_config.get("base_id")
                        
                        if target_table == "Catalog_MPC":
                            table_name = "MPC"
                        elif target_table == "Website_Trips":
                            base_id = self.airtable_config.get("trips_base_id") or base_id
                            table_name = "Trips"
                        else:
                            table_name = self.airtable_config.get("tables", {}).get("main_list", "List")

                        if not api_key or not base_id:
                            result["actions_results"].append({
                                "action_type": action_type,
                                "status": "failed",
                                "message": "Missing Airtable API Key or Base ID."
                            })
                        else:
                            try:
                                url = f"https://api.airtable.com/v0/{base_id}/{quote(table_name)}"
                                headers = {"Authorization": f"Bearer {api_key}"}
                                
                                formulas = []
                                if agency_filter:
                                    formulas.append(f"FIND('{agency_filter}', {{Real Product Name}})")
                                if status_filter:
                                    formulas.append(f"FIND('{status_filter}', {{Booking Status}})")
                                    
                                filter_formula = ""
                                if len(formulas) > 1:
                                    filter_formula = f"AND({','.join(formulas)})"
                                elif len(formulas) == 1:
                                    filter_formula = formulas[0]

                                params = {}
                                if filter_formula:
                                    params["filterByFormula"] = filter_formula

                                response = requests.get(url, headers=headers, params=params)
                                if response.status_code == 200:
                                    records = response.json().get("records", [])
                                    
                                    # Python-side filtering for dates
                                    import datetime
                                    filtered_records = []
                                    for r in records:
                                        fields = r.get("fields", {})
                                        keep = True
                                        
                                        # Simple date filter logic for "today"
                                        if date_value and date_type:
                                            target_date_str = ""
                                            if date_value.lower() == "today":
                                                target_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                                            elif date_value.lower() == "tomorrow":
                                                target_date_str = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                                            else:
                                                target_date_str = date_value # assume YYYY-MM-DD
                                                
                                            record_date = fields.get(date_type, "")
                                            if target_date_str not in str(record_date):
                                                keep = False
                                                
                                        if keep:
                                            filtered_records.append(fields)

                                    # Format message to send back to user
                                    msg_lines = [f"🔔 *نتيجة استعلام PI ({target_table})*:\\n"]
                                    msg_lines.append(f"تم العثور على {len(filtered_records)} نتيجة مطابقة:\\n")
                                    
                                    for idx, fields in enumerate(filtered_records[:30], 1): # limit to 30 to avoid huge msg
                                        t_name = fields.get("trip name") or fields.get("Name") or fields.get("Trip Name") or "Unknown"
                                        p_id = fields.get("Product ID") or fields.get("Real Product Name") or fields.get("Booking Nr.") or "N/A"
                                        status = fields.get("Booking Status") or "N/A"
                                        msg_lines.append(f"{idx}. {t_name}\\n   (Details: {p_id} | Status: {status})")

                                    if len(filtered_records) > 30:
                                        msg_lines.append("\\n... (تم إخفاء باقي النتائج لتجنب الإطالة)")

                                    final_msg = "\\n".join(msg_lines)
                                    admin_phone = "201010323484"
                                    success = self._send_whatsapp_notification(admin_phone, final_msg)
                                    
                                    result["actions_results"].append({
                                        "action_type": action_type,
                                        "status": "executed" if success else "failed",
                                        "message": f"Successfully fetched and sent {len(filtered_records)} records."
                                    })
                                else:
                                    result["actions_results"].append({
                                        "action_type": action_type,
                                        "status": "failed",
                                        "message": f"Airtable API Error: {response.text}"
                                    })
                            except Exception as e:
                                result["actions_results"].append({
                                    "action_type": action_type,
                                    "status": "failed",
                                    "message": str(e)
                                })
'''

if idx1 != -1 and idx2 != -1:
    content = content[:idx1] + new_block + content[idx2:]
    with open('runtime/pi_brain/background_task_engine.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS replaced background engine logic 2")
else:
    print("FAILED to find block")
