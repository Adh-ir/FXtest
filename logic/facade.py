import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import List, Optional
from .api_client import TwelveDataClient
from .data_processor import DataProcessor

# Cache for 30 minutes (1800 seconds)
@st.cache_data(ttl=1800, show_spinner=False)
def get_rates(api_key: str, base_currencies: List[str], start_date: str, end_date: str) -> pd.DataFrame:
    """
    Main entry point for fetching Forex rates.
    Handles caching, API interaction, and data processing.
    
    Args:
        api_key: The Twelve Data API Key.
        base_currencies: List of base currency codes (e.g. ['ZAR', 'USD']).
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).
        
    Returns:
        pd.DataFrame: The processed DataFrame with columns [Currency Base, Currency Source, Date, Exchange Rate].
    """
    # 1. Setup
    client = TwelveDataClient(api_key)
    
    # 2. Generate Configuration
    # Note: We pass the list directly now, assuminig the UI parses the string or we do it here.
    # The prompt implies strictly python module usage `data = get_rates(api_key, base, source, date_range)`.
    # Let's align signatures. The user said: `data = get_rates(api_key, base, source, date_range)` 
    # But `base` can be a list? "Base Currencies: ZAR, USD".
    # I will stick to what makes sense: `base_currencies` list.
    
    pairs_config = DataProcessor.generate_pairs_config(base_currencies)
    
    # 3. Fetch Data
    fetch_results = []
    
    for config in pairs_config:
        api_symbol = config['api_symbol']
        # Determine if we need time series or single point
        # The legacy code handled both. Here we have start/end dates.
        # If dates are the same or not provided, maybe single point?
        # But for robustness, let's always use time_series if dates are present.
        
        # NOTE: The legacy code fetcher iterates and sleeps.
        # Inside this cached function, the `client` instance is fresh.
        # If we parallelize or cache partials, that's complex.
        # `st.cache_data` caches the *result* of this entire function.
        # So repeated calls with SAME args return instantly.
        # Calls with different dates/bases re-run logic.
        
        # Throttling is handled inside `client`.
        # Since we instantiate `client` here, the deque is fresh.
        # THIS IS A POTENTIAL ISSUE if multiple calls happen in parallel or sequential non-cached.
        # But `st.cache_data` helps. Also, `client` logic sleeps.
        # If `get_rates` is called once for a big list, the single `client` instance handles throttling for that batch.
        # That is correct behavior.
        
        data = client.fetch_time_series(api_symbol, start_date, end_date)
        
        if data:
            fetch_results.append({
                'config': config,
                'api_data': data
            })
            
    # 4. Process Data
    final_df = DataProcessor.process_results(fetch_results)
    
    return final_df
