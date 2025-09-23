#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bank Account Management System
Handles multiple bank account connections and access tokens
"""

import json
import os
import datetime
from typing import List, Dict, Optional
from plaid import Configuration, ApiClient
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.item_get_request import ItemGetRequest

class BankAccountManager:
    def __init__(self, plaid_client):
        self.plaid_client = plaid_client
        self.accounts_file = '_bank_accounts.json'
        self.accounts = self._load_accounts()
    
    def _load_accounts(self) -> Dict:
        """Load bank accounts from file"""
        try:
            if os.path.exists(self.accounts_file):
                with open(self.accounts_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"[ERROR] Error loading bank accounts: {e}")
            return {}
    
    def _save_accounts(self):
        """Save bank accounts to file"""
        try:
            with open(self.accounts_file, 'w') as f:
                json.dump(self.accounts, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Error saving bank accounts: {e}")
    
    def add_account(self, access_token: str, account_name: str = None) -> bool:
        """Add a new bank account"""
        try:
            # Get account information from Plaid
            accounts_req = AccountsGetRequest(access_token=access_token)
            accounts_resp = self.plaid_client.accounts_get(accounts_req)
            
            # Get item information
            item_req = ItemGetRequest(access_token=access_token)
            item_resp = self.plaid_client.item_get(item_req)
            
            # Generate account ID
            account_id = f"account_{len(self.accounts) + 1}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Generate sheet name (clean and safe for Google Sheets)
            institution_name = item_resp.item.institution_name
            sheet_name = self._generate_sheet_name(institution_name, account_name)
            
            # Store account data
            account_data = {
                'access_token': access_token,
                'account_name': account_name or f"Bank Account {len(self.accounts) + 1}",
                'institution_name': institution_name,
                'sheet_name': sheet_name,
                'accounts': [
                    {
                        'account_id': acc.account_id,
                        'name': acc.name,
                        'type': str(acc.type) if acc.type else None,
                        'subtype': str(acc.subtype) if acc.subtype else None,
                        'mask': acc.mask
                    }
                    for acc in accounts_resp.accounts
                ],
                'created_at': datetime.datetime.now().isoformat(),
                'last_sync': None
            }
            
            self.accounts[account_id] = account_data
            self._save_accounts()
            
            print(f"[OK] Added account: {account_data['account_name']} ({account_data['institution_name']})")
            print(f"     Account ID: {account_id}")
            print(f"     Sheet name: {sheet_name}")
            print(f"     Linked accounts: {len(account_data['accounts'])}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Error adding account: {e}")
            return False
    
    def _generate_sheet_name(self, institution_name: str, account_name: str = None) -> str:
        """Generate a clean sheet name for Google Sheets"""
        # Use account name if provided, otherwise use institution name
        base_name = account_name or institution_name
        
        # Clean the name for Google Sheets (max 100 chars, no special chars)
        import re
        clean_name = re.sub(r'[^\w\s-]', '', base_name)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
        
        # Truncate if too long
        if len(clean_name) > 100:
            clean_name = clean_name[:97] + "..."
        
        # Ensure uniqueness
        existing_sheets = [acc.get('sheet_name', '') for acc in self.accounts.values()]
        if clean_name in existing_sheets:
            counter = 1
            original_name = clean_name
            while clean_name in existing_sheets:
                clean_name = f"{original_name} {counter}"
                counter += 1
        
        return clean_name
    
    def remove_account(self, account_id: str) -> bool:
        """Remove a bank account"""
        if account_id in self.accounts:
            account_name = self.accounts[account_id]['account_name']
            del self.accounts[account_id]
            self._save_accounts()
            print(f"[OK] Removed account: {account_name}")
            return True
        else:
            print(f"[ERROR] Account {account_id} not found")
            return False
    
    def list_accounts(self) -> List[Dict]:
        """List all bank accounts"""
        if not self.accounts:
            print("[INFO] No bank accounts linked")
            return []
        
        print("\n=== Linked Bank Accounts ===")
        for account_id, account_data in self.accounts.items():
            print(f"\nAccount ID: {account_id}")
            print(f"Name: {account_data['account_name']}")
            print(f"Institution: {account_data['institution_name']}")
            print(f"Created: {account_data['created_at']}")
            print(f"Last Sync: {account_data.get('last_sync', 'Never')}")
            print(f"Linked Accounts:")
            for acc in account_data['accounts']:
                print(f"  - {acc['name']} ({acc['type']}) ****{acc['mask']}")
        
        return list(self.accounts.values())
    
    def get_account_access_token(self, account_id: str) -> Optional[str]:
        """Get access token for a specific account"""
        if account_id in self.accounts:
            return self.accounts[account_id]['access_token']
        return None
    
    def get_all_access_tokens(self) -> List[tuple]:
        """Get all access tokens with their account info"""
        return [
            (account_id, account_data['access_token'], account_data['account_name'])
            for account_id, account_data in self.accounts.items()
        ]
    
    def update_last_sync(self, account_id: str):
        """Update last sync timestamp for an account"""
        if account_id in self.accounts:
            self.accounts[account_id]['last_sync'] = datetime.datetime.now().isoformat()
            self._save_accounts()
    
    def get_account_info(self, account_id: str) -> Optional[Dict]:
        """Get account information"""
        return self.accounts.get(account_id)
    
    def migrate_legacy_token(self) -> bool:
        """Migrate legacy single access token to new system"""
        legacy_file = '_access_token.json'
        if not os.path.exists(legacy_file):
            return False
        
        try:
            with open(legacy_file, 'r') as f:
                legacy_data = json.load(f)
            
            access_token = legacy_data.get('access_token')
            if not access_token:
                return False
            
            # Add as first account
            success = self.add_account(access_token, "Legacy Bank Account")
            
            if success:
                # Backup legacy file
                backup_file = f'_access_token_backup_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                os.rename(legacy_file, backup_file)
                print(f"[OK] Legacy token migrated. Backup saved as: {backup_file}")
                return True
            
        except Exception as e:
            print(f"[ERROR] Error migrating legacy token: {e}")
        
        return False
