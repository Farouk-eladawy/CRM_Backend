import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_FILE = 'google_reviews_token.json'

def get_google_reviews():
    if not os.path.exists(TOKEN_FILE):
        print("Token file not found.")
        return

    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    
    try:
        # Fetch Accounts
        account_mgmt = build('mybusinessaccountmanagement', 'v1', credentials=creds)
        accounts_result = account_mgmt.accounts().list().execute()
        accounts = accounts_result.get('accounts', [])
        
        if not accounts:
            print("No accounts found.")
            return
            
        print(f"Found {len(accounts)} accounts:")
        for acc in accounts:
            print(f"- Account Name: {acc.get('name')} | Account Title: {acc.get('accountName')}")
            
            # Fetch Locations for each account
            # Using mybusinessbusinessinformation API
            business_info = build('mybusinessbusinessinformation', 'v1', credentials=creds)
            locations_result = business_info.accounts().locations().list(parent=acc['name']).execute()
            locations = locations_result.get('locations', [])
            
            print(f"  Found {len(locations)} locations:")
            for loc in locations:
                print(f"  - Location Name (ID): {loc.get('name')} | Title: {loc.get('title')}")
                
                # Fetch reviews for the location
                reviews_api = build('mybusinessreviews', 'v1', credentials=creds)
                try:
                    reviews_result = reviews_api.accounts().locations().reviews().list(parent=loc['name']).execute()
                    reviews = reviews_result.get('reviews', [])
                    print(f"    -> Found {len(reviews)} reviews (showing latest 1):")
                    if reviews:
                        print(f"       {reviews[0]}")
                except Exception as e:
                    print(f"    -> Could not fetch reviews: {e}")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    get_google_reviews()