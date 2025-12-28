import time
import requests
import logging
from collections import deque
from typing import Optional, Dict, Any, List

# Configure logger
logger = logging.getLogger(__name__)

class TwelveDataClient:
    """
    Client for interacting with the Twelve Data API.
    Enforces strict rate limiting (8 requests per minute) for Free Plan usage.
    """
    
    BASE_URL = "https://api.twelvedata.com"
    RATE_LIMIT_REQUESTS = 8
    RATE_LIMIT_WINDOW = 60  # seconds

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
            sleep_time = (oldest_timestamp + self.RATE_LIMIT_WINDOW) - now + 0.5 # Add buffering
            
            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds.")
                time.sleep(sleep_time)
                # After sleeping, we technically might have space, but let's re-check or just proceed.
                # Recursive strictness, but let's just append new time after sleep.
        
        self._request_timestamps.append(time.time())

    def fetch_time_series(self, symbol: str, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """
        Fetches time series data for a specific symbol.
        """
        url = f"{self.BASE_URL}/time_series"
        params = {
            "apikey": self.api_key,
            "symbol": symbol,
            "interval": "1day",
            "start_date": start_date,
            "end_date": end_date
        }
        
        return self._make_request(url, params)

    def fetch_exchange_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetches the current exchange rate for a symbol.
        """
        url = f"{self.BASE_URL}/exchange_rate"
        params = {
            "apikey": self.api_key,
            "symbol": symbol
        }
        return self._make_request(url, params)

    def fetch_available_pairs(self, base_currency: str) -> List[str]:
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
            
            if 'data' not in data:
                logger.error(f"Failed to fetch forex pairs: {data}")
                return []
            
            base_upper = base_currency.upper()
            targets = set()
            
            for pair in data['data']:
                symbol = pair.get('symbol', '')
                if '/' in symbol:
                    left, right = symbol.split('/')
                    # If base is on the left (e.g., ZAR/USD), target is right
                    if left == base_upper:
                        targets.add(right)
                    # If base is on the right (e.g., USD/ZAR), target is left
                    elif right == base_upper:
                        targets.add(left)
            
            return sorted(list(targets))
            
        except Exception as e:
            logger.error(f"Error fetching forex pairs: {e}")
            return []

    def _make_request(self, url: str, params: Dict[str, str], retry_count: int = 0) -> Optional[Dict[str, Any]]:
        """
        Helper to make the GET request with 429 handling and rate limit enforcement.
        """
        self._enforce_rate_limit()
        
        try:
            response = requests.get(url, params=params)
            
            if response.status_code == 429:
                if retry_count < 3:
                     # Exponential backoff: 60s, 120s, etc.
                    wait_time = 60 * (retry_count + 1)
                    logger.warning(f"HTTP 429 received from API. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    return self._make_request(url, params, retry_count + 1)
                else:
                    logger.error("Max retries reached for 429 errors.")
                    return None

            data = response.json()
            
            # Application-level error check
            if data.get('code') == 429:
                 if retry_count < 3:
                    wait_time = 60 * (retry_count + 1)
                    logger.warning(f"API Code 429 received. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    return self._make_request(url, params, retry_count + 1)
                 else:
                    return None
            
            if data.get('status') == 'error':
                 logger.error(f"API Error: {data.get('message')}")
                 return None

            return data

        except requests.RequestException as e:
            logger.error(f"Network error: {e}")
            return None
