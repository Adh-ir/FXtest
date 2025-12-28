"""
Audit & Reconciliation Module

Processes user-uploaded Excel files, fetches official rates from Twelve Data API,
and compares them to user-provided rates.

CRITICAL: Designed to survive strict API Rate Limits (Twelve Data Free Tier = ~8 requests/minute).
"""

import time
import random
import re
import logging
import pandas as pd
from typing import Generator, Dict, Any, Tuple, Optional
from datetime import datetime

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# --- Column Name Mappings (Flexible Schema Support) ---
# Maps various possible column names to our internal standard names
COLUMN_MAPPINGS = {
    'date': ['Date', 'date', 'DATE', 'Transaction Date', 'Trade Date'],
    'base': ['Base', 'base', 'BASE', 'Base Currency', 'base_currency', 'From', 'from'],
    'source': ['Source', 'source', 'SOURCE', 'Source Currency', 'source_currency', 'To', 'to', 'Target'],
    'user_rate': ['User Rate', 'user_rate', 'Rate', 'rate', 'Exchange Rate', 'exchange_rate', 'FX Rate']
}


def validate_schema(df: pd.DataFrame) -> Tuple[bool, Dict[str, str], str]:
    """
    Validates the DataFrame schema and maps columns to standard names.
    
    Args:
        df: The input DataFrame to validate.
        
    Returns:
        Tuple of (is_valid, column_mapping, error_message)
        - is_valid: True if all required columns are found
        - column_mapping: Dict mapping internal names to actual column names
        - error_message: Empty string if valid, otherwise describes missing columns
    """
    found_mapping = {}
    missing_fields = []
    
    for internal_name, possible_names in COLUMN_MAPPINGS.items():
        matched = None
        for name in possible_names:
            if name in df.columns:
                matched = name
                break
        
        if matched:
            found_mapping[internal_name] = matched
        else:
            missing_fields.append(internal_name)
    
    if missing_fields:
        error_msg = f"Missing required columns. Expected one of each: {', '.join([f'{k}: {COLUMN_MAPPINGS[k]}' for k in missing_fields])}"
        return False, {}, error_msg
    
    return True, found_mapping, ""


# --- Rate Cache (Simple In-Memory) ---
# Key: (date_str, base, source) -> Value: rate
# This prevents redundant API calls for the same date/pair combination.
_rate_cache: Dict[Tuple[str, str, str], float] = {}


def _get_cached_rate(date_str: str, base: str, source: str) -> Optional[float]:
    """Check if rate is already in cache."""
    key = (date_str, base.upper(), source.upper())
    return _rate_cache.get(key)


def _set_cached_rate(date_str: str, base: str, source: str, rate: float):
    """Store rate in cache."""
    key = (date_str, base.upper(), source.upper())
    _rate_cache[key] = rate


def _fetch_rate_from_api(api_key: str, base: str, source: str, date_str: str) -> Optional[float]:
    """
    Fetches a single historical rate from Twelve Data API.
    Uses the time_series endpoint with outputsize=1 for efficiency.
    """
    import requests
    
    url = "https://api.twelvedata.com/time_series"
    params = {
        "apikey": api_key,
        "symbol": f"{base}/{source}",
        "interval": "1day",
        "start_date": date_str,
        "outputsize": 1  # Get closest candle
    }
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        
        if 'values' in data and len(data['values']) > 0:
            rate = float(data['values'][0]['close'])
            return rate
        elif data.get('code') == 429:
            logger.warning("API 429 Rate Limit hit during fetch.")
            return None
        else:
            logger.warning(f"API returned no data for {base}/{source} on {date_str}: {data.get('message', 'Unknown')}")
            return None
            
    except Exception as e:
        logger.error(f"API request failed: {e}")
        return None


def _generate_mock_rate(base: str, source: str, user_rate: float) -> float:
    """
    Generates a mock rate for testing mode.
    Returns a rate with a small random variance from user_rate to simulate real API data.
    """
    # Variance between -5% and +5%
    variance_pct = random.uniform(-0.05, 0.05)
    mock_rate = user_rate * (1 + variance_pct)
    return round(mock_rate, 6)


