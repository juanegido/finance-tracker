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
SHEET_NAME = "All_Transactions"

# Configure Plaid client
plaid_host = "https://sandbox.plaid.com" if PLAID_ENV == "sandbox" else "https://production.plaid.com"
config = Configuration(
    host=plaid_host,
    api_key={"clientId": PLAID_CLIENT_ID, "secret": PLAID_SECRET}
)
client = plaid_api.PlaidApi(ApiClient(config))

def load_bank_accounts():
    """Load bank account manager and migrate legacy token if needed"""
    bank_manager = BankAccountManager(client)
    
    # Try to migrate legacy token if no accounts exist
    if not bank_manager.accounts:
        print("[INFO] No bank accounts found. Checking for legacy token...")
        if bank_manager.migrate_legacy_token():
            print("[OK] Legacy token migrated to new system")
        else:
            print("[ERROR] No bank accounts linked. Run 'python setup.py' to link accounts")
            return None
    
    return bank_manager

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
        print(f"[ERROR] Error authenticating with Google Sheets: {e}")
        return None

def categorize_transaction(txn):
    """
    The "Brain" - Advanced Categorization Function
    This function contains the specific business logic for the remodeler client.
    It uses a subcontractor "database" to assign a specific scope of work.
    """
    # Use .lower() and handle cases where the name might be missing
    name = txn.name.lower() if txn.name else ""

    # ===================================================================
    # STEP 1: THE SUBCONTRACTOR DATABASE
    # Maps a keyword from the sub's name to their specific service.
    # This is our source of truth.
    # ===================================================================
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

    # ===================================================================
    # RULE 1: HANDLE TRICKY PAYMENT METHODS FIRST
    # ===================================================================
    if "quickbooks" in name or "intuit" in name:
        return {"category": "QuickBooks Bill Pay", "project": "NEEDS REVIEW"}
    if "zelle" in name:
        return {"category": "Zelle Payment", "project": "Bellevue"}
    if "check #" in name:
        return {"category": "Subcontractor Payout", "project": "Bellevue"}

    # ===================================================================
    # RULE 2: CHECK THE SUBCONTRACTOR DATABASE (THE NEW, SMART RULE)
    # ===================================================================
    for sub_keyword, sub_details in SUBCONTRACTOR_DATABASE.items():
        if sub_keyword in name:
            # We found a match! Use the specific service as the category.
            return {"category": sub_details["service"], "project": "Bellevue"}

    # ===================================================================
    # RULE 3: HANDLE KNOWN MATERIAL & EQUIPMENT VENDORS
    # ===================================================================
    if any(vendor in name for vendor in ["home depot", "lowe's", "sherwin-williams"]):
        return {"category": "Materials", "project": "Bellevue"}
    if any(vendor in name for vendor in ["sunbelt", "united rentals"]):
        return {"category": "Equipment Rental", "project": "Bellevue"}
    if any(vendor in name for vendor in ["chevron", "shell", "76"]):
        return {"category": "Fuel", "project": "Admin"}

    # ===================================================================
    # RULE 4: DEFAULT CATCH-ALL
    # ===================================================================
    else:
        return {"category": "Uncategorized", "project": "Unknown"}

def get_existing_transaction_ids(service, sheet_name):
    """Get existing transaction IDs from a specific Google Sheet"""
    try:
        range_name = f"{sheet_name}!A:A"  # Column A contains transaction IDs
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, 
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        # Skip header and return set of transaction IDs
        return set(row[0] for row in values[1:] if row)
    except Exception as e:
        print(f"[WARNING] Could not fetch existing transactions from {sheet_name}: {e}")
        return set()

def create_sheet_if_not_exists(service, sheet_name):
    """Create a new sheet if it doesn't exist"""
    try:
        # Get all sheets
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
        
        if sheet_name not in existing_sheets:
            print(f"Creating new sheet: {sheet_name}")
            
            # Create new sheet
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }
            
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=request_body
            ).execute()
            
            # Set up headers
            headers = [['transaction_id', 'date', 'name', 'amount', 'category', 'project']]
            body = {'values': headers}
            
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{sheet_name}!A1:F1",
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"[OK] Created sheet '{sheet_name}' with headers")
        else:
            print(f"[OK] Sheet '{sheet_name}' already exists")
            
    except Exception as e:
        print(f"[ERROR] Error creating sheet '{sheet_name}': {e}")

