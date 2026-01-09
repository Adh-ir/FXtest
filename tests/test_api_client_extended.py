from unittest.mock import MagicMock, patch

import pytest
from forex.api_client import TwelveDataClient


@pytest.fixture
def client(mock_api_key):
    return TwelveDataClient(mock_api_key)


class TestTwelveDataClientExtended:
    @patch("forex.api_client.requests.get")
    def test_fetch_exchange_rate_happy_path(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"rate": "18.50"}
        mock_get.return_value = mock_response

        result = client.fetch_exchange_rate("USD/ZAR")
        assert result == {"rate": "18.50"}

    @patch("forex.api_client.requests.get")
    def test_fetch_historical_rate_happy_path(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"values": [{"close": "18.50"}]}
        mock_get.return_value = mock_response

        result = client.fetch_historical_rate("USD", "ZAR", "2024-01-01")
        assert result == 18.50

    @patch("forex.api_client.requests.get")
    def test_fetch_historical_rate_no_data(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"values": []}
        mock_get.return_value = mock_response

        result = client.fetch_historical_rate("USD", "ZAR", "2024-01-01")
        assert result is None

    @patch("forex.api_client.requests.get")
    def test_fetch_historical_rate_error(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "error"}
        mock_get.return_value = mock_response

        result = client.fetch_historical_rate("USD", "ZAR", "2024-01-01")
        assert result is None

    @patch("forex.api_client.time.sleep")
    @patch("forex.api_client.requests.get")
    def test_make_request_rate_limit_retry(self, mock_get, mock_sleep, client):
        mock_response_err = MagicMock()
        mock_response_err.status_code = 429

        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.json.return_value = {"data": "ok"}

        mock_get.side_effect = [mock_response_err, mock_response_ok]

        result = client._make_request("url", {})
        assert result == {"data": "ok"}
        assert mock_sleep.called

    def test_redact_api_key(self, client, mock_api_key):
        text = f"Error with key {mock_api_key}"
        redacted = client._redact_api_key(text)
        assert "[REDACTED]" in redacted
        assert mock_api_key not in redacted

    @patch("forex.api_client.time.sleep")
    def test_enforce_rate_limit_sleeps(self, mock_sleep, client):
        client.RATE_LIMIT_REQUESTS = 1
        client.RATE_LIMIT_WINDOW = 60
        client._request_timestamps.append(1000)

        with patch("forex.api_client.time.time", return_value=1001):
            client._enforce_rate_limit()
            assert mock_sleep.called
