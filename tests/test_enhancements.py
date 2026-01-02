from datetime import datetime
from unittest.mock import MagicMock, patch

from forex.auditor import _fetch_rate_with_fallback
from forex.data_processor import DataProcessor


class TestDataProcessorForwardFill:
    def test_process_results_forward_fill(self):
        """Verify forward fill covers weekends."""

        # Mock fetcher result
        # Data: Friday 2023-01-06 = 10.0
        # Request: 2023-01-06 to 2023-01-09 (Fri to Mon)
        # Expected: Fri=10, Sat=10, Sun=10, Mon=NaN (if no data) or Mon=NaN -> dropped

        mock_api_data = {"values": [{"datetime": "2023-01-06", "close": "10.0"}]}

        config = {
            "api_symbol": "USD/ZAR",
            "user_base": "USD",
            "user_target": "ZAR",
            "invert": False,
            "calculation_mode": "direct",
        }

        fetch_results = [{"config": config, "api_data": mock_api_data}]

        # We need to mock datetime.now() because of the "today" check in code
        # Let's assume today is 2023-02-01 so we can fill up to Jan 9
        with patch("forex.data_processor.datetime") as mock_dt:
            mock_dt.now.return_value.date.return_value = datetime(2023, 2, 1).date()

            df = DataProcessor.process_results(
                fetch_results,
                start_date="2023-01-06",
                end_date="2023-01-08",  # Fri, Sat, Sun
            )

        assert not df.empty
        assert len(df) == 3  # Fri, Sat, Sun

        # Check rates
        rates = df["Exchange Rate"].tolist()
        dates = df["Date"].tolist()

        assert dates == [
            "2023-01-08",
            "2023-01-07",
            "2023-01-06",
        ]  # Descending order check
        assert rates == [10.0, 10.0, 10.0]

    def test_process_results_limit_constraint(self):
        """Verify forward fill respects 3-day limit."""

        # Data: Day 1. Gap Day 2,3,4,5.
        # Fill Day 2,3,4. Day 5 dropped.

        mock_api_data = {"values": [{"datetime": "2023-01-01", "close": "10.0"}]}

        config = {
            "api_symbol": "USD/ZAR",
            "user_base": "USD",
            "user_target": "ZAR",
            "invert": False,
        }

        fetch_results = [{"config": config, "api_data": mock_api_data}]

        with patch("forex.data_processor.datetime") as mock_dt:
            mock_dt.now.return_value.date.return_value = datetime(2023, 2, 1).date()

            df = DataProcessor.process_results(
                fetch_results,
                start_date="2023-01-01",
                end_date="2023-01-05",  # 5 days
            )

        # 1(Data), 2(Fill), 3(Fill), 4(Fill), 5(NaN)
        # Should contain 1,2,3,4. 5 dropped.
        assert len(df) == 4
        assert "2023-01-05" not in df["Date"].values
        assert "2023-01-04" in df["Date"].values


class TestAuditorLookback:
    def test_fetch_rate_fallback_success_immediate(self):
        """Test success on exact date."""
        mock_client = MagicMock()
        mock_client.fetch_historical_rate.return_value = 1.5

        rate = _fetch_rate_with_fallback(mock_client, "USD", "ZAR", "2023-01-05")

        assert rate == 1.5
        mock_client.fetch_historical_rate.assert_called_once_with("USD", "ZAR", "2023-01-05")

    def test_fetch_rate_fallback_lookback(self):
        """Test fallback works (e.g. Sunday -> Friday)."""
        mock_client = MagicMock()
        # 2023-01-01 is Sunday.
        # Call 1: 2023-01-01 -> None
        # Call 2 (Lookback 1): 2022-12-31 -> None
        # Call 3 (Lookback 2): 2022-12-30 -> 1.5 (Friday)
        mock_client.fetch_historical_rate.side_effect = [None, None, 1.5]

        # Use 2023-02-01 as "now" to allow lookback (avoid "today" check)
        with patch("forex.auditor.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2023-02-01"
            # We must restore original strptime because _fetch_rate_with_fallback uses it
            mock_dt.strptime.side_effect = datetime.strptime

            rate = _fetch_rate_with_fallback(mock_client, "USD", "ZAR", "2023-01-01")

        assert rate == 1.5
        assert mock_client.fetch_historical_rate.call_count == 3

    def test_fetch_rate_fallback_fail(self):
        """Test fail if no data within 3 days."""
        mock_client = MagicMock()
        mock_client.fetch_historical_rate.return_value = None

        with patch("forex.auditor.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2023-02-01"
            mock_dt.strptime.side_effect = datetime.strptime

            rate = _fetch_rate_with_fallback(mock_client, "USD", "ZAR", "2023-01-01")

        assert rate is None
        # 1 initial + 3 lookbacks = 4 calls
        assert mock_client.fetch_historical_rate.call_count == 4
