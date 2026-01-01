import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import List, Optional
from .api_client import TwelveDataClient
from .data_processor import DataProcessor
from .config import CACHE_CONFIG

# Cache for configured duration
@st.cache_data(ttl=CACHE_CONFIG.RATE_TTL_SECONDS, show_spinner=False)
def _fetch_rates_cached(api_key: str, base_currencies: List[str], start_date: str, end_date: str, target_currencies: List[str] = None) -> pd.DataFrame:
    """
    Internal cached function for fetching Forex rates.
    Does NOT apply inversion - that is handled by the caller.
    """
    # 1. Setup
    client = TwelveDataClient(api_key)
    
    # 2. Generate Configuration
    pairs_config = DataProcessor.generate_pairs_config(base_currencies, target_currencies)
    
    # 3. Fetch Data
    fetch_results = []
    
    for config in pairs_config:
        api_symbol = config['api_symbol']
        data = client.fetch_time_series(api_symbol, start_date, end_date)
        
        if data:
            fetch_results.append({
                'config': config,
                'api_data': data
            })
            
    # 4. Process Data
    final_df = DataProcessor.process_results(fetch_results, start_date=start_date, end_date=end_date)
    
    return final_df


def get_rates(api_key: str, base_currencies: List[str], start_date: str, end_date: str, target_currencies: List[str] = None, invert: bool = False) -> pd.DataFrame:
    """
    Main entry point for fetching Forex rates.
    Handles caching, API interaction, and data processing.
    
    Args:
        api_key: The Twelve Data API Key.
        base_currencies: List of base currency codes (e.g. ['ZAR', 'USD']).
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).
        target_currencies: Optional list of target/source currencies.
        invert: If True, inverts rates and swaps Base/Source columns.
        
    Returns:
        pd.DataFrame: The processed DataFrame with columns [Currency Base, Currency Source, Date, Exchange Rate].
    """
    # Get cached base data
    final_df = _fetch_rates_cached(api_key, base_currencies, start_date, end_date, target_currencies)
    
    # Apply inversion OUTSIDE of cache to ensure it always runs
    if invert and not final_df.empty and 'Exchange Rate' in final_df.columns:
        # Make a copy to avoid modifying the cached DataFrame
        final_df = final_df.copy()
        
        final_df['Exchange Rate'] = 1 / final_df['Exchange Rate']
        final_df['Exchange Rate'] = final_df['Exchange Rate'].round(6)
        
        # Swap Base and Source columns to reflect the inverted rate
        if 'Currency Base' in final_df.columns and 'Currency Source' in final_df.columns:
            final_df.rename(columns={'Currency Base': 'Currency Source', 'Currency Source': 'Currency Base'}, inplace=True)
            # Reorder columns to standard format
            final_df = final_df[['Currency Base', 'Currency Source', 'Date', 'Exchange Rate']]
    
    return final_df

@st.cache_data(ttl=CACHE_CONFIG.CURRENCY_TTL_SECONDS, show_spinner=False)
def get_available_currencies(api_key: str, base_currency: str) -> List[str]:
    """
    Fetches all available forex pairs for a given base currency.
    Cached for configured duration (default: 24 hours).
    """
    client = TwelveDataClient(api_key)
    return client.fetch_available_pairs(base_currency)
