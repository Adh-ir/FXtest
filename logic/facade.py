import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import List, Optional
from .api_client import TwelveDataClient
from .data_processor import DataProcessor
from .config import CACHE_CONFIG

# Cache for configured duration
@st.cache_data(ttl=CACHE_CONFIG.RATE_TTL_SECONDS, show_spinner=False)
def get_rates(api_key: str, base_currencies: List[str], start_date: str, end_date: str, target_currencies: List[str] = None) -> pd.DataFrame:
    """
    Main entry point for fetching Forex rates.
    Handles caching, API interaction, and data processing.
    
    Args:
        api_key: The Twelve Data API Key.
        base_currencies: List of base currency codes (e.g. ['ZAR', 'USD']).
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).
        target_currencies: Optional list of target/source currencies.
        
    Returns:
        pd.DataFrame: The processed DataFrame with columns [Currency Base, Currency Source, Date, Exchange Rate].
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
    final_df = DataProcessor.process_results(fetch_results)
    
    return final_df

@st.cache_data(ttl=CACHE_CONFIG.CURRENCY_TTL_SECONDS, show_spinner=False)
def get_available_currencies(api_key: str, base_currency: str) -> List[str]:
    """
    Fetches all available forex pairs for a given base currency.
    Cached for configured duration (default: 24 hours).
    """
    client = TwelveDataClient(api_key)
    return client.fetch_available_pairs(base_currency)
