# Finance Tracker

Simple Python app that fetches bank transactions from Plaid and syncs them to Google Sheets.

## Quick Start

### 1. Setup (one time only)
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with your credentials
cp .env.example .env
# Edit .env with your Plaid and Google credentials

# Run setup
python setup.py
```

### 2. Sync transactions
```bash
# Manual sync
python sync.py

# Or automate with cron (daily at 9 AM)
0 9 * * * cd /path/to/finance && python sync.py
```

## Files

- **`setup.py`** - One-time setup (Plaid + Google Sheets)
- **`sync.py`** - Sync transactions to Google Sheets

## Configuration

### Environment Variables (.env)
```env
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PLAID_ENV=sandbox
GOOGLE_SHEET_ID=your_google_sheet_id
```

### Google Sheets Setup
1. Go to https://console.cloud.google.com/
2. Create project and enable Google Sheets API
3. Create Service Account credentials
4. Download as `credentials.json`
5. Share your Google Sheet with the service account email

## Output

Transactions are saved to Google Sheets with columns:
- `transaction_id` - Unique Plaid transaction ID
- `date` - Transaction date
- `name` - Merchant/description
- `amount` - Transaction amount
- `category` - Auto-assigned category
- `project` - Project assignment

## Business Logic

Auto-categorizes transactions for construction companies:

### Subcontractors
- All-Pro Plumbing → Plumbing
- J&L Electric → Electrical
- Sal's Drywall → Drywall & Paint
- And more...

### Vendors
- Home Depot, Lowe's → Materials
- Sunbelt, United Rentals → Equipment Rental
- Chevron, Shell → Fuel

### Payment Methods
- QuickBooks → QuickBooks Bill Pay
- Zelle → Zelle Payment
- Check # → Subcontractor Payout

## That's it!

Just 2 commands:
1. `python setup.py` (once)
2. `python sync.py` (whenever you want to sync)