#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup simplificado para Finance Tracker
Configura Plaid y Google Sheets en un solo archivo
"""

import os
import json
import datetime
from dotenv import load_dotenv
from plaid import Configuration, ApiClient
from plaid.api import plaid_api
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

# Google Sheets imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

# Load environment variables
load_dotenv()

# Plaid credentials from environment
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")

# Google Sheets configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# Configure Plaid client
plaid_host = "https://sandbox.plaid.com" if PLAID_ENV == "sandbox" else "https://production.plaid.com"
config = Configuration(
    host=plaid_host,
    api_key={"clientId": PLAID_CLIENT_ID, "secret": PLAID_SECRET}
)
client = plaid_api.PlaidApi(ApiClient(config))

def check_environment():
    """Check required environment variables"""
    print("=== Checking Configuration ===")
    
    required_vars = {
        'PLAID_CLIENT_ID': PLAID_CLIENT_ID,
        'PLAID_SECRET': PLAID_SECRET,
        'GOOGLE_SHEET_ID': SPREADSHEET_ID
    }
    
    missing_vars = []
    for var, value in required_vars.items():
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {value[:10]}..." if len(str(value)) > 10 else f"✅ {var}: {value}")
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Add these to your .env file:")
        for var in missing_vars:
            print(f"{var}=your_value_here")
        return False
    
    print("✅ All environment variables configured")
    return True

def setup_plaid():
    """Setup Plaid connection"""
    print("\n=== Setting up Plaid ===")
    
    # Check if access token already exists
    if os.path.exists('_access_token.json'):
        print("✅ Access token already exists")
        return True
    
    print("Creating link token...")
    try:
        user = LinkTokenCreateRequestUser(client_user_id="user-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        req = LinkTokenCreateRequest(
            user=user,
            client_name="Finance Tracker",
            products=[Products("transactions")],
            country_codes=[CountryCode("US")],
            language="en"
        )
        resp = client.link_token_create(req)
        link_token = resp.link_token
        print(f"✅ Link token created: {link_token[:20]}...")
        
        # For sandbox, use test credentials
        if PLAID_ENV == "sandbox":
            print("\n=== Using Sandbox Test Credentials ===")
            print("Username: user_good")
            print("Password: pass_good")
            
            # Create HTML for testing
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Plaid Link Test</title>
    <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
</head>
<body>
    <h2>Connect Bank</h2>
    <button id="link-button">Connect Bank</button>
    <div id="result"></div>
    
    <script>
        document.getElementById('link-button').onclick = function() {{
            const handler = Plaid.create({{
                token: '{link_token}',
                onSuccess: async function(public_token, metadata) {{
                    console.log('Success!', public_token);
                    document.getElementById('result').innerHTML = 
                        '<p>Success! Public token: ' + public_token + '</p>' +
                        '<p>Copy this token and run: python setup.py --exchange-token ' + public_token + '</p>';
                }},
                onExit: function(err, metadata) {{
                    console.log('Exit', err, metadata);
                }}
            }});
            handler.open();
        }};
    </script>
</body>
</html>
"""
            with open('plaid_link.html', 'w') as f:
                f.write(html_content)
            
            print("4. Open plaid_link.html in your browser to connect")
            print("5. After getting the public token, run:")
            print("   python setup.py --exchange-token YOUR_PUBLIC_TOKEN")
            
        return True
        
    except Exception as e:
        print(f"❌ Error creating link token: {e}")
        return False

def exchange_public_token(public_token):
    """Exchange public token for access token"""
    print(f"\n=== Exchanging public token ===")
    
    try:
        ex = client.item_public_token_exchange(ItemPublicTokenExchangeRequest(public_token=public_token))
        access_token = ex.access_token
        
        # Save access token
        token_data = {
            'access_token': access_token,
            'created_at': datetime.datetime.now().isoformat(),
            'environment': PLAID_ENV
        }
        
        with open('_access_token.json', 'w') as f:
            json.dump(token_data, f, indent=2)
        
        print(f"✅ Access token saved to _access_token.json")
        return True
        
    except Exception as e:
        print(f"❌ Error exchanging token: {e}")
        return False

def setup_google_sheets():
    """Setup Google Sheets"""
    print("\n=== Setting up Google Sheets ===")
    
    # Check if credentials.json exists
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json not found!")
        print("\nTo setup Google Sheets API:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing one")
        print("3. Enable Google Sheets API")
        print("4. Go to 'Credentials' → 'Create Credentials' → 'Service Account'")
        print("5. Download the JSON file and save as 'credentials.json'")
        print("6. Share your Google Sheet with the service account email")
        return False
    
    print("✅ credentials.json found")
    
    # Check if it's Service Account or OAuth
    try:
        with open('credentials.json', 'r') as f:
            creds_data = json.load(f)
        
        if 'type' in creds_data and creds_data['type'] == 'service_account':
            print("✅ Service Account detected - no additional authentication required")
            return True
        else:
            # It's OAuth credentials, check if token.json exists
            if os.path.exists('token.json'):
                print("✅ Google Sheets token already exists")
                return True
            
            # Authenticate with Google OAuth
            print("Authenticating with Google OAuth...")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Save token for future use
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            
            print("✅ Google authentication completed")
            return True
        
    except Exception as e:
        print(f"❌ Error authenticating with Google: {e}")
        return False

def setup_sheet_headers():
    """Setup headers in Google Sheet"""
    print("\n=== Setting up Google Sheet headers ===")
    
    try:
        # Authenticate based on credential type
        with open('credentials.json', 'r') as f:
            creds_data = json.load(f)
        
        if 'type' in creds_data and creds_data['type'] == 'service_account':
            # Service Account
            creds = service_account.Credentials.from_service_account_file(
                'credentials.json', 
                scopes=SCOPES
            )
        else:
            # OAuth
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
        
        service = build('sheets', 'v4', credentials=creds)
        
        # Check if headers already exist
        range_name = "All_Transactions!A1:F1"
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, 
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        # If no headers or wrong headers, set them up
        if not values or values[0] != ['transaction_id', 'date', 'name', 'amount', 'category', 'project']:
            headers = [['transaction_id', 'date', 'name', 'amount', 'category', 'project']]
            
            body = {'values': headers}
            
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range="All_Transactions!A1:F1",
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print("✅ Headers set up in Google Sheet")
        else:
            print("✅ Headers already exist in Google Sheet")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up headers: {e}")
        return False

def main():
    import sys
    
    # If --exchange-token is passed, exchange token
    if len(sys.argv) > 2 and sys.argv[1] == '--exchange-token':
        public_token = sys.argv[2]
        if exchange_public_token(public_token):
            print("\n🎉 Plaid setup completed!")
            print("Now run: python setup.py to complete configuration")
        return
    
    print("=== Finance Tracker Setup ===")
    
    # Check environment
    if not check_environment():
        return
    
    # Setup Plaid
    if not setup_plaid():
        return
    
    # Setup Google Sheets
    if not setup_google_sheets():
        return
    
    # Setup sheet headers
    if not setup_sheet_headers():
        return
    
    print("\n🎉 Setup completed!")
    print("You can now run: python sync.py")

if __name__ == "__main__":
    main()
