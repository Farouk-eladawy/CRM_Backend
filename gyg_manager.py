import json
import os
import re

class GYGManager:
    def __init__(self, data_file="Get_Your_Guide_data.json"):
        self.data_file = data_file
        self.data = []
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                print(f"Loaded {len(self.data)} GYG trips.")
            except Exception as e:
                print(f"Error loading GYG data: {e}")
        else:
            print("GYG data file not found yet.")

    def search(self, query):
        """
        Search for trips in the local GYG data.
        Returns a list of formatted strings or dictionaries.
        """
        if not self.data:
            self.load_data() # Try reloading in case it was just created
            if not self.data:
                return []

        query_lower = query.lower()
        matches = []

        for trip in self.data:
            # Score based on title match
            score = 0
            title = trip.get('title', '').lower()
            full_text = trip.get('full_text', '').lower()
            
            if query_lower in title:
                score += 50
            elif query_lower in full_text:
                score += 10
            
            # Check for keyword overlap
            query_words = set(query_lower.split())
            title_words = set(re.sub(r'[^\w\s]', '', title).split())
            overlap = len(query_words.intersection(title_words))
            if overlap > 0:
                score += 5 * overlap

            if score > 0:
                matches.append((score, trip))

        # Sort by score
        matches.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matches[:3]] # Return top 3

    def format_trip_details(self, trip):
        """
        Format trip data for the AI context.
        """
        # Since we might have raw text dump, we present it as is or try to clean it.
        # If we have structured fields later, we use them.
        
        content = f"**Source:** Get Your Guide Supplier Portal\n"
        content += f"**Trip Name:** {trip.get('title')}\n"
        content += f"**Link:** {trip.get('url')}\n"
        
        if 'full_text' in trip:
            # Truncate if too long, or try to extract relevant sections if we had parsed them
            # For now, we provide a chunk of the text
            text = trip['full_text']
            # Simple heuristic to clean up navigation menus if possible (hard without DOM structure)
            content += f"**Details (Scraped):**\n{text[:2000]}...\n"
        
        return content
