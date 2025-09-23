# Multiple Bank Accounts Guide

Your finance tracker now supports linking multiple bank accounts with **separate sheets for each bank**! Here's how to use the new functionality:

## Quick Start

### 1. First Time Setup
```bash
python setup.py
```
This will:
- Migrate your existing single account (if any) to the new system
- Allow you to link additional accounts
- Set up the updated Google Sheets schema

### 2. Link Additional Accounts
```bash
python setup.py
```
When you run setup again, it will detect existing accounts and ask if you want to add more.

### 3. Manage Accounts
```bash
python manage_accounts.py
```
This gives you a menu to:
- List all linked accounts
- Add new accounts
- Remove accounts
- Test connections
- Migrate legacy tokens

### 4. Sync All Accounts
```bash
python sync.py
```
Now syncs transactions from ALL linked accounts automatically.

## What's New

### Separate Sheets Per Bank
- **Each bank gets its own sheet** within the same Google Sheets document
- Sheet names are automatically generated from bank names (e.g., "Bank of America", "Chase Business")
- No more mixing transactions from different banks in one sheet

### Google Sheets Schema
Each bank's sheet has the same clean schema:
- `transaction_id` | `date` | `name` | `amount` | `category` | `project`

### Account Management
- Each bank account gets a unique ID, name, and dedicated sheet
- Sheets are automatically created when you link new accounts
- Last sync timestamps are tracked per account
- Legacy single-account setup is automatically migrated

### File Structure
- `_bank_accounts.json` - Stores all your linked accounts
- `_access_token_backup_*.json` - Backup of your old single token (if migrated)

## Examples

### Link Multiple Accounts
1. Run `python setup.py`
2. Enter a name like "Chase Business" or "Personal Checking"
3. Connect through Plaid Link
4. Repeat for additional accounts

### View All Accounts
```bash
python manage_accounts.py
# Choose option 1 to list all accounts
```

### Remove an Account
```bash
python manage_accounts.py
# Choose option 3 to remove an account
```

## Migration from Single Account

If you had a single account linked before:
1. Your existing `_access_token.json` will be automatically migrated
2. It becomes your first account in the new system
3. The old file is backed up with a timestamp
4. No data is lost

## Troubleshooting

### "No bank accounts found"
- Run `python setup.py` to link your first account
- Or run `python manage_accounts.py` and choose option 5 to migrate legacy token

### "Connection failed"
- Run `python manage_accounts.py` and choose option 4 to test all connections
- Re-link accounts if needed

### Google Sheets errors
- The schema is automatically updated when you run setup
- Make sure your service account has write access to the sheet

## Benefits

- **Organized by Bank**: Each bank has its own dedicated sheet for easy organization
- **Clean Separation**: No mixing of transactions from different banks
- **Automatic Sheet Creation**: Sheets are created automatically when you link new accounts
- **Flexible Management**: Add/remove accounts as needed
- **Backward Compatible**: Existing setup continues to work

## Sheet Organization

Your Google Sheets document now looks like this:
- **Sheet 1**: "Bank of America" - All Bank of America transactions
- **Sheet 2**: "Chase Business" - All Chase Business transactions  
- **Sheet 3**: "Wells Fargo Personal" - All Wells Fargo Personal transactions
- And so on...

Each sheet has the same clean format with headers and categorized transactions.
