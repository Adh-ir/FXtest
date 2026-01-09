from unittest.mock import MagicMock, patch

from forex.facade import clear_facade_cache, get_available_currencies, get_rates
from forex.utils import create_template_excel


class TestFacadeExtended:
    @patch("forex.facade.TwelveDataClient")
    @patch("forex.facade.get_cache_backend")
    def test_get_rates_happy_path(self, mock_get_cache, mock_client_class):
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        mock_client = MagicMock()
        mock_client.fetch_time_series.return_value = {
            "meta": {"symbol": "USD/ZAR"},
            "values": [{"datetime": "2024-01-01", "close": "18.50"}],
        }
        mock_client_class.return_value = mock_client

        result = get_rates("key", ["USD"], "2024-01-01", "2024-01-01", ["ZAR"])
        assert not result.empty
        assert "Exchange Rate" in result.columns
        assert mock_cache.set.called

    @patch("forex.facade.TwelveDataClient")
    @patch("forex.facade.get_cache_backend")
    def test_get_rates_invert(self, mock_get_cache, mock_client_class):
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        mock_client = MagicMock()
        mock_client.fetch_time_series.return_value = {
            "meta": {"symbol": "EUR/USD"},
            "values": [{"datetime": "2024-01-01", "close": "1.10"}],
        }
        mock_client_class.return_value = mock_client

        # EUR/USD = 1.10. Inverted should be USD/EUR = 1/1.10 = 0.909091
        result = get_rates("key", ["EUR"], "2024-01-01", "2024-01-01", ["USD"], invert=True)
        assert result.iloc[0]["Currency Base"] == "USD"
        assert result.iloc[0]["Currency Source"] == "EUR"
        assert result.iloc[0]["Exchange Rate"] == round(1 / 1.10, 6)

    @patch("forex.facade.TwelveDataClient")
    @patch("forex.facade.get_cache_backend")
    def test_get_available_currencies_caching(self, mock_get_cache, mock_client_class):
        mock_cache = MagicMock()
        mock_cache.get.return_value = ["ZAR", "USD"]
        mock_get_cache.return_value = mock_cache

        result = get_available_currencies("key", "EUR")
        assert result == ["ZAR", "USD"]
        assert not mock_client_class.called

    @patch("forex.facade.get_cache_backend")
    def test_clear_facade_cache(self, mock_get_cache):
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache
        clear_facade_cache()
        assert mock_cache.clear.called


class TestUtilsExtended:
    def test_create_template_excel(self):
        content = create_template_excel()
        assert isinstance(content, bytes)
        assert len(content) > 0
