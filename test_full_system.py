import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_agent import AIAgent, CAIRO_OFFSET

class TestSystem(unittest.TestCase):
    def setUp(self):
        # Mock dependencies before initializing AIAgent
        with patch('ai_agent.Api'), \
             patch('ai_agent.GmailService'), \
             patch('ai_agent.KnowledgeBase'):
            self.agent = AIAgent()
            
        # Mock internal components
        self.agent.send_email = MagicMock(return_value=True)
        self.agent.query_ai = MagicMock(return_value="AI Response")
        self.agent.kb = MagicMock()
        self.agent.kb.search.return_value = []
        self.agent.search_trips_db = MagicMock(return_value="")
        
    def test_date_conversion(self):
        """Test Date Conversion Logic (UTC to Cairo)"""
        print("\n--- Testing Date Conversion ---")
        
        # Case 1: ISO Format UTC (Midnight UTC = 3 AM Cairo Next Day if late? No, simple offset)
        # 2026-01-21 22:00:00 UTC -> +3 hours -> 2026-01-22 01:00:00 Cairo
        utc_date = "2026-01-21T22:00:00.000Z"
        date_obj, fmt_date = self.agent.get_corrected_trip_date(utc_date)
        
        print(f"Input: {utc_date}")
        print(f"Output: {fmt_date}")
        
        expected_date = datetime(2026, 1, 22).date()
        self.assertEqual(date_obj, expected_date)
        self.assertIn("22 January 2026", fmt_date)
        
        # Case 2: Simple Date
        simple_date = "2026-01-22"
        date_obj, fmt_date = self.agent.get_corrected_trip_date(simple_date)
        print(f"Input: {simple_date} -> Output: {fmt_date}")
        self.assertEqual(date_obj, datetime(2026, 1, 22).date())

    def test_ticket_request_rule(self):
        """Test Rule: Ticket Request for Ticket-Only Trip"""
        print("\n--- Testing Ticket Request Rule ---")
        
        fields = {
            'trip Name': 'Museum QR Code',
            'Booking Nr.': '123',
            'Customer Name': 'Test User',
            'Customer Email': 'test@example.com',
            'Tickets Files': [{'url': 'http://ticket.link'}],
            'Agency': 'Tiqets'
        }
        
        # Mock email templates
        with patch('ai_agent.email_templates.generate_ticket_email', return_value="<html>Ticket</html>") as mock_tmpl:
            self.agent.handle_customer_inquiry('rec123', fields, "Please send my ticket")
            
            # Should have called generate_ticket_email
            mock_tmpl.assert_called()
            # Should have sent email
            self.agent.send_email.assert_called_with('test@example.com', "Your Tickets: Museum QR Code", "<html>Ticket</html>")
            print("✔ Ticket Request handled correctly via Rule")

    def test_missing_info_logic(self):
        """Test Rule: Missing Info (Hotel/Room)"""
        print("\n--- Testing Missing Info Logic ---")
        
        # Setup: Missing Hotel, Future Trip
        fields = {
            'trip Name': 'Sea Trip',
            'Booking Nr.': '456',
            'Date Trip': '2026-05-01T10:00:00.000Z', # Future
            'Customer Email': 'test@example.com',
            'Hotel Name': '', # MISSING
            'Room number': '' # MISSING
        }
        
        # Mock AI to return a specific response if it reaches AI (which it shouldn't if we had a strict rule, 
        # but handle_customer_inquiry relies on AI for the text, but prompts it with strict instructions)
        
        # Actually, in handle_customer_inquiry, we construct a prompt. 
        # We can't easily test the AI's output without mocking query_ai to return what we expect the AI to say given the prompt.
        # But we CAN check if the prompt contains the correct instructions.
        
        with patch.object(self.agent, 'query_ai', return_value="Please provide hotel name") as mock_ai:
            self.agent.handle_customer_inquiry('rec456', fields, "When is pickup?")
            
            # Check the prompt sent to AI
            call_args = mock_ai.call_args_list[1] # 0 is analysis, 1 is final response
            prompt_sent = call_args[0][0]
            
            self.assertIn("**MISSING_HOTEL_INFO**: True", prompt_sent)
            self.assertIn("**RULE 2: MISSING DETAILS", prompt_sent)
            print("✔ Prompt correctly flagged missing info")

    def test_kb_priority(self):
        """Test Hybrid Logic: KB should be prioritized"""
        print("\n--- Testing Knowledge Base Priority ---")
        
        fields = {'trip Name': 'Safari', 'Customer Email': 'test@example.com'}
        
        # Mock KB Result
        self.agent.kb.search.return_value = [{'source': 'Trip DB', 'content': 'Safari starts at 8 AM', 'score': 10}]
        
        with patch.object(self.agent, 'query_ai') as mock_ai:
            self.agent.handle_customer_inquiry('rec789', fields, "What time does it start?")
            
            prompt_sent = mock_ai.call_args_list[1][0][0]
            self.assertIn("**KNOWLEDGE BASE (Trusted Internal Data):**", prompt_sent)
            self.assertIn("Safari starts at 8 AM", prompt_sent)
            print("✔ Knowledge Base results included in prompt")

if __name__ == '__main__':
    unittest.main()
