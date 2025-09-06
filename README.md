# Finance Tracker with Google Sheets Integration

Automated finance tracking system that fetches bank transactions from Plaid API, categorizes them using business logic rules, and syncs directly to Google Sheets.

## 🚀 Features

- **Plaid Integration**: Secure bank account connection
- **Smart Categorization**: Automatic expense categorization for construction companies using business rules
- **Google Sheets Sync**: Direct integration with Google Sheets (no CSV files)
- **Token Persistence**: One-time setup, automatic reuse
- **Duplicate Prevention**: Only new transactions are added
- **Cron Ready**: Automated daily sync capability

## 📋 Quick Start

### 1. Setup Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with your credentials
cp .env.example .env
# Edit .env with your Plaid and Google credentials
```

### 2. Google Sheets Setup
```bash
# Validate your setup
python setup_google_sheets.py

# Download Google Service Account key as 'credentials.json'
# Share your Google Sheet with the service account email
```

### 3. Plaid Token Setup
```bash
# Create link token
python connect_api_bank.py

# Connect bank and get public token
# Exchange for access token
python get_token.py
```

### 4. Run Sync
```bash
# Manual sync
python finance_tracker_sheets.py

# Or use cron-friendly wrapper
python run_sync.py
```

## 📁 File Structure

### Core Files
- **`finance_tracker_sheets.py`** - Main script with Google Sheets integration
- **`run_sync.py`** - Cron-friendly wrapper with logging
- **`setup_google_sheets.py`** - Setup validation helper

### Legacy Files (CSV-based)
- **`finance_tracker_v3.py`** - Original CSV-based version
- **`connect_api_bank.py`** - Plaid link token creation
- **`get_token.py`** - Token exchange helper

### Configuration
- **`requirements.txt`** - Python dependencies
- **`SETUP_INSTRUCTIONS.md`** - Detailed setup guide

## 🏗️ Business Logic

The system automatically categorizes transactions for construction companies:

### Subcontractor Database
- All-Pro Plumbing → Plumbing
- J&L Electric → Electrical  
- Sal's Drywall → Drywall & Paint
- Creative Landscape → Landscaping
- And more...

### Vendor Categories
- Home Depot, Lowe's → Materials
- Sunbelt, United Rentals → Equipment Rental
- Chevron, Shell → Fuel

### Payment Methods
- QuickBooks → QuickBooks Bill Pay
- Zelle → Zelle Payment
- Check # → Subcontractor Payout

## 🔧 Configuration

### Environment Variables (.env)
```env
# Plaid Configuration
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PLAID_HOST=https://sandbox.plaid.com

# Google Sheets Configuration  
GOOGLE_SHEET_ID=your_google_sheet_id
```

### Google Sheets Setup
1. Create Google Cloud Project
2. Enable Google Sheets API
3. Create Service Account credentials
4. Download as `credentials.json`
5. Share your sheet with service account email

## 📊 Output Format

Transactions are saved to Google Sheets with columns:
- `transaction_id` - Unique Plaid transaction ID
- `date` - Transaction date
- `name` - Merchant/description
- `amount` - Transaction amount
- `category` - Auto-assigned category
- `project` - Project assignment (Bellevue, Admin, etc.)

## 🤖 Automation

### Daily Cron Job
```bash
# Add to crontab for daily 9 AM sync
0 9 * * * cd /path/to/finance && python run_sync.py
```

### Manual Execution
```bash
# Run anytime
python finance_tracker_sheets.py
```

## 🔒 Security

- Service Account authentication (no user login required)
- Access tokens stored locally with timestamps
- No sensitive data in code repository
- Google Sheets permissions managed via sharing

## 📈 Monitoring

- Daily log files in `logs/` directory
- Success/failure notifications
- Transaction count reporting
- Error handling and recovery
