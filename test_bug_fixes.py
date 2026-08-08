import unittest
import os
import sqlite3
from datetime import datetime, date
from knowledge_base import KnowledgeBase
from ai_agent import AIAgent

class TestBugFixes(unittest.TestCase):
    def setUp(self):
        # Setup temporary DB for KB
        self.db_path = "test_kb.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.kb = KnowledgeBase(self.db_path)
        
        # Setup Agent (mocking config)
        self.agent = AIAgent()
        # Mock timezone if needed (but it tries to load pytz)

    def tearDown(self):
        # Close connection before deleting
        if hasattr(self, 'kb') and self.kb.conn:
            self.kb.conn.close()
            
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass # Ignore if still locked (Windows is strict)
            
    def test_fts5_sanitization(self):
        """Test that searching with special chars does not crash"""
        # Insert a dummy record
        cur = self.kb.conn.cursor()
        cur.execute("INSERT INTO trips (id, title, description, itinerary, faqs) VALUES (?, ?, ?, ?, ?)", 
                    ("1", "Test Trip", "A great trip.", "Itinerary here.", "FAQ"))
        cur.execute("INSERT INTO trips_fts (title, description, itinerary, faqs) VALUES (?, ?, ?, ?)", 
                    ("Test Trip", "A great trip.", "Itinerary here.", "FAQ"))
        self.kb.conn.commit()
        
        # 1. Search with dot (caused syntax error before)
        try:
            results = self.kb.search("Mrs. Smith")
            print("Search with dot: Success")
        except Exception as e:
            self.fail(f"Search with dot failed: {e}")
            
        # 2. Search with quotes and colon
        try:
            results = self.kb.search('Title: "Test"')
            print("Search with quotes/colon: Success")
        except Exception as e:
            self.fail(f"Search with quotes/colon failed: {e}")

    def test_date_correction(self):
        """Test date parsing logic"""
        # 1. Standard ISO with Time (Midnight UTC)
        # 2026-01-21T00:00:00.000Z -> Should be Jan 21 (converted to Cairo 02:00)
        d, fmt = self.agent.get_corrected_trip_date("2026-01-21T00:00:00.000Z")
        self.assertEqual(d, date(2026, 1, 21))
        
        # 2. ISO with Time (Late night UTC)
        # 2026-01-20T22:00:00.000Z -> Should be Jan 21 (Cairo 00:00)
        d, fmt = self.agent.get_corrected_trip_date("2026-01-20T22:00:00.000Z")
        self.assertEqual(d, date(2026, 1, 21))
        
        # 3. Simple Date String
        d, fmt = self.agent.get_corrected_trip_date("2026-01-21")
        self.assertEqual(d, date(2026, 1, 21))

if __name__ == '__main__':
    unittest.main()
