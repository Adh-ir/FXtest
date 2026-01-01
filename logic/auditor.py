"""
Audit & Reconciliation Module

Processes user-uploaded Excel files, fetches official rates from Twelve Data API,
and compares them to user-provided rates.

CRITICAL: Designed to survive strict API Rate Limits (Twelve Data Free Tier = ~8 requests/minute).
"""

import time
import random
import logging
import pandas as pd
import requests
from typing import Generator, Dict, Any, Tuple, Optional
from datetime import datetime

from .config import API_CONFIG, AUDIT_CONFIG

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# --- Column Name Mappings (Flexible Schema Support) ---
COLUMN_MAPPINGS = {
    'date': ['Date', 'date', 'DATE', 'Transaction Date', 'Trade Date'],
    'base': ['Base', 'base', 'BASE', 'Base Currency', 'base_currency', 'From', 'from'],
    'source': ['Source', 'source', 'SOURCE', 'Source Currency', 'source_currency', 'To', 'to', 'Target'],
    'user_rate': ['User Rate', 'user_rate', 'Rate', 'rate', 'Exchange Rate', 'exchange_rate', 'FX Rate']
}


def validate_schema(df: pd.DataFrame) -> Tuple[bool, Dict[str, str], str]:
    """
    Validates the DataFrame schema and maps columns to standard names.
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
    """
    url = f"{API_CONFIG.BASE_URL}/time_series"
    params = {
        "apikey": api_key,
        "symbol": f"{base}/{source}",
        "interval": "1day",
        "start_date": date_str,
        "outputsize": 1
    }
    
    try:
        resp = requests.get(url, params=params, timeout=API_CONFIG.REQUEST_TIMEOUT_SECONDS)
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
    """
    # Variance between -5% and +5%
    variance_pct = random.uniform(-0.05, 0.05)
    mock_rate = user_rate * (1 + variance_pct)
    return round(mock_rate, 6)


def _parse_date(date_value: Any, date_fmt: str) -> Optional[str]:
    """
    Parses a date value from Excel into a standardized YYYY-MM-DD string.
    """
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
    testing_mode: bool = True
) -> Generator[Dict[str, Any], None, Tuple[pd.DataFrame, Dict[str, Any]]]:
    """
    Processes a user-uploaded Excel/CSV file for audit and reconciliation.
    
    YIELDS progress updates for UI feedback, then RETURNS final results.
    """
    
    # --- 1. Load File ---
    yield {"current": 0, "total": 0, "message": "Loading file...", "status": "loading"}
    
    try:
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
    
    # --- 2. Validate Schema ---
    is_valid, col_map, error_msg = validate_schema(df)
    
    if not is_valid:
        yield {"current": 0, "total": 0, "message": error_msg, "status": "error"}
        return pd.DataFrame(), {"total_rows": 0, "exceptions": 0, "passed": 0, "api_errors": 0, "error": error_msg}
    
    schema_info = ", ".join([f"{k}='{v}'" for k, v in col_map.items()])
    yield {"current": 0, "total": 0, "message": f"Schema validated. Columns: {schema_info}", "status": "loading"}
    
    total_rows = len(df)
    yield {"current": 0, "total": total_rows, "message": f"Loaded {total_rows} rows. Starting audit...", "status": "processing"}
    
    # --- 3. Prepare Output Columns ---
    df['API Rate'] = None
    df['Variance %'] = None
    df['Status'] = None
    
    # --- 4. Process Rows (use config for rate limiting) ---
    BATCH_SIZE = AUDIT_CONFIG.BATCH_SIZE
    BATCH_SLEEP = AUDIT_CONFIG.BATCH_SLEEP_SECONDS
    
    passed = 0
    exceptions = 0
    api_errors = 0
    
    for idx, row in df.iterrows():
        row_num = idx + 1
        
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
        
        api_rate = _get_cached_rate(date_str, base, source)
        cache_hit = api_rate is not None
        
        if not cache_hit:
            if testing_mode:
                api_rate = _generate_mock_rate(base, source, user_rate)
                yield {
                    "current": row_num,
                    "total": total_rows,
                    "message": f"Row {row_num}: [MOCK] {base}/{source} = {api_rate:.6f}",
                    "status": "processing"
                }
            else:
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
            
            _set_cached_rate(date_str, base, source, api_rate)
        else:
            yield {
                "current": row_num,
                "total": total_rows,
                "message": f"Row {row_num}: [CACHE] {base}/{source} = {api_rate:.6f}",
                "status": "processing"
            }
        
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


def run_audit(
    file,
    date_fmt: str = "YYYY-MM-DD",
    threshold: float = 5.0,
    api_key: str = "",
    testing_mode: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Runs the audit without yielding progress (for simple scripts).
    """
    gen = process_audit_file(file, date_fmt, threshold, api_key, testing_mode)
    
    result = None
    for update in gen:
        logger.info(update['message'])
        if update['status'] == 'complete':
            pass
    
    try:
        result = gen.send(None)
    except StopIteration as e:
        result = e.value
    
    return result if result else (pd.DataFrame(), {})
