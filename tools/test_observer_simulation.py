import sys
import os
import json
import logging

# Setup paths
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(TOOLS_DIR)
sys.path.append(BASE_DIR)

# Import Observer Logic
try:
    from OpenClaw_Observer import analyze_change_context
except ImportError:
    print("Error: Could not import OpenClaw_Observer. Run this from the project root.")
    sys.exit(1)

def simulate_change(scenario_name, field, old_val, new_val, purpose, owner, trip_date_offset_hours=24):
    print(f"\n--- Scenario: {scenario_name} ---")
    print(f"🔄 Change: '{field}' changed from '{old_val}' -> '{new_val}'")
    
    # Mock Record Data
    from datetime import datetime, timedelta
    trip_date = (datetime.now() + timedelta(hours=trip_date_offset_hours)).isoformat()
    
    record_data = {
        'Date Trip': trip_date,
        'Booking Nr.': 'TEST-123',
        'Last Modified By': owner
    }
    
    ecosystem_info = {
        'purpose': purpose
    }
    
    print("🧠 Asking AI to analyze...")
    insight = analyze_change_context('TEST-REC-001', field, old_val, new_val, record_data, ecosystem_info)
    print(f"💡 AI Insight: {insight}")

def main():
    print("🚀 Starting Observer Logic Simulation...\n")

    # Scenario 1: Critical Pickup Change (Human Override)
    simulate_change(
        scenario_name="Last Minute Pickup Change",
        field="pickup time",
        old_val="08:00 AM",
        new_val="08:30 AM",
        purpose="Logistics",
        owner="Automation_System", # Usually automated, but changed by human
        trip_date_offset_hours=0.5 # 30 mins before trip!
    )

    # Scenario 2: Finance Update (Routine)
    simulate_change(
        scenario_name="Routine Invoice Generation",
        field="Stripe invoice",
        old_val="",
        new_val="https://stripe.com/invoice/inv_123",
        purpose="Finance",
        owner="Automation_System",
        trip_date_offset_hours=48
    )

    # Scenario 3: Manual Remark (Human)
    simulate_change(
        scenario_name="Agent Adding Note",
        field="Remarks",
        old_val="",
        new_val="Customer requested vegan meal",
        purpose="Communication",
        owner="Human_Agent",
        trip_date_offset_hours=24
    )

if __name__ == "__main__":
    main()
