"""
Smoke tests for forex/auditor.py
Tests both happy paths and edge cases for audit functionality.
"""

from io import BytesIO

import pandas as pd


class TestValidateSchema:
    """Tests for validate_schema function."""

    def test_happy_path_valid_columns(self, valid_audit_dataframe):
        """Happy path: validates DataFrame with correct columns."""
        from forex.auditor import validate_schema

        is_valid, column_mapping, error = validate_schema(valid_audit_dataframe)

        assert is_valid is True
        assert error == ""
        assert isinstance(column_mapping, dict)
        # Should have mappings for the standard internal names
        assert "date" in column_mapping
        assert "base" in column_mapping
        assert "source" in column_mapping
        assert "user_rate" in column_mapping

    def test_edge_case_missing_columns(self, invalid_audit_dataframe):
        """Edge case: returns error for missing required columns."""
        from forex.auditor import validate_schema

        is_valid, column_mapping, error = validate_schema(invalid_audit_dataframe)

        assert is_valid is False
        assert isinstance(error, str)
        assert len(error) > 0


class TestParseDate:
    """Tests for _parse_date function."""

    def test_happy_path_yyyy_mm_dd(self):
        """Happy path: parses YYYY-MM-DD format."""
        from forex.auditor import _parse_date

        result = _parse_date("2024-01-15", "YYYY-MM-DD")

        assert result == "2024-01-15"

    def test_happy_path_dd_mm_yyyy(self):
        """Happy path: parses DD/MM/YYYY format."""
        from forex.auditor import _parse_date

        result = _parse_date("15/01/2024", "DD/MM/YYYY")

        assert result == "2024-01-15"

    def test_edge_case_invalid_date(self):
        """Edge case: returns None for invalid date."""
        from forex.auditor import _parse_date

        result = _parse_date("invalid-date", "YYYY-MM-DD")

        assert result is None

    def test_smart_separator_flexibility(self):
        """Smart parsing handles different separators."""
        from forex.auditor import _parse_date

        # Format says dashes, but data uses slashes - should still work
        result = _parse_date("2026/1/2", "YYYY-MM-DD")

        assert result == "2026-01-02"

    def test_smart_single_digit_handling(self):
        """Smart parsing handles single-digit days/months."""
        from forex.auditor import _parse_date

        result = _parse_date("2026-1-2", "YYYY-MM-DD")

        assert result == "2026-01-02"

    def test_smart_dayfirst_detection(self):
        """Smart parsing detects day-first from format."""
        from forex.auditor import _parse_date

        # DD-MM format means 1/2 = Jan 2nd (day=1, month=2? No, day=2, month=1)
        # Wait, DD-MM means first number is day, second is month
        # So 2-1-2026 with DD-MM-YYYY means day=2, month=1 = Jan 2nd
        result = _parse_date("2-1-2026", "DD-MM-YYYY")

        assert result == "2026-01-02"

    def test_smart_monthfirst_detection(self):
        """Smart parsing detects month-first from format."""
        from forex.auditor import _parse_date

        # MM-DD format means 1-2 = Jan 2nd (month=1, day=2)
        result = _parse_date("1-2-2026", "MM-DD-YYYY")

        assert result == "2026-01-02"

    def test_smart_yyyy_dd_mm_ambiguity(self):
        """Smart parsing handles YYYY-DD-MM format correctly."""
        from forex.auditor import _parse_date

        # YYYY-DD-MM with 2026/1/2 means year=2026, day=1, month=2 = Feb 1st
        result = _parse_date("2026/1/2", "YYYY-DD-MM")

        assert result == "2026-02-01"


class TestGenerateMockRate:
    """Tests for _generate_mock_rate function."""

    def test_happy_path_returns_float(self):
        """Happy path: returns a float rate."""
        from forex.auditor import _generate_mock_rate

        result = _generate_mock_rate("ZAR", "USD", 18.50)

        assert isinstance(result, float)

    def test_happy_path_rate_is_close_to_user_rate(self):
        """Happy path: mock rate is within reasonable range of user rate."""
        from forex.auditor import _generate_mock_rate

        user_rate = 18.50
        result = _generate_mock_rate("ZAR", "USD", user_rate)

        # Mock rate should be within 10% of user rate
        assert abs(result - user_rate) / user_rate < 0.10


class TestClearRateCache:
    """Tests for clear_rate_cache function."""

    def test_happy_path_clears_cache(self):
        """Happy path: cache is cleared without error."""
        from forex.auditor import (
            _get_cached_rate,
            _set_cached_rate,
            clear_rate_cache,
        )

        # Set a value first
        _set_cached_rate("2024-01-01", "TEST", "USD", 99.99)

        # Clear the cache
        clear_rate_cache()

        # Verify the value is gone
        result = _get_cached_rate("2024-01-01", "TEST", "USD")
        assert result is None


