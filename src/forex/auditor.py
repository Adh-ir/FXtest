"""
Audit & Reconciliation Module

Processes user-uploaded Excel files, fetches official rates from Twelve Data API,
and compares them to user-provided rates.

CRITICAL: Designed to survive strict API Rate Limits (Twelve Data Free Tier = ~8 requests/minute).
"""

import asyncio
import logging
import random
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from .api_client import TwelveDataClient
from .cache import get_cache_backend
from .config import AUDIT_CONFIG

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# --- Column Name Mappings (Flexible Schema Support) ---
COLUMN_MAPPINGS = {
    "date": ["Date", "date", "DATE", "Transaction Date", "Trade Date"],
    "base": ["Base", "base", "BASE", "Base Currency", "base_currency", "From", "from"],
    "source": [
        "Source",
        "source",
        "SOURCE",
        "Source Currency",
        "source_currency",
        "To",
        "to",
        "Target",
    ],
    "user_rate": [
        "User Rate",
        "user_rate",
        "Rate",
        "rate",
        "Exchange Rate",
        "exchange_rate",
        "FX Rate",
    ],
}


def validate_schema(df: pd.DataFrame) -> tuple[bool, dict[str, str], str]:
    """
    Validates the DataFrame schema and maps columns to standard names.
    Case-insensitive matching and whitespace ignoring.
    """
    found_mapping = {}
    missing_fields = []

    # Normalize columns: lower case and remove ALL whitespace (not just strip)
    # This handles "Base Currency", "BaseCurrency", " Base Currency " etc.
    df_cols_norm = {c.lower().replace(" ", ""): c for c in df.columns}

    for required, variants in COLUMN_MAPPINGS.items():
        # Normalize variants too
        variants_norm = [v.lower().replace(" ", "") for v in variants]
        match = next((col for col in df_cols_norm if col in variants_norm), None)

        if match:
            # Rename the original column to the standard internal name
            original_col_name = df_cols_norm[match]
            df.rename(columns={original_col_name: required}, inplace=True)
            found_mapping[required] = required  # Track that we have mapped it
        else:
            missing_fields.append(required)

    if missing_fields:
        missing_desc = ", ".join(
            [f"{k} (e.g., {COLUMN_MAPPINGS[k][0]})" for k in missing_fields]
        )
        error_msg = f"Missing required columns. Expected one of each: {missing_desc}"
        return False, {}, error_msg

    return True, found_mapping, ""


# --- Rate Cache (using distributed cache backend) ---
# TTL of 24 hours for audit rates (they don't change frequently)
AUDIT_RATE_CACHE_TTL = 86400


def _create_rate_cache_key(date_str: str, base: str, source: str) -> str:
    """Create cache key for audit rate lookup."""
    return f"audit_rate:{date_str}:{base.upper()}:{source.upper()}"


def _get_cached_rate(date_str: str, base: str, source: str) -> float | None:
    """Check if rate is already in cache."""
    cache = get_cache_backend()
    return cache.get(_create_rate_cache_key(date_str, base, source))


def _set_cached_rate(date_str: str, base: str, source: str, rate: float) -> None:
    """Store rate in cache."""
    cache = get_cache_backend()
    cache.set(
        _create_rate_cache_key(date_str, base, source),
        rate,
        ttl_seconds=AUDIT_RATE_CACHE_TTL,
    )


def _fetch_rate_with_fallback(client: TwelveDataClient, base: str, source: str, date_str: str) -> float | None:
    """
    Fetches rate with a 3-day lookback fallback for missing data (e.g. weekends).
    IMPORTANT: Lookback is DISABLED for current date (today) to avoid stale data.
    """
    # 1. Try exact date
    rate = client.fetch_historical_rate(base, source, date_str)
    if rate is not None:
        return rate

    # 2. Check if requested date is today - if so, skip lookback
    today_str = datetime.now().strftime("%Y-%m-%d")
    if date_str == today_str:
        logger.info(f"Requested date is today ({today_str}). Skipping lookback to avoid stale data.")
        return None

    # 3. Lookback up to 3 days (only for historical dates)
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        for i in range(1, 4):
            prev_date = dt - timedelta(days=i)
            prev_str = prev_date.strftime("%Y-%m-%d")

            logger.info(f"Looking back {i} day(s) to {prev_str} for {base}/{source}")
            rate = client.fetch_historical_rate(base, source, prev_str)
            if rate is not None:
                return rate
    except Exception as e:
        logger.warning(f"Error during lookback: {e}")

    return None


