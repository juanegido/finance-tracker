# Finance Tracker with Google Sheets Setup

## Prerequisites

1. **Plaid Account**: You need Plaid API credentials
2. **Google Cloud Project**: With Google Sheets API enabled
3. **Google Sheet**: Target spreadsheet for transaction data

## Setup Steps

### 1. Environment Variables

Create a `.env` file in the project root with:

```env
# Plaid Configuration
PLAID_CLIENT_ID=your_plaid_client_id_here
PLAID_SECRET=your_plaid_secret_here
PLAID_HOST=https://sandbox.plaid.com
PLAID_ENV=sandbox

# Google Sheets Configuration
GOOGLE_SHEET_ID=your_google_sheet_id_here
```

**To get Google Sheet ID**: Copy from URL `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`

### 2. Google Sheets API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Sheets API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Choose "Desktop application"
6. Download the JSON file and save as `credentials.json` in project root

### 3. Plaid Token Setup

1. Run `python connect_api_bank.py` to create link token
2. Use the generated HTML file to connect your bank (or use sandbox credentials)
3. Run `python get_token.py` to exchange public token for access token

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run Setup Check

```bash
python setup_google_sheets.py
```

### 6. Run Finance Tracker

```bash
python finance_tracker_sheets.py
```

## Features

- **Token Persistence**: Plaid access token stored and reused
- **Google Sheets Output**: Transactions written directly to your sheet
- **Smart Categorization**: Same logic as v3 with vendor/project matching
- **Duplicate Prevention**: Only new transactions are added
- **Cron Ready**: Can be run manually or scheduled

## File Structure

- `finance_tracker_sheets.py` - Main script with Google Sheets integration
- `setup_google_sheets.py` - Setup validation helper
- `_access_token.json` - Persistent Plaid access token
- `credentials.json` - Google OAuth credentials (download from GCP)
- `token.json` - Google OAuth token (created on first run)

## Cron Setup Example

```bash
# Run every day at 9 AM
0 9 * * * cd /path/to/finance && python finance_tracker_sheets.py
```
