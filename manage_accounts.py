#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bank Account Management Utility
Standalone tool to manage multiple bank accounts
"""

import os
import sys
from dotenv import load_dotenv
from plaid import Configuration, ApiClient
from plaid.api import plaid_api
from bank_accounts import BankAccountManager

# Load environment variables
load_dotenv()

# Plaid credentials from environment
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")

# Configure Plaid client
plaid_host = "https://sandbox.plaid.com" if PLAID_ENV == "sandbox" else "https://production.plaid.com"
config = Configuration(
    host=plaid_host,
    api_key={"clientId": PLAID_CLIENT_ID, "secret": PLAID_SECRET}
)
client = plaid_api.PlaidApi(ApiClient(config))

def show_menu():
    """Show the main menu"""
    print("\n=== Bank Account Management ===")
    print("1. List all bank accounts")
    print("2. Add new bank account")
    print("3. Remove bank account")
    print("4. Test account connection")
    print("5. Migrate legacy token")
    print("6. Exit")
    print()

def list_accounts(bank_manager):
    """List all bank accounts"""
    bank_manager.list_accounts()

def add_account(bank_manager):
    """Add a new bank account"""
    print("\n=== Add New Bank Account ===")
    
    # Get account name from user
    account_name = input("Enter a name for this bank account (or press Enter for auto-generated): ").strip()
    if not account_name:
        account_name = None
    
    # Get public token from user
    print("\nTo link a new account:")
    print("1. Run 'python setup.py' to get a link token")
    print("2. Use the generated plaid_link.html to connect your bank")
    print("3. Copy the public token and paste it here")
    
    while True:
        public_token = input("\nEnter public token (or 'cancel' to exit): ").strip()
        
        if public_token.lower() == 'cancel':
            print("Account linking cancelled")
            return
        
        if public_token and public_token.startswith('public-'):
            print("Exchanging public token for access token...")
            if exchange_public_token(public_token, bank_manager, account_name):
                print("Bank account added successfully!")
                return
            else:
                print("Failed to add bank account. Please try again.")
                continue
        else:
            print("Invalid token format. Please enter a valid public token.")
            continue

def remove_account(bank_manager):
    """Remove a bank account"""
    print("\n=== Remove Bank Account ===")
    
    if not bank_manager.accounts:
        print("No bank accounts to remove")
        return
    
    # Show accounts
    print("Current bank accounts:")
    for i, (account_id, account_data) in enumerate(bank_manager.accounts.items(), 1):
        print(f"{i}. {account_data['account_name']} ({account_data['institution_name']})")
    
    while True:
        try:
            choice = input(f"\nEnter account number to remove (1-{len(bank_manager.accounts)}) or 'cancel': ").strip()
            
            if choice.lower() == 'cancel':
                return
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(bank_manager.accounts):
                account_ids = list(bank_manager.accounts.keys())
                account_id = account_ids[choice_num - 1]
                account_name = bank_manager.accounts[account_id]['account_name']
                
                confirm = input(f"Are you sure you want to remove '{account_name}'? (y/n): ").strip().lower()
                if confirm in ['y', 'yes']:
                    bank_manager.remove_account(account_id)
                else:
                    print("Removal cancelled")
                return
            else:
                print(f"Please enter a number between 1 and {len(bank_manager.accounts)}")
        except ValueError:
            print("Please enter a valid number")

def test_connection(bank_manager):
    """Test connection to all bank accounts"""
    print("\n=== Testing Bank Account Connections ===")
    
    if not bank_manager.accounts:
        print("No bank accounts to test")
        return
    
    for account_id, account_data in bank_manager.accounts.items():
        print(f"\nTesting {account_data['account_name']}...")
        
        try:
            from plaid.model.accounts_get_request import AccountsGetRequest
            accounts_req = AccountsGetRequest(access_token=account_data['access_token'])
            accounts_resp = client.accounts_get(accounts_req)
            print(f"  ✓ Connection successful - {len(accounts_resp.accounts)} accounts found")
        except Exception as e:
            print(f"  ✗ Connection failed: {e}")

def migrate_legacy(bank_manager):
    """Migrate legacy access token"""
    print("\n=== Migrate Legacy Token ===")
    
    if bank_manager.migrate_legacy_token():
        print("Legacy token migrated successfully!")
    else:
        print("No legacy token found or migration failed")

def exchange_public_token(public_token, bank_manager, account_name=None):
    """Exchange public token for access token and add to bank manager"""
    try:
        from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
        ex = client.item_public_token_exchange(ItemPublicTokenExchangeRequest(public_token=public_token))
        access_token = ex.access_token
        
        # Add account to bank manager
        return bank_manager.add_account(access_token, account_name)
        
    except Exception as e:
        print(f"Error exchanging token: {e}")
        return False

def main():
    """Main function"""
    print("=== Finance Tracker - Bank Account Manager ===")
    
    # Validate configuration
    if not PLAID_CLIENT_ID or not PLAID_SECRET:
        print("[ERROR] Plaid credentials not found in environment variables")
        print("Make sure PLAID_CLIENT_ID and PLAID_SECRET are set in your .env file")
        return 1
    
    # Initialize bank account manager
    bank_manager = BankAccountManager(client)
    
    while True:
        show_menu()
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == '1':
            list_accounts(bank_manager)
        elif choice == '2':
            add_account(bank_manager)
        elif choice == '3':
            remove_account(bank_manager)
        elif choice == '4':
            test_connection(bank_manager)
        elif choice == '5':
            migrate_legacy(bank_manager)
        elif choice == '6':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1-6.")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
