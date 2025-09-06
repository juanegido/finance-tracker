# -*- coding: utf-8 -*-
"""
Google Sheets Setup Helper
Helps set up Google Sheets API authentication
"""

import os
from dotenv import load_dotenv

def main():
    print("=== Google Sheets Setup Helper ===")
    print()
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Please create a .env file with your configuration.")
        return
    
    load_dotenv()
    
    # Check for required environment variables
    required_vars = ['PLAID_CLIENT_ID', 'PLAID_SECRET', 'GOOGLE_SHEET_ID']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print()
        print("Please add these to your .env file:")
        print("PLAID_CLIENT_ID=your_plaid_client_id")
        print("PLAID_SECRET=your_plaid_secret")
        print("GOOGLE_SHEET_ID=your_google_sheet_id")
        return
    
    print("✅ All required environment variables found")
    
    # Check for credentials.json
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json not found!")
        print()
        print("To set up Google Sheets API:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing one")
        print("3. Enable Google Sheets API")
        print("4. Go to 'Credentials' → 'Create Credentials' → 'OAuth 2.0 Client ID'")
        print("5. Choose 'Desktop application'")
        print("6. Download the JSON file and save as 'credentials.json'")
        return
    
    print("✅ credentials.json found")
    
    # Check for access token
    if not os.path.exists('_access_token.json'):
        print("❌ _access_token.json not found!")
        print("Please run connect_api_bank.py and get_token.py first to set up Plaid access token")
        return
    
    print("✅ _access_token.json found")
    
    print()
    print("🎉 Setup looks good!")
    print("You can now run: python finance_tracker_sheets.py")
    print()
    print("Note: On first run, you'll be prompted to authenticate with Google.")
    print("This will create a token.json file for future use.")

if __name__ == "__main__":
    main()
