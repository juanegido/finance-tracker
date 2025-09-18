#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Finance Tracker Sync - Versión Simplificada
Solo sincroniza transacciones de Plaid a Google Sheets
"""

import json
import datetime
import os
import sys
from dotenv import load_dotenv
from plaid import Configuration, ApiClient
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest

# Google Sheets imports
from google.oauth2.credentials import Credentials
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
SHEET_NAME = "All_Transactions"

# Configure Plaid client
plaid_host = "https://sandbox.plaid.com" if PLAID_ENV == "sandbox" else "https://production.plaid.com"
config = Configuration(
    host=plaid_host,
    api_key={"clientId": PLAID_CLIENT_ID, "secret": PLAID_SECRET}
)
client = plaid_api.PlaidApi(ApiClient(config))

def load_access_token():
    """Load Plaid access token"""
    try:
        with open('_access_token.json', 'r') as f:
            data = json.load(f)
            return data['access_token']
    except FileNotFoundError:
        print("❌ _access_token.json not found. Run python setup.py first")
        return None
    except Exception as e:
        print(f"❌ Error loading access token: {e}")
        return None

def get_google_sheets_service():
    """Get Google Sheets service"""
    try:
        # Check credential type
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
                # If no token, do authentication flow
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Save token for future use
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
        
        service = build('sheets', 'v4', credentials=creds)
        return service
        
    except Exception as e:
        print(f"❌ Error authenticating with Google Sheets: {e}")
        return None

def categorize_transaction(txn):
    """Categorize transaction based on business logic"""
    name = txn.name.lower() if txn.name else ""

    # Subcontractor database
    SUBCONTRACTOR_DATABASE = {
        "all-pro plumbing":   {"service": "Plumbing"},
        "j&l electric":       {"service": "Electrical"},
        "sal's drywall":      {"service": "Drywall & Paint"},
        "creative landscape": {"service": "Landscaping"},
        "best quality roofing": {"service": "Roofing"},
        "a-1 painting":       {"service": "Drywall & Paint"},
        "precision framing":  {"service": "Framing"},
        "elite concrete":     {"service": "Concrete & Foundation"},
        "custom cabinetry":  {"service": "Cabinets & Millwork"},
        "total home insulation": {"service": "Insulation"},
        "flores tile & stone": {"service": "Flooring & Tile"},
        "window world":       {"service": "Windows & Doors"}
    }

    # Rule 1: Payment methods
    if "quickbooks" in name or "intuit" in name:
        return {"category": "QuickBooks Bill Pay", "project": "NEEDS REVIEW"}
    if "zelle" in name:
        return {"category": "Zelle Payment", "project": "Bellevue"}
    if "check #" in name:
        return {"category": "Subcontractor Payout", "project": "Bellevue"}

    # Rule 2: Check subcontractor database
    for sub_keyword, sub_details in SUBCONTRACTOR_DATABASE.items():
        if sub_keyword in name:
            return {"category": sub_details["service"], "project": "Bellevue"}

    # Rule 3: Handle vendors
    if any(vendor in name for vendor in ["home depot", "lowe's", "sherwin-williams"]):
        return {"category": "Materials", "project": "Bellevue"}
    if any(vendor in name for vendor in ["sunbelt", "united rentals"]):
        return {"category": "Equipment Rental", "project": "Bellevue"}
    if any(vendor in name for vendor in ["chevron", "shell", "76"]):
        return {"category": "Fuel", "project": "Admin"}

    # Rule 4: Default
    return {"category": "Uncategorized", "project": "Unknown"}

def get_existing_transaction_ids(service):
    """Get existing transaction IDs from Google Sheet"""
    try:
        range_name = f"{SHEET_NAME}!A:A"  # Column A contains transaction IDs
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, 
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        # Skip header and return set of transaction IDs
        return set(row[0] for row in values[1:] if row)
    except Exception as e:
        print(f"⚠️  Could not fetch existing transactions: {e}")
        return set()

def append_transactions_to_sheet(service, transactions_data):
    """Append new transactions to Google Sheet"""
    if not transactions_data:
        return
    
    try:
        range_name = f"{SHEET_NAME}!A:F"
        
        body = {'values': transactions_data}
        
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        print(f"[OK] Added {len(transactions_data)} transactions to Google Sheet")
        
    except Exception as e:
        print(f"❌ Error appending to Google Sheet: {e}")

def main():
    print("=== Finance Tracker Sync ===")
    
    # Validate configuration
    if not SPREADSHEET_ID:
        print("❌ GOOGLE_SHEET_ID not found in environment variables")
        print("Add GOOGLE_SHEET_ID to your .env file")
        return 1
    
    # Load Plaid access token
    access_token = load_access_token()
    if not access_token:
        return 1
    
    print("[OK] Plaid access token loaded")
    
    # Get Google Sheets service
    service = get_google_sheets_service()
    if not service:
        return 1
    
    print("[OK] Google Sheets service authenticated")
    
    # Get existing transactions
    existing_ids = get_existing_transaction_ids(service)
    print(f"Found {len(existing_ids)} existing transactions in sheet")
    
    # Fetch recent transactions from Plaid
    print("Fetching recent transactions from Plaid...")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=60)).date()
    end_date = datetime.datetime.now().date()
    
    try:
        txn_req = TransactionsGetRequest(access_token=access_token, start_date=start_date, end_date=end_date)
        txn_resp = client.transactions_get(txn_req)
        transactions = txn_resp.transactions
        print(f"Fetched {len(transactions)} total transactions")
    except Exception as e:
        print(f"❌ Error fetching transactions: {e}")
        return 1
    
    # Process and categorize transactions
    new_transactions = []
    
    for t in transactions:
        if t.transaction_id not in existing_ids:
            tags = categorize_transaction(t)
            row = [t.transaction_id, t.date.isoformat(), t.name, t.amount, tags["category"], tags["project"]]
            new_transactions.append(row)
    
    # Append new transactions to Google Sheet
    if new_transactions:
        append_transactions_to_sheet(service, new_transactions)
        print("\nNew transactions:")
        for t in new_transactions[:5]:  # Show first 5
            print(f"  {t[2]} - ${t[3]} ({t[4]})")
        if len(new_transactions) > 5:
            print(f"  ... and {len(new_transactions) - 5} more")
    else:
        print("[OK] No new transactions found")
    
    print(f"\n[OK] Sync completed successfully!")
    print(f"Total new transactions processed: {len(new_transactions)}")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
