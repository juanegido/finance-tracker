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
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

# Bank account management
from bank_accounts import BankAccountManager

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
            print(f"[OK] {var}: {value[:10]}..." if len(str(value)) > 10 else f"[OK] {var}: {value}")
    
    if missing_vars:
        print(f"\n[ERROR] Missing environment variables: {', '.join(missing_vars)}")
        print("Add these to your .env file:")
        for var in missing_vars:
            print(f"{var}=your_value_here")
        return False
    
    print("[OK] All environment variables configured")
    return True

def setup_plaid():
    """Setup Plaid connection"""
    print("\n=== Setting up Plaid ===")
    
    # Initialize bank account manager
    bank_manager = BankAccountManager(client)
    
    # Check if we already have bank accounts
    if bank_manager.accounts:
        print(f"[OK] Found {len(bank_manager.accounts)} existing bank accounts")
        bank_manager.list_accounts()
        
        # Ask if user wants to add more accounts
        while True:
            add_more = input("\n[INPUT] Do you want to add another bank account? (y/n): ").strip().lower()
            if add_more in ['y', 'yes']:
                if link_new_account(bank_manager):
                    continue
                else:
                    break
            elif add_more in ['n', 'no']:
                break
            else:
                print("[ERROR] Please enter 'y' or 'n'")
        
        return True
    
    # Check if legacy access token exists
    if os.path.exists('_access_token.json'):
        print("[INFO] Found legacy access token. Migrating to new system...")
        if bank_manager.migrate_legacy_token():
            print("[OK] Legacy token migrated successfully")
            return True
        else:
            print("[ERROR] Failed to migrate legacy token")
    
    # No accounts found, need to link first account
    print("[INFO] No bank accounts found. Let's link your first account...")
    return link_new_account(bank_manager)