def _generate_mock_rate(base: str, source: str, user_rate: float) -> float:
    """
    Generates a mock rate for testing mode.
    """
    # Variance between -5% and +5%
    variance_pct = random.uniform(-0.05, 0.05)
    mock_rate = user_rate * (1 + variance_pct)
    return round(mock_rate, 6)


def _parse_date(date_value: Any, date_fmt: str) -> str | None:
    """
    Parses a date value from Excel into a standardized YYYY-MM-DD string.

    Uses the format string to determine day/month order (dayfirst), then
    leverages pandas for flexible parsing that handles:
    - Different separators (-, /, .)
    - Single-digit days/months (1 vs 01)
    - Various formats as long as day/month order is correct
    """

    # Detect if format is day-first or month-first by checking position of D vs M
    fmt_upper = date_fmt.upper()

    # Find first occurrence of D and M in the format
    d_pos = fmt_upper.find("D")
    m_pos = fmt_upper.find("M")

    # If D appears before M, it's day-first; otherwise month-first
    # Default to month-first (ISO standard) if can't determine
    dayfirst = d_pos < m_pos if (d_pos >= 0 and m_pos >= 0) else False

    try:
        if isinstance(date_value, datetime):
            return date_value.strftime("%Y-%m-%d")
        elif isinstance(date_value, str):
            date_str = date_value.strip()
            # Use pandas with the detected dayfirst setting
            dt = pd.to_datetime(date_str, dayfirst=dayfirst)
            return dt.strftime("%Y-%m-%d")
        else:
            # Excel datetime objects, etc.
            dt = pd.to_datetime(date_value, dayfirst=dayfirst)
            return dt.strftime("%Y-%m-%d")
    except Exception as e:
        logger.warning(f"Date parse error for '{date_value}': {e}")
        return None


def process_audit_file(
    file,
    date_fmt: str = "YYYY-MM-DD",
    threshold: float = 5.0,
    api_key: str = "",
    testing_mode: bool = True,
    invert_rates: bool = False,
) -> Generator[dict[str, Any], None, tuple[pd.DataFrame, dict[str, Any]]]:
    """
    Processes a user-uploaded Excel/CSV file for audit and reconciliation.

    YIELDS progress updates for UI feedback, then RETURNS final results.
    """

    # --- 1. Load File ---
    yield {"current": 0, "total": 0, "message": "Loading file...", "status": "loading"}

    try:
        file_path = ""
        if hasattr(file, "name"):
            file_path = file.name
        elif isinstance(file, str):
            file_path = file

        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
    except Exception as e:
        yield {
            "current": 0,
            "total": 0,
            "message": f"Error loading file: {e}",
            "status": "error",
        }
        return pd.DataFrame(), {
            "total_rows": 0,
            "exceptions": 0,
            "passed": 0,
            "api_errors": 0,
            "error": str(e),
        }

    # --- 2. Validate Schema ---
    is_valid, col_map, error_msg = validate_schema(df)

    if not is_valid:
        yield {"current": 0, "total": 0, "message": error_msg, "status": "error"}
        return pd.DataFrame(), {
            "total_rows": 0,
            "exceptions": 0,
            "passed": 0,
            "api_errors": 0,
            "error": error_msg,
        }

    schema_info = ", ".join([f"{k}='{v}'" for k, v in col_map.items()])
    yield {
        "current": 0,
        "total": 0,
        "message": f"Schema validated. Columns: {schema_info}",
        "status": "loading",
    }

    total_rows = len(df)
    yield {
        "current": 0,
        "total": total_rows,
        "message": f"Loaded {total_rows} rows. Starting audit...",
        "status": "processing",
    }

    # --- 3. Prepare Output Columns ---
    df["API Rate"] = None
    df["Variance %"] = None
    df["Status"] = None

    # --- 4. Process Rows (use config for rate limiting) ---
    BATCH_SIZE = AUDIT_CONFIG.BATCH_SIZE

    # Initialize API Client
    api_client = TwelveDataClient(api_key=api_key) if not testing_mode else None

    passed = 0
    exceptions = 0
    api_errors = 0

    for idx, row in df.iterrows():
        row_num = idx + 1

        date_str = _parse_date(row[col_map["date"]], date_fmt)
        if not date_str:
            df.at[idx, "Status"] = "DATE_ERROR"
            api_errors += 1
            yield {
                "current": row_num,
                "total": total_rows,
                "message": f"Row {row_num}: Invalid date format",
                "status": "processing",
            }
            continue

        base = str(row[col_map["base"]]).strip().upper()
        source = str(row[col_map["source"]]).strip().upper()
        user_rate = float(row[col_map["user_rate"]])

        api_rate = _get_cached_rate(date_str, base, source)
        cache_hit = api_rate is not None

        if not cache_hit:
            if testing_mode:
                api_rate = _generate_mock_rate(base, source, user_rate)
                yield {
                    "current": row_num,
                    "total": total_rows,
                    "message": f"Row {row_num}: [MOCK] {base}/{source} = {api_rate:.6f}",
                    "status": "processing",
                }
            else:
                if row_num > 1 and (row_num - 1) % BATCH_SIZE == 0:
                    yield {
                        "current": row_num,
                        "total": total_rows,
                        "message": f"Processing batch {(row_num - 1) // BATCH_SIZE}...",
                        "status": "processing",
                    }

                # Use centralized client
                api_rate = _fetch_rate_with_fallback(api_client, base, source, date_str)

                if api_rate is None:
                    df.at[idx, "Status"] = "API_ERROR"
                    api_errors += 1
                    yield {
                        "current": row_num,
                        "total": total_rows,
                        "message": f"Row {row_num}: API error for {base}/{source}",
                        "status": "processing",
                    }
                    continue

                yield {
                    "current": row_num,
                    "total": total_rows,
                    "message": f"Row {row_num}: Fetched {base}/{source} = {api_rate:.6f}",
                    "status": "processing",
                }

            _set_cached_rate(date_str, base, source, api_rate)
        else:
            yield {
                "current": row_num,
                "total": total_rows,
                "message": f"Row {row_num}: [CACHE] {base}/{source} = {api_rate:.6f}",
                "status": "processing",
            }

        if api_rate and api_rate != 0:
            if invert_rates:
                api_rate = 1 / api_rate

            variance = abs((user_rate - api_rate) / api_rate) * 100
            df.at[idx, "API Rate"] = round(api_rate, 6)
            df.at[idx, "Variance %"] = round(variance, 2)

            if variance <= threshold:
                df.at[idx, "Status"] = "PASS"
                passed += 1
            else:
                df.at[idx, "Status"] = "EXCEPTION"
                exceptions += 1

    summary = {
        "total_rows": total_rows,
        "passed": passed,
        "exceptions": exceptions,
        "api_errors": api_errors,
        "testing_mode": testing_mode,
    }

    # Include the final result in the yield for reliable capture
    yield {
        "current": total_rows,
        "total": total_rows,
        "message": f"Audit complete. Passed: {passed}, Exceptions: {exceptions}, Errors: {api_errors}",
        "status": "complete",
        "result": (df, summary),  # Include result here for reliable access
    }

    return df, summary  # Keep for backward compatibility


