"""
Smoke tests for forex/api_client.py
Tests both happy paths and edge cases for TwelveDataClient.
"""

from unittest.mock import MagicMock, patch


class TestTwelveDataClientInit:
    """Tests for TwelveDataClient initialization."""

    def test_happy_path_initialization(self, mock_api_key):
        """Happy path: client initializes with API key."""
        from forex.api_client import TwelveDataClient

        client = TwelveDataClient(mock_api_key)

        assert client.api_key == mock_api_key
        assert hasattr(client, "_request_timestamps")

    def test_happy_path_has_base_url(self, mock_api_key):
        """Happy path: client has correct BASE_URL."""
        from forex.api_client import TwelveDataClient

        client = TwelveDataClient(mock_api_key)

        assert client.BASE_URL == "https://api.twelvedata.com"


class TestTwelveDataClientFetchTimeSeries:
    """Tests for fetch_time_series method."""

    @patch("forex.api_client.requests.get")
    def test_happy_path_returns_data(self, mock_get, mock_api_key):
        """Happy path: fetch_time_series returns expected data structure."""
        from forex.api_client import TwelveDataClient

        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "meta": {"symbol": "USD/ZAR"},
            "values": [{"datetime": "2024-01-01", "close": "18.50"}],
        }
        mock_get.return_value = mock_response

        client = TwelveDataClient(mock_api_key)
        result = client.fetch_time_series("USD/ZAR", "2024-01-01", "2024-01-02")

        assert result is not None
        assert "meta" in result
        assert "values" in result

    @patch("forex.api_client.requests.get")
    def test_edge_case_api_error_response(self, mock_get, mock_api_key):
        """Edge case: API returns error status."""
        from forex.api_client import TwelveDataClient

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "message": "Invalid symbol",
        }
        mock_get.return_value = mock_response

        client = TwelveDataClient(mock_api_key)
        result = client.fetch_time_series("INVALID/PAIR", "2024-01-01", "2024-01-02")

        assert result is None


class TestTwelveDataClientFetchAvailablePairs:
    """Tests for fetch_available_pairs method."""

    @patch("forex.api_client.requests.get")
    def test_happy_path_returns_currency_list(self, mock_get, mock_api_key):
        """Happy path: returns list of currency codes."""
        from forex.api_client import TwelveDataClient

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"symbol": "ZAR/USD"},
                {"symbol": "ZAR/EUR"},
                {"symbol": "USD/ZAR"},
            ]
        }
        mock_get.return_value = mock_response

        client = TwelveDataClient(mock_api_key)
        result = client.fetch_available_pairs("ZAR")

        assert isinstance(result, list)
        assert "USD" in result
        assert "EUR" in result

    @patch("forex.api_client.requests.get")
    def test_edge_case_no_pairs_found(self, mock_get, mock_api_key):
        """Edge case: returns empty list when no pairs found."""
        from forex.api_client import TwelveDataClient

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        client = TwelveDataClient(mock_api_key)
        result = client.fetch_available_pairs("INVALID")

        assert result == []


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    def test_rate_limit_constants_exist(self, mock_api_key):
        """Happy path: rate limit constants are properly defined."""
        from forex.api_client import TwelveDataClient

        client = TwelveDataClient(mock_api_key)

        assert hasattr(client, "RATE_LIMIT_REQUESTS")
        assert hasattr(client, "RATE_LIMIT_WINDOW")
        assert client.RATE_LIMIT_REQUESTS == 8
        assert client.RATE_LIMIT_WINDOW == 60