def get_all_existing_transaction_ids(service, bank_manager):
    """Get all existing transaction IDs from all bank sheets"""
    all_ids = set()
    for account_id, account_data in bank_manager.accounts.items():
        sheet_name = account_data.get('sheet_name', account_data['account_name'])
        sheet_ids = get_existing_transaction_ids(service, sheet_name)
        all_ids.update(sheet_ids)
    return all_ids

def append_transactions_to_sheet(service, transactions_data, sheet_name):
    """Append new transactions to a specific Google Sheet"""
    if not transactions_data:
        return
    
    try:
        range_name = f"{sheet_name}!A:F"  # No account column needed since each sheet is for one bank
        
        body = {'values': transactions_data}
        
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        print(f"[OK] Added {len(transactions_data)} transactions to sheet '{sheet_name}'")
        
    except Exception as e:
        print(f"[ERROR] Error appending to sheet '{sheet_name}': {e}")

def main():
    print("=== Finance Tracker Sync ===")
    
    # Validate configuration
    if not SPREADSHEET_ID:
        print("[ERROR] GOOGLE_SHEET_ID not found in environment variables")
        print("Add GOOGLE_SHEET_ID to your .env file")
        return 1
    
    # Load bank accounts
    bank_manager = load_bank_accounts()
    if not bank_manager:
        return 1
    
    print(f"[OK] Loaded {len(bank_manager.accounts)} bank accounts")
    
    # Get Google Sheets service
    service = get_google_sheets_service()
    if not service:
        return 1
    
    print("[OK] Google Sheets service authenticated")
    
    # Get all existing transaction IDs from all sheets
    all_existing_ids = get_all_existing_transaction_ids(service, bank_manager)
    print(f"Found {len(all_existing_ids)} existing transactions across all sheets")
    
    # Fetch recent transactions from all bank accounts
    print("Fetching recent transactions from all bank accounts...")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=60)).date()
    end_date = datetime.datetime.now().date()
    
    total_new_transactions = 0
    
    # Process each bank account
    for account_id, access_token, account_name in bank_manager.get_all_access_tokens():
        print(f"\nProcessing {account_name}...")
        
        # Get account data to find sheet name
        account_data = bank_manager.get_account_info(account_id)
        sheet_name = account_data.get('sheet_name', account_name)
        
        # Create sheet if it doesn't exist
        create_sheet_if_not_exists(service, sheet_name)
        
        # Get existing transactions for this specific sheet
        sheet_existing_ids = get_existing_transaction_ids(service, sheet_name)
        
        try:
            txn_req = TransactionsGetRequest(access_token=access_token, start_date=start_date, end_date=end_date)
            txn_resp = client.transactions_get(txn_req)
            transactions = txn_resp.transactions
            print(f"  Fetched {len(transactions)} transactions")
            
            # Process and categorize transactions
            account_new_transactions = []
            
            for t in transactions:
                if t.transaction_id not in sheet_existing_ids:
                    tags = categorize_transaction(t)
                    # Row format: [transaction_id, date, name, amount, category, project]
                    row = [t.transaction_id, t.date.isoformat(), t.name, t.amount, tags["category"], tags["project"]]
                    account_new_transactions.append(row)
            
            if account_new_transactions:
                print(f"  Found {len(account_new_transactions)} new transactions")
                # Append to this bank's sheet
                append_transactions_to_sheet(service, account_new_transactions, sheet_name)
                total_new_transactions += len(account_new_transactions)
                
                # Show sample transactions
                print(f"  Sample transactions:")
                for t in account_new_transactions[:3]:
                    print(f"    {t[2]} - ${t[3]} ({t[4]})")
                if len(account_new_transactions) > 3:
                    print(f"    ... and {len(account_new_transactions) - 3} more")
                
                # Update last sync timestamp
                bank_manager.update_last_sync(account_id)
            else:
                print(f"  No new transactions")
                
        except Exception as e:
            print(f"  [ERROR] Error fetching transactions from {account_name}: {e}")
            continue
    
    print(f"\n[OK] Sync completed successfully!")
    print(f"Total new transactions processed: {total_new_transactions}")
    print(f"Each bank's transactions are now in separate sheets")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