def clear_rate_cache() -> None:
    """Clears the rate cache (works with both in-memory and Redis)."""
    cache = get_cache_backend()
    cache.clear()
    logger.info("Rate cache cleared.")


def run_audit(
    file,
    date_fmt: str = "YYYY-MM-DD",
    threshold: float = 5.0,
    api_key: str = "",
    testing_mode: bool = True,
    invert_rates: bool = False,
    progress_callback: Callable[[str], None] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Runs the audit synchronously (for simple scripts and Streamlit).
    Returns the result directly without using StopIteration.
    Encapsulates generator logic for simpler consumption.
    Now supports optional progress_callback to report status strings.
    """
    gen = process_audit_file(file, date_fmt, threshold, api_key, testing_mode, invert_rates)

    result = None

    # Iterate through the generator to drive execution
    for update in gen:
        # Check if we have a progress message to report
        if progress_callback and "message" in update:
            # Format: "Step X/Y: Message" or just "Message"
            # If current/total are present, we can format a nice string
            current = update.get("current")
            total = update.get("total")
            msg = update.get("message", "")

            if current is not None and total is not None and total > 0:
                progress_callback(f"processing {current}/{total}: {msg}")
            else:
                progress_callback(msg)

        if update.get("status") == "complete" and "result" in update:
            result = update["result"]

    return result if result else (pd.DataFrame(), {})


# Thread pool for async operations
_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_worker")


async def run_audit_async(
    file,
    date_fmt: str = "YYYY-MM-DD",
    threshold: float = 5.0,
    api_key: str = "",
    testing_mode: bool = True,
    invert_rates: bool = False,
    progress_callback: Callable[[str], None] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Async version of run_audit for non-blocking execution.

    Offloads the synchronous audit processing to a thread pool,
    allowing the UI to remain responsive during large file processing.

    Usage:
        result = await run_audit_async(file, api_key=key)

    Args:
        Same as run_audit()

    Returns:
        tuple[pd.DataFrame, dict]: Audit results and summary statistics
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _audit_executor,
        lambda: run_audit(
            file,
            date_fmt,
            threshold,
            api_key,
            testing_mode,
            invert_rates,
            progress_callback,
        ),
    )
    return result
