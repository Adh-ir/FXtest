import time
import requests
import logging

class APIFetcher:
    """
    The API Throttle (The Fetcher)
    Fetches exchange rates from Twelve Data API with strict throttling and error handling.
    """
    
    BASE_URL = "https://api.twelvedata.com/exchange_rate"
    TIME_SERIES_URL = "https://api.twelvedata.com/time_series"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    def fetch_rates(self, pairs_config: list, start_date: str = None, end_date: str = None) -> list:
        """
        Iterates through the list of pairs and fetches rates.
        Enforces rate limits: Sleep 15s every 5 requests.
        Handles 429 errors with 60s cooldown.
        """
        results = []
        request_count = 0
        
        print(f"Starting fetch for {len(pairs_config)} pairs...")
        
        for config in pairs_config:
            symbol = config['api_symbol']
            
            # Throttling Logic: Sleep after every 5th request (before the 6th, 11th, etc.)
            # "processes requests in batches of 5 ... delay between every 5th request"
            if request_count > 0 and request_count % 5 == 0:
                print(f"Request count is {request_count}. Throttling for 15 seconds to respect API limits...")
                time.sleep(15)
            
            print(f"Fetching {symbol}...")
            api_data = self._make_request(symbol, start_date, end_date)
            
            if api_data:
                results.append({
                    'api_data': api_data,
                    'config': config
                })
            
            request_count += 1
            
        return results

    def _make_request(self, symbol: str, start_date: str = None, end_date: str = None) -> dict:
        """
        Helper to make the GET request with 429 handling.
        """
        if start_date and end_date:
            url = f"{self.TIME_SERIES_URL}?symbol={symbol}&interval=1day&start_date={start_date}&end_date={end_date}&apikey={self.api_key}"
        else:
            url = f"{self.BASE_URL}?symbol={symbol}&apikey={self.api_key}"
        
        while True:
            try:
                response = requests.get(url)
                
                # Check for HTTP errors first (though API usually returns 200 with error JSON)
                if response.status_code == 429:
                    print("HTTP 429 received. Entering 60s cooldown...")
                    time.sleep(60)
                    continue
                
                try:
                    data = response.json()
                except ValueError:
                    print(f"Invalid JSON response for {symbol}")
                    return None

                # Twelve Data Check
                if 'rate' in data or 'values' in data:
                    return data
                elif data.get('code') == 429:
                    print("API Code 429 (Limit Reached). Entering 60s cooldown...")
                    time.sleep(60)
                    continue
                else:
                    print(f"Error fetching {symbol}: {data.get('message', 'Unknown error')}")
                    return None
                    
            except requests.RequestException as e:
                print(f"Network error fetching {symbol}: {e}")
                return None
