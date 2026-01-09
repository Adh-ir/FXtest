from forex.data_processor import DataProcessor


class TestDataProcessorExtended:
    def test_parse_targets_keywords(self):
        assert DataProcessor.parse_targets("MAJOR") == DataProcessor.MAJOR_BASKET
        assert DataProcessor.parse_targets("AFRICAN") == DataProcessor.AFRICAN_BASKET
        assert DataProcessor.parse_targets("[DEFAULT]") == DataProcessor.TARGET_BASKET

    def test_parse_targets_with_base(self):
        # Should filter out base currency
        res = DataProcessor.parse_targets("USD, EUR, ZAR", base_currency="ZAR")
        assert "USD" in res
        assert "EUR" in res
        assert "ZAR" not in res

    def test_determine_standard_pair(self):
        # Priority: EUR < GBP < USD < ZAR (exotic)
        assert DataProcessor._determine_standard_pair("EUR", "USD") == ("EUR/USD", False)
        assert DataProcessor._determine_standard_pair("USD", "EUR") == ("EUR/USD", True)
        assert DataProcessor._determine_standard_pair("GBP", "EUR") == ("EUR/GBP", True)
        assert DataProcessor._determine_standard_pair("ZAR", "USD") == ("USD/ZAR", True)

    def test_parse_api_response_realtime(self):
        api_data = {"rate": "18.50", "timestamp": 1704067200}  # 2024-01-01
        df = DataProcessor._parse_api_response(api_data)
        assert not df.empty
        assert df.iloc[0]["Exchange Rate"] == 18.50
        assert df.iloc[0]["Date"] == "2024-01-01"

    def test_process_results_cross_via_usd(self):
        # Mock results for ZAR/BWP (cross via USD)
        fetch_results = [
            {
                "config": {
                    "api_symbol": "USD/ZAR",
                    "invert": False,
                    "user_base": "ZAR",
                    "user_target": "BWP",
                    "calculation_mode": "cross_via_usd",
                },
                "api_data": {"values": [{"datetime": "2024-01-01", "close": "18.00"}]},
            },
            # Note: The code expects USD/BWP in the cache for this mode
            {
                "config": {"api_symbol": "USD/BWP", "invert": False, "user_base": "USD", "user_target": "BWP"},
                "api_data": {"values": [{"datetime": "2024-01-01", "close": "13.50"}]},
            },
        ]

        df = DataProcessor.process_results(fetch_results)
        assert not df.empty
        # Filter for the cross rate result
        cross_df = df[(df["Currency Base"] == "ZAR") & (df["Currency Source"] == "BWP")]
        assert not cross_df.empty
        # Rate = (1/18) * 13.5 = 0.75
        assert cross_df.iloc[0]["Exchange Rate"] == 0.75
        assert cross_df.iloc[0]["Currency Base"] == "ZAR"
        assert cross_df.iloc[0]["Currency Source"] == "BWP"
