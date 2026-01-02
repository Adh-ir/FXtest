from unittest.mock import patch

import pytest

from forex.facade import get_rates


class TestGetRates:
    """Tests for the get_rates facade function."""

    @pytest.fixture
    def mock_api_client(self):
        with patch("forex.facade.TwelveDataClient") as mock:
            yield mock

    def test_get_rates_invert_swap_columns(self, mock_api_client):
        """
        Verify that when invert=True:
        1. The rate is inverted (1/rate).
        2. The Base and Source columns are swapped.
        """
        # Setup Mock
        mock_instance = mock_api_client.return_value

        # Mock fetch_time_series response
        mock_instance.fetch_time_series.return_value = {"values": [{"datetime": "2023-01-01", "close": "2.0"}]}

        # Input: Base=USD, Source=EUR => Rate should be 2.0
        # If Inverted: Base=EUR, Source=USD => Rate should be 0.5

        # Note: forex/data_processor.py determines standard pair.
        # USD(Index 4) vs EUR(Index 0) -> Priority EUR < USD -> Pair EUR/USD
        # Wait, let's look at DataProcessor.determine_standard_pair again.
        # EUR is index 0. USD is index 4. p_a(EUR) < p_b(USD). Returns EUR/USD, invert=False.

        # Let's try a case where we simple ask for Base=USD, Source=ZAR
        # USD(4) vs ZAR(999). p_a < p_b. Pair USD/ZAR. Invert=False.

        # We ask for get_rates(Base=["USD"], Target=["ZAR"], invert=True)
        # Expected:
        #  - Originally: Base=USD, Source=ZAR, Rate=2.0
        #  - Inverted: Base=ZAR, Source=USD, Rate=0.5

        df = get_rates(
            api_key="test",
            base_currencies=["USD"],
            start_date="2023-01-01",
            end_date="2023-01-02",
            target_currencies=["ZAR"],
            invert=True,
        )

        assert not df.empty
        row = df.iloc[0]

        # Check Rate Inversion
        assert row["Exchange Rate"] == 0.5

        # Check Column Swapping
        assert row["Currency Base"] == "ZAR"
        assert row["Currency Source"] == "USD"
