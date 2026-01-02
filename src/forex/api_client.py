"""
Twelve Data API Client

Client for interacting with the Twelve Data API with rate limiting.
"""

import logging
import time
from collections import deque
from typing import Any

import requests

from .config import API_CONFIG

# Configure logger
logger = logging.getLogger(__name__)


class TwelveDataClient:
    """
    Client for interacting with the Twelve Data API.
    Enforces strict rate limiting (8 requests per minute) for Free Plan usage.
    """

    BASE_URL = API_CONFIG.BASE_URL
    RATE_LIMIT_REQUESTS = API_CONFIG.RATE_LIMIT_REQUESTS
    RATE_LIMIT_WINDOW = API_CONFIG.RATE_LIMIT_WINDOW_SECONDS

    def __init__(self, api_key: str):
        self.api_key = api_key
        # Queue to track request timestamps for rate limiting
        self._request_timestamps = deque()

    def _enforce_rate_limit(self):
        """
        Ensures we don't exceed RATE_LIMIT_REQUESTS per RATE_LIMIT_WINDOW.
        Sleeps if necessary.
        """
        now = time.time()

        # Remove timestamps older than the window
        while self._request_timestamps and self._request_timestamps[0] <= now - self.RATE_LIMIT_WINDOW:
            self._request_timestamps.popleft()

        if len(self._request_timestamps) >= self.RATE_LIMIT_REQUESTS:
            # Calculate sleep time: Time until the oldest request expires from the window
            oldest_timestamp = self._request_timestamps[0]
            sleep_time = (oldest_timestamp + self.RATE_LIMIT_WINDOW) - now + 0.5  # Add buffering

            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds.")
                time.sleep(sleep_time)

        self._request_timestamps.append(time.time())

    def fetch_time_series(self, symbol: str, start_date: str, end_date: str) -> dict[str, Any] | None:
        """
        Fetches time series data for a specific symbol.
        """
        url = f"{self.BASE_URL}/time_series"
        params = {
            "apikey": self.api_key,
            "symbol": symbol,
            "interval": "1day",
            "start_date": start_date,
            "end_date": end_date,
        }

        return self._make_request(url, params)

    def fetch_exchange_rate(self, symbol: str) -> dict[str, Any] | None:
        """
        Fetches the current exchange rate for a symbol.
        """
        url = f"{self.BASE_URL}/exchange_rate"
        params = {"apikey": self.api_key, "symbol": symbol}
        return self._make_request(url, params)

    def fetch_historical_rate(self, base: str, quote: str, date: str) -> float | None:
        """
        Fetches a single historical rate for a base/quote pair on a specific date.
        Returns the close price as a float, or None if not found or error.
        """
        url = f"{self.BASE_URL}/time_series"
        params = {
            "apikey": self.api_key,
            "symbol": f"{base}/{quote}",
            "interval": "1day",
            "start_date": date,
            "outputsize": "1",
        }

        data = self._make_request(url, params)

        if not data:
            return None

        if "values" in data and len(data["values"]) > 0:
            try:
                return float(data["values"][0]["close"])
            except (ValueError, KeyError, IndexError) as e:
                logger.error(f"Error parsing rate from API response: {e}")
                return None

        return None

    def fetch_available_pairs(self, base_currency: str) -> list[str]:
        """
        Fetches all available forex pairs for a given base currency.
        Returns list of target currency codes (e.g., ['USD', 'EUR', 'GBP', ...])

        Note: This does NOT count against rate limit as it's a metadata call.
        """
        url = f"{self.BASE_URL}/forex_pairs"
        params = {"apikey": self.api_key}

        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()

            if "data" not in data:
                logger.error(f"Failed to fetch forex pairs: {data}")
                return []

            base_upper = base_currency.upper()
            targets = set()

            for pair in data["data"]:
                symbol = pair.get("symbol", "")
                if "/" in symbol:
                    left, right = symbol.split("/")
                    # If base is on the left (e.g., ZAR/USD), target is right
                    if left == base_upper:
                        targets.add(right)
                    # If base is on the right (e.g., USD/ZAR), target is left
                    elif right == base_upper:
                        targets.add(left)

            return sorted(targets)

        except Exception as e:
            safe_message = self._redact_api_key(str(e))
            logger.error(f"Error fetching forex pairs: {safe_message}")
            return []

    def _make_request(self, url: str, params: dict[str, str], retry_count: int = 0) -> dict[str, Any] | None:
        """
        Helper to make the GET request with 429 handling and rate limit enforcement.
        """
        self._enforce_rate_limit()

        try:
            response = requests.get(url, params=params, timeout=API_CONFIG.REQUEST_TIMEOUT_SECONDS)

            if response.status_code == 429:
                if retry_count < API_CONFIG.MAX_RETRIES:
                    # Exponential backoff: 60s, 120s, etc.
                    wait_time = API_CONFIG.RETRY_BACKOFF_SECONDS * (retry_count + 1)
                    logger.warning(f"HTTP 429 received from API. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    return self._make_request(url, params, retry_count + 1)
                else:
                    logger.error("Max retries reached for 429 errors.")
                    return None

            data = response.json()

            # Application-level error check
            if data.get("code") == 429:
                if retry_count < API_CONFIG.MAX_RETRIES:
                    wait_time = API_CONFIG.RETRY_BACKOFF_SECONDS * (retry_count + 1)
                    logger.warning(f"API Code 429 received. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    return self._make_request(url, params, retry_count + 1)
                else:
                    return None

            if data.get("status") == "error":
                logger.error(f"API Error: {data.get('message')}")
                return None

            return data

        except requests.RequestException as e:
            # Redact API key from error message if it helps explain the details of the error without leaking secrets
            safe_message = self._redact_api_key(str(e))
            logger.error(f"Network error: {safe_message}")
            return None

    def _redact_api_key(self, text: str) -> str:
        """
        Removes the API key from a string if present.
        """
        if self.api_key and self.api_key in text:
            return text.replace(self.api_key, "[REDACTED]")
        return text
