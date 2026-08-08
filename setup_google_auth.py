import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes needed for Google My Business API
SCOPES = ['https://www.googleapis.com/auth/business.manage']

CLIENT_SECRET_FILE = 'client_secret_472093177999-1boehgsjfg94apu0et3r84i81171lrkh.apps.googleusercontent.com.json'
TOKEN_FILE = 'google_reviews_token.json'

def main():
    creds = None
    # Check if token file already exists
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing access token...")
            creds.refresh(Request())
        else:
            print("No valid token found. Starting OAuth flow...")
            # Use port 8090 to avoid conflict with Evolution API
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=8090)
            
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            print(f"Token saved successfully to {TOKEN_FILE}")
            
    print("Authentication successful! You can now use the Google Business Profile API.")

if __name__ == '__main__':
    main()