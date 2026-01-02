"""
Facade Module

High-level API for fetching Forex rates. Provides caching and abstraction
over the TwelveDataClient and DataProcessor.

NOTE: This module is framework-agnostic. Caching uses functools.lru_cache
for portability. When used within Streamlit, the app.py layer can add
additional st.cache_data decorators if needed.
"""

import pandas as pd
from functools import lru_cache
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from .api_client import TwelveDataClient
from .data_processor import DataProcessor
from .config import CACHE_CONFIG


def _create_cache_key(api_key: str, base_currencies: List[str], start_date: str, 
                      end_date: str, target_currencies: Optional[List[str]]) -> Tuple:
    """Creates a hashable cache key from the request parameters."""
    return (
        api_key,
        tuple(sorted(base_currencies)),
        start_date,
        end_date,
        tuple(sorted(target_currencies)) if target_currencies else None
    )


# In-memory cache for rate data
_rates_cache: dict = {}
_rates_cache_timestamps: dict = {}

# In-memory cache for currency pairs
_currencies_cache: dict = {}
_currencies_cache_timestamps: dict = {}


def _is_cache_valid(cache_timestamps: dict, key: Tuple, ttl_seconds: int) -> bool:
    """Check if a cache entry is still valid based on TTL."""
    if key not in cache_timestamps:
        return False
    cache_time = cache_timestamps[key]
    return (datetime.now() - cache_time).total_seconds() < ttl_seconds


def _fetch_rates_internal(api_key: str, base_currencies: List[str], start_date: str, 
                          end_date: str, target_currencies: List[str] = None) -> pd.DataFrame:
    """
    Internal function for fetching Forex rates.
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


def get_rates(api_key: str, base_currencies: List[str], start_date: str, end_date: str, 
              target_currencies: List[str] = None, invert: bool = False) -> pd.DataFrame:
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
    # Create cache key
    cache_key = _create_cache_key(api_key, base_currencies, start_date, end_date, target_currencies)
    
    # Check cache
    if _is_cache_valid(_rates_cache_timestamps, cache_key, CACHE_CONFIG.RATE_TTL_SECONDS):
        final_df = _rates_cache[cache_key].copy()
    else:
        # Fetch fresh data
        final_df = _fetch_rates_internal(api_key, base_currencies, start_date, end_date, target_currencies)
        # Update cache
        _rates_cache[cache_key] = final_df.copy()
        _rates_cache_timestamps[cache_key] = datetime.now()
    
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


def get_available_currencies(api_key: str, base_currency: str) -> List[str]:
    """
    Fetches all available forex pairs for a given base currency.
    Cached for configured duration (default: 24 hours).
    """
    cache_key = (api_key, base_currency.upper())
    
    # Check cache
    if _is_cache_valid(_currencies_cache_timestamps, cache_key, CACHE_CONFIG.CURRENCY_TTL_SECONDS):
        return _currencies_cache[cache_key]
    
    # Fetch fresh data
    client = TwelveDataClient(api_key)
    currencies = client.fetch_available_pairs(base_currency)
    
    # Update cache
    _currencies_cache[cache_key] = currencies
    _currencies_cache_timestamps[cache_key] = datetime.now()
    
    return currencies


def clear_facade_cache() -> None:
    """Clears all facade caches. Useful for testing."""
    global _rates_cache, _rates_cache_timestamps, _currencies_cache, _currencies_cache_timestamps
    _rates_cache = {}
    _rates_cache_timestamps = {}
    _currencies_cache = {}
    _currencies_cache_timestamps = {}
