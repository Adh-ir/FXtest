"""
Test script for the Audit & Reconciliation Module.
Tests with REAL API calls (testing_mode=False).
LIMITED SAMPLE to avoid burning too many API credits.
"""

import sys
import os
import importlib.util

# Direct file import to avoid triggering logic/__init__.py (which imports Streamlit)
auditor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logic', 'auditor.py')
spec = importlib.util.spec_from_file_location("auditor", auditor_path)
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)

process_audit_file = auditor.process_audit_file
clear_rate_cache = auditor.clear_rate_cache

import pandas as pd
from io import BytesIO

# Your Twelve Data API Key (from environment variable)
API_KEY = os.environ.get("TWELVE_DATA_API_KEY", "")


def test_live_api_limited():
    """Tests the auditor with REAL API calls on a 10-row sample."""
    print("=== LIVE API TEST (10 rows) ===")
    print("⚠️  This will make REAL API calls to Twelve Data.")
    print("⚠️  Estimated time: ~1-2 minutes (with batch delays).\n")
    
    # Clear cache to ensure fresh API calls
    clear_rate_cache()
    
    # Load full CSV and take first 10 rows
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dummy_data.csv')
    
    if not os.path.exists(csv_path):
        print(f"ERROR: File not found: {csv_path}")
        return
    
    df_full = pd.read_csv(csv_path)
    df_sample = df_full.head(20)  # Next 20 rows
    
    # Save sample to BytesIO to pass to auditor
    buffer = BytesIO()
    df_sample.to_csv(buffer, index=False)
    buffer.seek(0)
    buffer.name = "sample.csv"  # Important for file type detection
    
    print(f"Sample rows: {len(df_sample)}")
    print(f"Pairs being tested:")
    for _, row in df_sample.iterrows():
        print(f"  {row['Date']}: {row['Base Currency']}/{row['Source Currency']} = {row['rate']}")
    print("\nStarting audit...\n")
    
    # Use the generator to see progress
    gen = process_audit_file(
        file=buffer,
        date_fmt="YYYY-MM-DD",
        threshold=5.0,
        api_key=API_KEY,
        testing_mode=False  # <-- REAL API CALLS
    )
    
    result = None
    for update in gen:
        print(f"[{update['status'].upper()}] {update['message']}")
    
    # Get final result
    try:
        result = gen.send(None)
    except StopIteration as e:
        result = e.value
    
    if result:
        df, summary = result
        print("\n" + "="*50)
        print("=== FINAL RESULTS ===")
        print("="*50)
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
        print("\n=== Detailed Output ===")
        # Show all output
        if 'API Rate' in df.columns:
            print(df[['Base Currency', 'Source Currency', 'rate', 'API Rate', 'Variance %', 'Status']].to_string())


if __name__ == "__main__":
    test_live_api_limited()
