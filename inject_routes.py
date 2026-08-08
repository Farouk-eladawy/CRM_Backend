import os
import sys

def inject_sales_performance_routes():
    file_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\ai_agent.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    marker = "        # ==========================================\n        # TIQETS API REVERSE PROXY ROUTES"
    if marker not in content:
        print("Marker not found.")
        return

    routes_code = """
        # ==========================================
        # SALES PERFORMANCE & INTELLIGENCE CENTER
        # ==========================================
        @app.route('/api/sales_performance/kpis', methods=['POST', 'OPTIONS'])
        def api_sales_performance_kpis():
            if request.method == 'OPTIONS':
                return jsonify({}), 200
            try:
                data = request.json or {}
                from sales_performance_service import SalesPerformanceService
                service = SalesPerformanceService(self.airtable_api, self.base_id, self.config['airtable']['tables']['main_list'], self.config)
                result = service.get_kpis(data)
                return jsonify({"status": "success", "data": result}), 200
            except Exception as e:
                logging.error(f"Error in api_sales_performance_kpis: {e}", exc_info=True)
                return jsonify({"status": "error", "message": str(e)}), 500

        @app.route('/api/sales_performance/reviews', methods=['GET', 'POST', 'OPTIONS'])
        def api_sales_performance_reviews():
            if request.method == 'OPTIONS':
                return jsonify({}), 200
                
            try:
                from airtable_fields import FieldIds
                # Assuming table Sales_Performance_Reviews exists in the same base
                reviews_table_name = "Sales_Performance_Reviews"
                reviews_table = self.airtable_api.table(self.base_id, reviews_table_name)
                
                if request.method == 'GET':
                    month = request.args.get('month')
                    employee_email = request.args.get('employee_email')
                    
                    if not month or not employee_email:
                        return jsonify({"status": "error", "message": "month and employee_email required"}), 400
                        
                    report_id = f"{employee_email}_{month}"
                    formula = f"{{Report_ID}} = '{report_id}'"
                    
                    records = reviews_table.all(formula=formula)
                    if records:
                        return jsonify({"status": "success", "data": records[0]}), 200
                    else:
                        return jsonify({"status": "success", "data": None}), 200
                        
                elif request.method == 'POST':
                    data = request.json or {}
                    month = data.get('month')
                    employee_email = data.get('employee_email')
                    
                    if not month or not employee_email:
                        return jsonify({"status": "error", "message": "month and employee_email required"}), 400
                        
                    report_id = f"{employee_email}_{month}"
                    formula = f"{{Report_ID}} = '{report_id}'"
                    
                    records = reviews_table.all(formula=formula)
                    
                    fields_to_update = {
                        "Report_ID": report_id,
                        "Employee Email": employee_email,
                        "Month": month,
                        "Success Factors": data.get("success_factors", []),
                        "Sales Challenges": data.get("sales_challenges", []),
                        "Lost Reasons": data.get("lost_reasons", []),
                        "Objections": data.get("objections", []),
                        "Payment Issues": data.get("payment_issues", []),
                        "Support Needed": data.get("support_needed", ""),
                        "Next Month Plan": data.get("next_month_plan", ""),
                        "Report Status": data.get("report_status", "Draft")
                    }
                    
                    # Add manager fields if provided
                    if "manager_score" in data:
                        fields_to_update["Manager Score"] = data["manager_score"]
                    if "strengths" in data:
                        fields_to_update["Strengths"] = data["strengths"]
                    if "weaknesses" in data:
                        fields_to_update["Weaknesses"] = data["weaknesses"]
                    if "training_required" in data:
                        fields_to_update["Training Required"] = data["training_required"]
                    if "bonus_recommendation" in data:
                        fields_to_update["Bonus Recommendation"] = data["bonus_recommendation"]
                    if "manager_notes" in data:
                        fields_to_update["Manager Notes"] = data["manager_notes"]
                    if "promotion_potential" in data:
                        fields_to_update["Promotion Potential"] = data["promotion_potential"]
                        
                    if records:
                        updated = reviews_table.update(records[0]['id'], fields_to_update)
                        return jsonify({"status": "success", "data": updated}), 200
                    else:
                        created = reviews_table.create(fields_to_update)
                        return jsonify({"status": "success", "data": created}), 200
                        
            except Exception as e:
                logging.error(f"Error in api_sales_performance_reviews: {e}", exc_info=True)
                return jsonify({"status": "error", "message": str(e)}), 500
"""

    new_content = content.replace(marker, routes_code + "\n" + marker)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Routes injected successfully.")

if __name__ == "__main__":
    inject_sales_performance_routes()