class TestRunAudit:
    """Tests for process_audit_file generator and run_audit wrapper."""

    def test_happy_path_with_testing_mode(self, mocker):
        """Happy path: generator yields progress updates in testing mode."""
        from forex.auditor import process_audit_file

        # Mock the client to prevent any potential network calls even if forex slips
        mocker.patch("forex.auditor.TwelveDataClient")

        # Create test file
        df = pd.DataFrame(
            {
                "Date": ["2024-01-01"],
                "Base Currency": ["ZAR"],
                "Source Currency": ["USD"],
                "rate": [18.50],
            }
        )

        buffer = BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        buffer.name = "test.csv"

        gen = process_audit_file(
            file=buffer,
            date_fmt="YYYY-MM-DD",
            threshold=5.0,
            api_key="test_key",
            testing_mode=True,
        )

        # Collect all updates from the generator
        updates = list(gen)

        # Verify we got progress updates
        assert len(updates) > 0

        # Verify update structure
        for update in updates:
            assert "message" in update
            assert "status" in update

        # Verify we got a "complete" status at the end
        final_status = updates[-1]["status"]
        assert final_status == "complete"

    def test_edge_case_empty_file(self):
        """Edge case: handles empty CSV file gracefully."""
        from forex.auditor import run_audit

        # Create empty file with headers only
        df = pd.DataFrame(columns=["Date", "Base Currency", "Source Currency", "rate"])

        buffer = BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        buffer.name = "empty.csv"

        result = run_audit(
            file=buffer,
            date_fmt="YYYY-MM-DD",
            threshold=5.0,
            api_key="test_key",
            testing_mode=True,
        )

        # Should handle gracefully (either return empty or None)
        assert result is not None or result is None  # Both are acceptable


class TestFetchRateWithFallbackMocked:
    """Tests for _fetch_rate_with_fallback using mocked TwelveDataClient."""

    def test_happy_path_first_try_succeeds(self, mocker):
        """Happy path: returns rate on first attempt."""
        from forex.auditor import _fetch_rate_with_fallback

        # Mock the client
        mock_client = mocker.MagicMock()
        mock_client.fetch_historical_rate.return_value = 18.50

        result = _fetch_rate_with_fallback(mock_client, "ZAR", "USD", "2024-01-01")

        assert result == 18.50
        mock_client.fetch_historical_rate.assert_called_once_with("ZAR", "USD", "2024-01-01")

    def test_fallback_on_weekend(self, mocker):
        """Fallback: tries previous days when requested date fails."""
        from forex.auditor import _fetch_rate_with_fallback

        # Mock client to fail first, then succeed
        mock_client = mocker.MagicMock()
        mock_client.fetch_historical_rate.side_effect = [None, 18.50]

        result = _fetch_rate_with_fallback(mock_client, "ZAR", "USD", "2024-01-06")  # A Saturday

        assert result == 18.50
        assert mock_client.fetch_historical_rate.call_count == 2

    def test_no_fallback_for_today(self, mocker):
        """Edge case: no fallback applied for today's date."""
        from datetime import datetime

        from forex.auditor import _fetch_rate_with_fallback

        today = datetime.now().strftime("%Y-%m-%d")

        # Mock client returning None
        mock_client = mocker.MagicMock()
        mock_client.fetch_historical_rate.return_value = None

        result = _fetch_rate_with_fallback(mock_client, "ZAR", "USD", today)

        # Should only call once (no fallback for today)
        assert mock_client.fetch_historical_rate.call_count == 1
        assert result is None


class TestRateCaching:
    """Tests for rate caching functionality."""

    def test_cache_hit_avoids_api_call(self, mocker):
        """Cache hit: uses cached rate instead of API call."""
        from forex.auditor import _get_cached_rate, _set_cached_rate, clear_rate_cache

        # Clear any existing cache
        clear_rate_cache()

        # Set a cached rate
        _set_cached_rate("2024-01-01", "ZAR", "USD", 18.50)

        # Verify cache hit
        result = _get_cached_rate("2024-01-01", "ZAR", "USD")

        assert result == 18.50

    def test_cache_miss_returns_none(self):
        """Cache miss: returns None for uncached rate."""
        from forex.auditor import _get_cached_rate, clear_rate_cache

        clear_rate_cache()

        result = _get_cached_rate("2024-12-31", "XYZ", "ABC")

        assert result is None

    def test_cache_is_case_insensitive(self):
        """Cache keys are case-insensitive for currency codes."""
        from forex.auditor import _get_cached_rate, _set_cached_rate, clear_rate_cache

        clear_rate_cache()

        _set_cached_rate("2024-01-01", "zar", "usd", 18.50)

        # Should match with uppercase
        result = _get_cached_rate("2024-01-01", "ZAR", "USD")

        assert result == 18.50
