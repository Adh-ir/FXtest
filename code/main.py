import sys
import argparse
from core.config_manager import ConfigManager
from core.api_fetcher import APIFetcher
from core.data_serializer import DataSerializer

import os
from datetime import datetime, timedelta

# Constants
DEFAULT_API_KEY = ""
API_KEY_FILE = ".api_key"

def load_api_key():
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r") as f:
            return f.read().strip()
    return None

def save_api_key(key):
    with open(API_KEY_FILE, "w") as f:
        f.write(key)


def run_agent(base_currencies_str, api_key, start_date=None, end_date=None):
    print(f"--- Rate Harvester Agent Starting ---")
    print(f"Base Currencies: {base_currencies_str}")
    
    # 1. Configuration
    print("\n[Core] Generating Configuration...")
    bases = ConfigManager.parse_input(base_currencies_str)
    pairs_config = ConfigManager.generate_pairs(bases)
    print(f"Generated {len(pairs_config)} currency pair requests.")
    for p in pairs_config:
        print(f"  - {p['user_base']}->{p['user_target']} via {p['api_symbol']} ({p.get('calculation_mode', 'direct')})")

    # 2. Fetching
    print("\n[Core] Fetching Rates...")
    fetcher = APIFetcher(api_key)
    # Pass date range if provided
    results = fetcher.fetch_rates(pairs_config, start_date=start_date, end_date=end_date)
    print(f"Fetched {len(results)} responses.")

    # 3. Serializing
    print("\n[Core] Serializing Data...")
    serializer = DataSerializer()
    serializer.serialize(results, output_dir=".")
    print("\n--- Process Completed ---")

def run_acceptance_tests(api_key):
    print("\n=== RUNNING ACCEPTANCE TESTS ===\n")
    
    # Test Case 1: Africa Audit
    # Base ZAR -> Targets USD, BWP, MWK (and others in basket)
    print(">>> Test Case 1: The 'Africa Audit' Basket (Base: ZAR)")
    run_agent("ZAR", api_key)
    
    # Test Case 2: Major Check
    # Base USD -> Target EUR
    print("\n>>> Test Case 2: The 'Major' Check (Base: USD)")
    run_agent("USD", api_key)
    
    # Test Case 3: Rate Limit Resilience
    # Input ZAR, USD. Total ~10 pairs.
    print("\n>>> Test Case 3: Rate Limit Resilience (Base: ZAR, USD)")
    # Note: This will re-run ZAR and USD logic, proving the throttling.
    run_agent("ZAR, USD", api_key)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forex Rate Harvester")
    parser.add_argument("--bases", type=str, help="Comma-separated base currencies (e.g. 'ZAR,USD')")
    parser.add_argument("--test", action="store_true", help="Run acceptance tests")
    parser.add_argument("--apikey", type=str, default=DEFAULT_API_KEY, help="Twelve Data API Key")
    
    args = parser.parse_args()
    
    # 1. Determine API Key
    api_key = args.apikey
    if api_key == DEFAULT_API_KEY:
        # Check if saved locally
        saved_key = load_api_key()
        if saved_key:
            api_key = saved_key
            print(f"Loaded API Key from {API_KEY_FILE}")
    
    if args.test:
        run_acceptance_tests(api_key)
    elif args.bases:
        run_agent(args.bases, api_key)
    else:
        # Default behavior: Prompt user or run help
        print("No arguments provided. Running interaction mode.")
        
        # KEY PROMPT
        if api_key == DEFAULT_API_KEY: # Still default, meant wasn't in args or file
             user_key = input(f"Enter Twelve Data API Key: ")
             if user_key.strip():
                 api_key = user_key.strip()
                 save_api_key(api_key)
                 print("API Key saved.")

        # PAIRS PROMPT
        user_input = input("Enter base currencies (e.g., ZAR, USD): ")
        
        # DATE PROMPT
        end_date_str = input("Enter End Date (YYYY-MM-DD) [Default: Today]: ").strip()
        if not end_date_str:
            end_date = datetime.now()
        else:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            except ValueError:
                print("Invalid date format. Using Today.")
                end_date = datetime.now()
        
        # Calculate Start Date (365 days ago)
        start_date = end_date - timedelta(days=365)
        
        # Convert to string for API consistency if needed, but fetcher might handle datetime objects.
        # Let's pass formatted strings to be safe for API fetcher.
        s_date_str = start_date.strftime("%Y-%m-%d")
        e_date_str = end_date.strftime("%Y-%m-%d")

        print(f"Fetching data from {s_date_str} to {e_date_str}...")
        
        if user_input:
            run_agent(user_input, api_key, start_date=s_date_str, end_date=e_date_str)

