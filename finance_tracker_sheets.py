# -*- coding: utf-8 -*-
"""
Finance Tracker with Google Sheets Integration
Replaces CSV output with Google Sheets API
"""

import json
import datetime
import os
from dotenv import load_dotenv
from plaid import Configuration, ApiClient
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest

# Google Sheets imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

# Plaid credentials from environment
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")

# Google Sheets configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")  # Add this to your .env file
SHEET_NAME = "All_Transactions"  # Name of the sheet tab

# Configure Plaid client
plaid_host = os.getenv("PLAID_HOST", "https://sandbox.plaid.com")
config = Configuration(
    host=plaid_host,
    api_key={"clientId": PLAID_CLIENT_ID, "secret": PLAID_SECRET}
)
client = plaid_api.PlaidApi(ApiClient(config))

def load_access_token():
    """Load access token from file with persistence check"""
    try:
        with open('_access_token.json', 'r') as f:
            data = json.load(f)
            access_token = data['access_token']
            
            # Check if token is still valid (basic check)
            created_at = datetime.datetime.fromisoformat(data.get('created_at', '2020-01-01'))
            if (datetime.datetime.now() - created_at).days > 30:
                print("⚠️  Access token is older than 30 days. Consider refreshing.")
            
            return access_token
    except FileNotFoundError:
        print("❌ _access_token.json not found. Run connect_api_bank.py first to get an access token.")
        return None
    except Exception as e:
        print(f"❌ Error loading access token: {e}")
        return None

def save_access_token(access_token):
    """Save access token with timestamp for persistence tracking"""
    token_data = {
        'access_token': access_token,
        'created_at': datetime.datetime.now().isoformat(),
        'last_used': datetime.datetime.now().isoformat()
    }
    with open('_access_token.json', 'w') as f:
        json.dump(token_data, f, indent=2)
    print(f"✅ Access token saved to _access_token.json")

def update_token_usage():
    """Update last_used timestamp for token tracking"""
    try:
        with open('_access_token.json', 'r') as f:
            data = json.load(f)
        data['last_used'] = datetime.datetime.now().isoformat()
        with open('_access_token.json', 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not update token usage timestamp: {e}")

def authenticate_google_sheets():
    """Authenticate with Google Sheets API using Service Account"""
    try:
        if not os.path.exists('credentials.json'):
            print("❌ credentials.json not found!")
            print("Please download your Google Cloud Service Account key and save it as 'credentials.json'")
            return None
        
        # Use Service Account credentials
        creds = service_account.Credentials.from_service_account_file(
            'credentials.json', 
            scopes=SCOPES
        )
        
        return creds
        
    except Exception as e:
        print(f"❌ Error authenticating with Google Sheets: {e}")
        return None

def get_sheets_service():
    """Get Google Sheets service object"""
    creds = authenticate_google_sheets()
    if not creds:
        return None
    
    try:
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        print(f"❌ Error creating Google Sheets service: {e}")
        return None

def list_sheet_names(service):
    """List all sheet names in the spreadsheet"""
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = spreadsheet.get('sheets', [])
        sheet_names = [sheet['properties']['title'] for sheet in sheets]
        return sheet_names
    except Exception as e:
        print(f"❌ Error listing sheets: {e}")
        return []

def categorize(txn):
    """Categorize transaction based on business logic (ported from v3)"""
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

    # Rule 1: Handle payment methods
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
    """Get existing transaction IDs from Google Sheets"""
    try:
        range_name = f"{SHEET_NAME}!A:A"  # Column A contains transaction IDs
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, 
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        # Skip header row and return set of transaction IDs
        return set(row[0] for row in values[1:] if row)
    except Exception as e:
        print(f"⚠️  Could not fetch existing transactions: {e}")
        return set()

def setup_sheet_headers(service):
    """Set up headers in the Google Sheet if not already present"""
    try:
        # Check if headers exist
        range_name = f"{SHEET_NAME}!A1:F1"
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, 
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        # If no headers or wrong headers, set them up
        if not values or values[0] != ['transaction_id', 'date', 'name', 'amount', 'category', 'project']:
            headers = [['transaction_id', 'date', 'name', 'amount', 'category', 'project']]
            
            body = {
                'values': headers
            }
            
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_NAME}!A1:F1",
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print("✅ Sheet headers set up successfully")
        
    except Exception as e:
        print(f"❌ Error setting up sheet headers: {e}")

def append_transactions_to_sheet(service, transactions_data):
    """Append new transactions to Google Sheet"""
    if not transactions_data:
        return
    
    try:
        range_name = f"{SHEET_NAME}!A:F"
        
        body = {
            'values': transactions_data
        }
        
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        print(f"✅ Added {len(transactions_data)} transactions to Google Sheet")
        
    except Exception as e:
        print(f"❌ Error appending to Google Sheet: {e}")

def main():
    print("=== Finance Tracker with Google Sheets ===")
    
    # Validate environment
    if not SPREADSHEET_ID:
        print("❌ GOOGLE_SHEET_ID not found in environment variables")
        print("Please add GOOGLE_SHEET_ID to your .env file")
        return
    
    # Load access token
    access_token = load_access_token()
    if not access_token:
        return
    
    print("✅ Access token loaded successfully")
    update_token_usage()
    
    # Get Google Sheets service
    service = get_sheets_service()
    if not service:
        return
    
    print("✅ Google Sheets service authenticated")
    
    # List available sheets
    sheet_names = list_sheet_names(service)
    print(f"Available sheets: {sheet_names}")
    
    # Set up sheet headers
    setup_sheet_headers(service)
    
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
        return
    
    # Process and categorize transactions
    new_transactions = []
    
    for t in transactions:
        if t.transaction_id not in existing_ids:
            tags = categorize(t)
            row = [t.transaction_id, t.date.isoformat(), t.name, t.amount, tags["category"], tags["project"]]
            new_transactions.append(row)
    
    # Append new transactions to Google Sheet
    if new_transactions:
        append_transactions_to_sheet(service, new_transactions)
        print("New transactions:")
        for t in new_transactions[:5]:  # Show first 5
            print(f"  {t[2]} - ${t[3]} ({t[4]})")
        if len(new_transactions) > 5:
            print(f"  ... and {len(new_transactions) - 5} more")
    else:
        print("✅ No new transactions found")
    
    print(f"\n✅ Sync completed successfully!")
    print(f"Total new transactions processed: {len(new_transactions)}")

if __name__ == "__main__":
    main()
