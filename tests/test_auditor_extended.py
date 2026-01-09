from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
from forex.auditor import _fetch_rate_with_fallback, _parse_date


class TestAuditorExtended:
    def test_parse_date_datetime_obj(self):
        dt = datetime(2024, 1, 1)
        assert _parse_date(dt, "YYYY-MM-DD") == "2024-01-01"

    def test_parse_date_other_obj(self):
        # pd.Timestamp
        ts = pd.Timestamp("2024-01-01")
        assert _parse_date(ts, "YYYY-MM-DD") == "2024-01-01"

    def test_fetch_rate_with_fallback_success(self):
        mock_client = MagicMock()
        mock_client.fetch_historical_rate.side_effect = [None, 18.50]

        # Test fallback to prev day (2024-01-02 -> 2024-01-01)
        res = _fetch_rate_with_fallback(mock_client, "USD", "ZAR", "2024-01-02")
        assert res == 18.50
        assert mock_client.fetch_historical_rate.call_count == 2
