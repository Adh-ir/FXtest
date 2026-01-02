"""
Facade Module

High-level API for fetching Forex rates. Provides caching and abstraction
over the TwelveDataClient and DataProcessor.

NOTE: This module is framework-agnostic. Caching uses a pluggable backend
(Redis or in-memory) for horizontal scaling support. The cache backend is
auto-detected: Redis if available, otherwise in-memory fallback.
"""

import pandas as pd

from .api_client import TwelveDataClient
from .cache import get_cache_backend
from .config import CACHE_CONFIG
from .data_processor import DataProcessor


def _create_cache_key(
    api_key: str,
    base_currencies: list[str],
    start_date: str,
    end_date: str,
    target_currencies: list[str] | None,
) -> str:
    """Creates a cache key string from the request parameters."""
    base_key = ",".join(sorted(base_currencies))
    target_key = ",".join(sorted(target_currencies)) if target_currencies else "ALL"
    # Note: We hash the api_key to avoid storing it in cache keys
    api_hash = hash(api_key) % 100000
    return f"rates:{api_hash}:{base_key}:{target_key}:{start_date}:{end_date}"


def _create_currency_cache_key(api_key: str, base_currency: str) -> str:
    """Creates a cache key for currency pair lookups."""
    api_hash = hash(api_key) % 100000
    return f"currencies:{api_hash}:{base_currency.upper()}"


def _fetch_rates_internal(
    api_key: str,
    base_currencies: list[str],
    start_date: str,
    end_date: str,
    target_currencies: list[str] = None,
) -> pd.DataFrame:
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
        api_symbol = config["api_symbol"]
        data = client.fetch_time_series(api_symbol, start_date, end_date)

        if data:
            fetch_results.append({"config": config, "api_data": data})

    # 4. Process Data
    final_df = DataProcessor.process_results(fetch_results, start_date=start_date, end_date=end_date)

    return final_df


def get_rates(
    api_key: str,
    base_currencies: list[str],
    start_date: str,
    end_date: str,
    target_currencies: list[str] = None,
    invert: bool = False,
) -> pd.DataFrame:
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
        pd.DataFrame with columns [Currency Base, Currency Source, Date, Exchange Rate].
    """
    cache = get_cache_backend()
    cache_key = _create_cache_key(api_key, base_currencies, start_date, end_date, target_currencies)

    # Check cache
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        # Convert back from dict to DataFrame (for Redis JSON serialization)
        if isinstance(cached_data, dict):
            final_df = pd.DataFrame(cached_data)
        else:
            final_df = cached_data.copy()
    else:
        # Fetch fresh data
        final_df = _fetch_rates_internal(api_key, base_currencies, start_date, end_date, target_currencies)
        # Store in cache (convert to dict for JSON serialization)
        cache.set(
            cache_key,
            final_df.to_dict() if not final_df.empty else {},
            ttl_seconds=CACHE_CONFIG.RATE_TTL_SECONDS,
        )

    # Apply inversion OUTSIDE of cache to ensure it always runs
    if invert and not final_df.empty and "Exchange Rate" in final_df.columns:
        # Make a copy to avoid modifying the cached DataFrame
        final_df = final_df.copy()

        final_df["Exchange Rate"] = 1 / final_df["Exchange Rate"]
        final_df["Exchange Rate"] = final_df["Exchange Rate"].round(6)

        # Swap Base and Source columns to reflect the inverted rate
        if "Currency Base" in final_df.columns and "Currency Source" in final_df.columns:
            final_df.rename(
                columns={
                    "Currency Base": "Currency Source",
                    "Currency Source": "Currency Base",
                },
                inplace=True,
            )
            # Reorder columns to standard format
            final_df = final_df[["Currency Base", "Currency Source", "Date", "Exchange Rate"]]

    return final_df


def get_available_currencies(api_key: str, base_currency: str) -> list[str]:
    """
    Fetches all available forex pairs for a given base currency.
    Cached for configured duration (default: 24 hours).
    """
    cache = get_cache_backend()
    cache_key = _create_currency_cache_key(api_key, base_currency)

    # Check cache
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    # Fetch fresh data
    client = TwelveDataClient(api_key)
    currencies = client.fetch_available_pairs(base_currency)

    # Store in cache
    cache.set(cache_key, currencies, ttl_seconds=CACHE_CONFIG.CURRENCY_TTL_SECONDS)

    return currencies


def clear_facade_cache() -> None:
    """Clears all facade caches. Useful for testing."""
    cache = get_cache_backend()
    cache.clear()