def _parse_date(date_value: Any, date_fmt: str) -> Optional[str]:
    """
    Parses a date value from Excel into a standardized YYYY-MM-DD string.
    Handles both string dates and datetime objects.
    """
    # Common format mapping
    fmt_map = {
        "YYYY-MM-DD": "%Y-%m-%d",
        "DD/MM/YYYY": "%d/%m/%Y",
        "MM/DD/YYYY": "%m/%d/%Y",
        "DD-MM-YYYY": "%d-%m-%Y",
        "YYYY/MM/DD": "%Y/%m/%d",
    }
    
    python_fmt = fmt_map.get(date_fmt, "%Y-%m-%d")
    
    try:
        if isinstance(date_value, datetime):
            return date_value.strftime("%Y-%m-%d")
        elif isinstance(date_value, str):
            dt = datetime.strptime(date_value.strip(), python_fmt)
            return dt.strftime("%Y-%m-%d")
        else:
            # Try to convert via pandas
            dt = pd.to_datetime(date_value)
            return dt.strftime("%Y-%m-%d")
    except Exception as e:
        logger.warning(f"Date parse error for '{date_value}': {e}")
        return None


def process_audit_file(
    file,
    date_fmt: str = "YYYY-MM-DD",
    threshold: float = 5.0,
    api_key: str = "",
    testing_mode: bool = True  # DEFAULT TRUE to protect API credits
) -> Generator[Dict[str, Any], None, Tuple[pd.DataFrame, Dict[str, Any]]]:
    """
    Processes a user-uploaded Excel/CSV file for audit and reconciliation.
    
    YIELDS progress updates for UI feedback, then RETURNS final results.
    
    Args:
        file: File-like object or path to Excel/CSV file.
        date_fmt: The date format in the file (e.g., "YYYY-MM-DD", "DD/MM/YYYY").
        threshold: Variance percentage threshold for PASS/EXCEPTION (default 5%).
        api_key: Twelve Data API key (required if testing_mode=False).
        testing_mode: If True, uses mock rates instead of real API calls.
        
    Yields:
        Dict with progress info: {"current": int, "total": int, "message": str, "status": str}
        
    Returns:
        Tuple of (processed_dataframe, summary_dict)
    """
    
    # --- 1. Load File ---
    yield {"current": 0, "total": 0, "message": "Loading file...", "status": "loading"}
    
    try:
        # Determine file type from file object name or string path
        file_path = ""
        if hasattr(file, 'name'):
            file_path = file.name
        elif isinstance(file, str):
            file_path = file
            
        if file_path.lower().endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
    except Exception as e:
        yield {"current": 0, "total": 0, "message": f"Error loading file: {e}", "status": "error"}
        return pd.DataFrame(), {"total_rows": 0, "exceptions": 0, "passed": 0, "api_errors": 0, "error": str(e)}
    
    # --- 2. Validate Schema with Flexible Column Mapping ---
    is_valid, col_map, error_msg = validate_schema(df)
    
    if not is_valid:
        yield {"current": 0, "total": 0, "message": error_msg, "status": "error"}
        return pd.DataFrame(), {"total_rows": 0, "exceptions": 0, "passed": 0, "api_errors": 0, "error": error_msg}
    
    # Log the detected schema
    schema_info = ", ".join([f"{k}='{v}'" for k, v in col_map.items()])
    yield {"current": 0, "total": 0, "message": f"Schema validated. Columns: {schema_info}", "status": "loading"}
    
    total_rows = len(df)
    yield {"current": 0, "total": total_rows, "message": f"Loaded {total_rows} rows. Starting audit...", "status": "processing"}
    
    # --- 3. Prepare Output Columns ---
    df['API Rate'] = None
    df['Variance %'] = None
    df['Status'] = None
    
    # --- 4. Process Rows with Smart Throttling ---
    BATCH_SIZE = 5
    BATCH_SLEEP = 65  # seconds
    
    passed = 0
    exceptions = 0
    api_errors = 0
    
    for idx, row in df.iterrows():
        row_num = idx + 1
        
        # Parse date using mapped column name
        date_str = _parse_date(row[col_map['date']], date_fmt)
        if not date_str:
            df.at[idx, 'Status'] = 'DATE_ERROR'
            api_errors += 1
            yield {
                "current": row_num,
                "total": total_rows,
                "message": f"Row {row_num}: Invalid date format",
                "status": "processing"
            }
            continue
        
        base = str(row[col_map['base']]).strip().upper()
        source = str(row[col_map['source']]).strip().upper()
        user_rate = float(row[col_map['user_rate']])
        
        # --- Check Cache First ---
        api_rate = _get_cached_rate(date_str, base, source)
        cache_hit = api_rate is not None
        
        if not cache_hit:
            if testing_mode:
                # Generate mock rate
                api_rate = _generate_mock_rate(base, source, user_rate)
                yield {
                    "current": row_num,
                    "total": total_rows,
                    "message": f"Row {row_num}: [MOCK] {base}/{source} = {api_rate:.6f}",
                    "status": "processing"
                }
            else:
                # Real API call with throttling
                # Check if we need to pause for rate limit
                if row_num > 1 and (row_num - 1) % BATCH_SIZE == 0:
                    yield {
                        "current": row_num,
                        "total": total_rows,
                        "message": f"Pausing {BATCH_SLEEP}s for API rate limit... (Batch {(row_num-1)//BATCH_SIZE} complete)",
                        "status": "waiting"
                    }
                    time.sleep(BATCH_SLEEP)
                
                api_rate = _fetch_rate_from_api(api_key, base, source, date_str)
                
                if api_rate is None:
                    df.at[idx, 'Status'] = 'API_ERROR'
                    api_errors += 1
                    yield {
                        "current": row_num,
                        "total": total_rows,
                        "message": f"Row {row_num}: API error for {base}/{source}",
                        "status": "processing"
                    }
                    continue
                
                yield {
                    "current": row_num,
                    "total": total_rows,
                    "message": f"Row {row_num}: Fetched {base}/{source} = {api_rate:.6f}",
                    "status": "processing"
                }
            
            # Cache the rate
            _set_cached_rate(date_str, base, source, api_rate)
        else:
            yield {
                "current": row_num,
                "total": total_rows,
                "message": f"Row {row_num}: [CACHE] {base}/{source} = {api_rate:.6f}",
                "status": "processing"
            }
        
        # --- Calculate Variance ---
        if api_rate and api_rate != 0:
            variance = abs((user_rate - api_rate) / api_rate) * 100
            df.at[idx, 'API Rate'] = round(api_rate, 6)
            df.at[idx, 'Variance %'] = round(variance, 2)
            
            if variance <= threshold:
                df.at[idx, 'Status'] = 'PASS'
                passed += 1
            else:
                df.at[idx, 'Status'] = 'EXCEPTION'
                exceptions += 1
    
    # --- 5. Final Summary ---
    summary = {
        "total_rows": total_rows,
        "passed": passed,
        "exceptions": exceptions,
        "api_errors": api_errors,
        "testing_mode": testing_mode
    }
    
    yield {
        "current": total_rows,
        "total": total_rows,
        "message": f"Audit complete. Passed: {passed}, Exceptions: {exceptions}, Errors: {api_errors}",
        "status": "complete"
    }
    
    return df, summary


def clear_rate_cache():
    """Clears the in-memory rate cache."""
    global _rate_cache
    _rate_cache = {}
    logger.info("Rate cache cleared.")


# --- Convenience Function for Non-Generator Use ---
def run_audit(
    file,
    date_fmt: str = "YYYY-MM-DD",
    threshold: float = 5.0,
    api_key: str = "",
    testing_mode: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Runs the audit without yielding progress (for simple scripts).
    Returns (dataframe, summary).
    """
    gen = process_audit_file(file, date_fmt, threshold, api_key, testing_mode)
    
    result = None
    for update in gen:
        logger.info(update['message'])
        if update['status'] == 'complete':
            # The generator returns after the final yield
            pass
    
    # Get the return value
    try:
        result = gen.send(None)
    except StopIteration as e:
        result = e.value
    
    return result if result else (pd.DataFrame(), {})
