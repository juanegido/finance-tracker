import json
import datetime
from connect_api_bank import exchange_public_token, save_access_token

def main():
    print("=== Token Exchange Helper ===")
    print("Enter the public token you got from Plaid Link:")
    public_token = input("Public token: ").strip()
    
    if not public_token:
        print("No token provided")
        return
    
    print("Exchanging public token for access token...")
    access_token = exchange_public_token(public_token)
    
    if access_token:
        save_access_token(access_token)
        print("✅ Access token saved successfully!")
        print("You can now run finance_tracker_v3.py")
    else:
        print("❌ Failed to exchange token")

if __name__ == "__main__":
    main()
