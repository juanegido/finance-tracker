# Finance Tracker

Simple finance tracking using Plaid API to fetch bank transactions and categorize them.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get access token:**
   ```bash
   python connect_api_bank.py
   ```
   This creates `plaid_link.html` - open it in your browser

3. **Connect your bank:**
   - Open `plaid_link.html` in browser
   - Click "Connect Bank" 
   - Use sandbox credentials: `user_good` / `pass_good`
   - Copy the public token that appears

4. **Exchange token:**
   ```bash
   python get_token.py
   ```
   Paste the public token when prompted

5. **Run finance tracker:**
   ```bash
   python finance_tracker_v3.py
   ```

## Files

- `connect_api_bank.py` - Creates Plaid link token and HTML interface
- `get_token.py` - Helper to exchange public token for access token  
- `finance_tracker_v3.py` - Main script that fetches and categorizes transactions
- `transactions.csv` - Output file with categorized transactions
- `access_token.json` - Stored access token (created after step 4)

## How it works

1. First script gets Plaid access token by connecting to your bank
2. Second script uses that token to fetch transactions from last 60 days
3. Transactions are automatically categorized based on business rules
4. Results saved to CSV file with columns: transaction_id, date, name, amount, category, project