def link_new_account(bank_manager):
    """Link a new bank account"""
    print("\n=== Linking New Bank Account ===")
    
    # Get account name from user
    account_name = input("[INPUT] Enter a name for this bank account (or press Enter for auto-generated): ").strip()
    if not account_name:
        account_name = None
    
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
        print(f"[OK] Link token created: {link_token[:20]}...")
        
        # Create HTML for connection
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Plaid Link - Connect Your Bank</title>
    <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .container {{ max-width: 600px; margin: 0 auto; }}
        button {{ background: #007bff; color: white; padding: 15px 30px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }}
        button:hover {{ background: #0056b3; }}
        #result {{ margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
        .success {{ color: #28a745; }}
        .instructions {{ background: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Connect Your Bank Account</h2>
        <div class="instructions">
            <p><strong>Instructions:</strong></p>
            <p>1. Click "Connect Bank" below</p>
            <p>2. Select your bank and enter your credentials</p>
            <p>3. Copy the public token that appears</p>
            <p>4. Paste it in the terminal when prompted</p>
        </div>
        <button id="link-button">Connect Bank</button>
        <div id="result"></div>
    </div>
    
    <script>
        document.getElementById('link-button').onclick = function() {{
            const handler = Plaid.create({{
                token: '{link_token}',
                onSuccess: async function(public_token, metadata) {{
                    console.log('Success!', public_token);
                    document.getElementById('result').innerHTML = 
                        '<div class="success"><h3>[OK] Success!</h3>' +
                        '<p><strong>Public Token:</strong></p>' +
                        '<p style="background: white; padding: 10px; border-radius: 3px; word-break: break-all;">' + public_token + '</p>' +
                        '<p><strong>Copy this token and paste it in the terminal when prompted.</strong></p></div>';
                }},
                onExit: function(err, metadata) {{
                    console.log('Exit', err, metadata);
                    if (err) {{
                        document.getElementById('result').innerHTML = 
                            '<div style="color: #dc3545;"><h3>[ERROR] Connection Failed</h3>' +
                            '<p>Error: ' + err.error_message + '</p>' +
                            '<p>Please try again.</p></div>';
                    }}
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
        
        print(f"\n[INFO] Opening browser to connect your bank...")
        print(f"[INFO] If browser doesn't open, manually open: plaid_link.html")
        
        # Try to open browser automatically
        try:
            import webbrowser
            webbrowser.open('plaid_link.html')
        except:
            pass
        
        # Wait for user to provide public token
        print(f"\n[WAIT] Waiting for you to connect your bank...")
        print(f"[INFO] After connecting, copy the public token and paste it here:")
        
        while True:
            public_token = input("\n[INPUT] Enter public token (or 'quit' to exit): ").strip()
            
            if public_token.lower() == 'quit':
                print("[ERROR] Account linking cancelled")
                return False
            
            if public_token and public_token.startswith('public-'):
                print(f"[PROCESS] Exchanging public token for access token...")
                if exchange_public_token(public_token, bank_manager, account_name):
                    print(f"[OK] Bank account linked successfully!")
                    return True
                else:
                    print(f"[ERROR] Failed to exchange token. Please try again.")
                    continue
            else:
                print(f"[ERROR] Invalid token format. Please enter a valid public token.")
                continue
        
    except Exception as e:
        print(f"[ERROR] Error creating link token: {e}")
        return False

def exchange_public_token(public_token, bank_manager, account_name=None):
    """Exchange public token for access token and add to bank manager"""
    print(f"\n=== Exchanging public token ===")
    
    try:
        ex = client.item_public_token_exchange(ItemPublicTokenExchangeRequest(public_token=public_token))
        access_token = ex.access_token
        
        # Add account to bank manager
        if bank_manager.add_account(access_token, account_name):
            print(f"[OK] Bank account added successfully")
            return True
        else:
            print(f"[ERROR] Failed to add bank account")
            return False
        
    except Exception as e:
        print(f"[ERROR] Error exchanging token: {e}")
        return False

def setup_google_sheets():
    """Setup Google Sheets"""
    print("\n=== Setting up Google Sheets ===")
    
    # Check if credentials.json exists
    if not os.path.exists('credentials.json'):
        print("[ERROR] credentials.json not found!")
        print("\nTo setup Google Sheets API:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing one")
        print("3. Enable Google Sheets API")
        print("4. Go to 'Credentials' -> 'Create Credentials' -> 'Service Account'")
        print("5. Download the JSON file and save as 'credentials.json'")
        print("6. Share your Google Sheet with the service account email")
        return False
    
    print("[OK] credentials.json found")
    
    # Check if it's Service Account or OAuth
    try:
        with open('credentials.json', 'r') as f:
            creds_data = json.load(f)
        
        if 'type' in creds_data and creds_data['type'] == 'service_account':
            print("[OK] Service Account detected - no additional authentication required")
            return True
        else:
            # It's OAuth credentials, check if token.json exists
            if os.path.exists('token.json'):
                print("[OK] Google Sheets token already exists")
                return True
            
            # Authenticate with Google OAuth
            print("Authenticating with Google OAuth...")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Save token for future use
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            
            print("[OK] Google authentication completed")
            return True
        
    except Exception as e:
        print(f"[ERROR] Error authenticating with Google: {e}")
        return False

def setup_sheet_headers():
    """Setup headers in Google Sheet for each bank account"""
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
        
        # Initialize bank account manager to get account info
        bank_manager = BankAccountManager(client)
        
        if not bank_manager.accounts:
            print("[INFO] No bank accounts found. Headers will be set up when accounts are linked.")
            return True
        
        # Set up headers for each bank account sheet
        for account_id, account_data in bank_manager.accounts.items():
            sheet_name = account_data.get('sheet_name', account_data['account_name'])
            print(f"Setting up headers for sheet: {sheet_name}")
            
            try:
                # Check if headers already exist
                range_name = f"{sheet_name}!A1:F1"
                result = service.spreadsheets().values().get(
                    spreadsheetId=SPREADSHEET_ID, 
                    range=range_name
                ).execute()
                
                values = result.get('values', [])
                
                # If no headers or wrong headers, set them up
                expected_headers = ['transaction_id', 'date', 'name', 'amount', 'category', 'project']
                if not values or values[0] != expected_headers:
                    headers = [expected_headers]
                    
                    body = {'values': headers}
                    
                    service.spreadsheets().values().update(
                        spreadsheetId=SPREADSHEET_ID,
                        range=f"{sheet_name}!A1:F1",
                        valueInputOption='RAW',
                        body=body
                    ).execute()
                    
                    print(f"[OK] Headers set up for sheet '{sheet_name}'")
                else:
                    print(f"[OK] Headers already exist for sheet '{sheet_name}'")
                    
            except Exception as e:
                print(f"[WARNING] Could not set up headers for '{sheet_name}': {e}")
                continue
        
        print("[OK] Google Sheet headers setup completed")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error setting up headers: {e}")
        return False

def main():
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
    
    print("\n[SUCCESS] Setup completed!")
    print("You can now run: python sync.py")

if __name__ == "__main__":
    main()
