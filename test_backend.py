import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from logic.facade import get_rates
from logic.data_processor import DataProcessor
from logic.api_client import TwelveDataClient
from logic.utils import convert_df_to_csv, convert_df_to_excel
import streamlit as st

# Verify imports work
# Verify imports work
# logging.info("Imports successful.")

class TestBackend(unittest.TestCase):
    
    def setUp(self):
        # Mock Streamlit cache to just execute function
        # We can't easily mock the decorator behavior without reloading, 
        # so we rely on the fact that outside of Streamlit runtime, the function still runs 
        # but might complain about caching context if not careful.
        # Actually, st.cache_data works if streamlit is installed, even if no app running?
        # It usually warns "No script run context found". We can ignore that for logic testing.
        pass

    @patch('logic.api_client.TwelveDataClient.fetch_time_series')
    def test_get_rates_direct(self, mock_fetch):
        # logging.info("\nTesting Direct Rate Fetch (Target: USD)...")
        # Setup Mock Data
        mock_data = {
            'values': [
                {'datetime': '2023-01-01', 'close': '1.2345'}
            ],
            'status': 'ok'
        }
        mock_fetch.return_value = mock_data
        
        # Test
        # EUR is standard, USD is target. EUR/USD.
        df = get_rates("test_key", ["EUR"], "2023-01-01", "2023-01-02")
        
        # Verify
        self.assertFalse(df.empty)
        # We expect multiple rows because the basket has multiple targets.
        # Filter for USD
        usd_row = df[(df['Currency Base'] == 'EUR') & (df['Currency Source'] == 'USD')]
        self.assertEqual(len(usd_row), 1)
        self.assertEqual(usd_row.iloc[0]['Exchange Rate'], 1.2345)
        # logging.info("Direct Fetch Passed.")

    @patch('logic.api_client.TwelveDataClient.fetch_time_series')
    def test_get_rates_cross(self, mock_fetch):
        # logging.info("\nTesting Cross Rate Fetch (ZAR -> BWP)...")
        # Logic requests USD/ZAR and USD/BWP
        # ZAR is Exotic, BWP is Exotic.
        
        def side_effect(symbol, start, end):
            if symbol == 'USD/ZAR':
                return {'values': [{'datetime': '2023-01-01', 'close': '18.0'}], 'status': 'ok'}
            if symbol == 'USD/BWP':
                return {'values': [{'datetime': '2023-01-01', 'close': '13.0'}], 'status': 'ok'}
            return None
            
        mock_fetch.side_effect = side_effect
        
        df = get_rates("test_key", ["ZAR"], "2023-01-01", "2023-01-02")
        
        # Verify
        # Result should contain ZAR -> USD, ZAR -> EUR... ZAR -> BWP
        # We process ALL targets in basket.
        # Check ZAR -> BWP specifically
        # Rate = (1/USD_ZAR) * USD_BWP = (1/18.0) * 13.0 = 0.722222
        
        subset = df[(df['Currency Base'] == 'ZAR') & (df['Currency Source'] == 'BWP')]
        self.assertFalse(subset.empty)
        rate = subset.iloc[0]['Exchange Rate']
        expected = round((1.0/18.0) * 13.0, 6)
        self.assertEqual(rate, expected)
        # logging.info(f"Cross Rate Passed: {rate}")

    def test_export_utils(self):
        # logging.info("\nTesting Export Utils...")
        df = pd.DataFrame({
            'Currency Base': ['USD'], 'Currency Source': ['EUR'], 
            'Date': ['2023-01-01'], 'Exchange Rate': [0.9]
        })
        
        csv = convert_df_to_csv(df)
        self.assertTrue(len(csv) > 0)
        
        excel = convert_df_to_excel(df)
        self.assertTrue(len(excel) > 0)
        # logging.info("Export Utils Passed.")

if __name__ == '__main__':
    unittest.main()
