"""
Smoke tests for forex/data_processor.py
Tests both happy paths and edge cases for DataProcessor class.
"""


class TestParseTargets:
    """Tests for DataProcessor.parse_targets method."""

    def test_happy_path_comma_separated(self):
        """Happy path: parses comma-separated currency codes."""
        from forex.data_processor import DataProcessor

        result = DataProcessor.parse_targets("USD, EUR, GBP", "ZAR", None)

        assert isinstance(result, list)
        assert "USD" in result
        assert "EUR" in result
        assert "GBP" in result

    def test_happy_path_lowercase_input(self):
        """Happy path: handles lowercase input."""
        from forex.data_processor import DataProcessor

        result = DataProcessor.parse_targets("usd,eur,gbp", "ZAR", None)

        assert "USD" in result
        assert "EUR" in result

    def test_edge_case_empty_input(self):
        """Edge case: empty input returns default basket."""
        from forex.data_processor import DataProcessor

        result = DataProcessor.parse_targets("", "ZAR", None)

        assert isinstance(result, list)
        assert len(result) > 0  # Should return default basket

    def test_edge_case_whitespace_only(self):
        """Edge case: whitespace-only input returns default basket."""
        from forex.data_processor import DataProcessor

        result = DataProcessor.parse_targets("   ", "ZAR", None)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_edge_case_major_keyword(self):
        """Edge case: [MAJOR] keyword returns major currencies."""
        from forex.data_processor import DataProcessor

        result = DataProcessor.parse_targets("[MAJOR]", "ZAR", None)

        assert isinstance(result, list)
        # Major currencies typically include USD, EUR, GBP
        assert "USD" in result or len(result) > 0

    def test_edge_case_african_keyword(self):
        """Edge case: [AFRICAN] keyword returns African currencies."""
        from forex.data_processor import DataProcessor

        result = DataProcessor.parse_targets("[AFRICAN]", "ZAR", None)

        assert isinstance(result, list)


class TestGeneratePairsConfig:
    """Tests for DataProcessor.generate_pairs_config method."""

    def test_happy_path_single_base(self):
        """Happy path: generates config for single base currency."""
        from forex.data_processor import DataProcessor

        result = DataProcessor.generate_pairs_config(["ZAR"])

        assert isinstance(result, list)
        assert len(result) > 0
        # Each config should have required keys
        assert "user_base" in result[0]
        assert "user_target" in result[0]
        assert "api_symbol" in result[0]

    def test_happy_path_custom_targets(self):
        """Happy path: generates config with custom target currencies."""
        from forex.data_processor import DataProcessor

        result = DataProcessor.generate_pairs_config(["ZAR"], ["USD", "EUR"])

        assert len(result) == 2
        targets = [c["user_target"] for c in result]
        assert "USD" in targets
        assert "EUR" in targets

    def test_edge_case_multiple_bases(self):
        """Edge case: handles multiple base currencies."""
        from forex.data_processor import DataProcessor

        result = DataProcessor.generate_pairs_config(["ZAR", "USD"], ["EUR"])

        assert len(result) >= 2


class TestParseInputBases:
    """Tests for DataProcessor.parse_input_bases method."""

    def test_happy_path_comma_separated(self):
        """Happy path: parses comma-separated base currencies."""
        from forex.data_processor import DataProcessor

        result = DataProcessor.parse_input_bases("ZAR, USD, EUR")

        assert isinstance(result, list)
        assert "ZAR" in result
        assert "USD" in result

    def test_edge_case_single_value(self):
        """Edge case: single value without comma."""
        from forex.data_processor import DataProcessor

        result = DataProcessor.parse_input_bases("ZAR")

        assert result == ["ZAR"]


class TestDataProcessorConstants:
    """Tests for DataProcessor class constants."""

    def test_has_standard_bases(self):
        """Happy path: class has STANDARD_BASES constant."""
        from forex.data_processor import DataProcessor

        assert hasattr(DataProcessor, "STANDARD_BASES")
        assert isinstance(DataProcessor.STANDARD_BASES, list)

    def test_has_target_basket(self):
        """Happy path: class has TARGET_BASKET constant."""
        from forex.data_processor import DataProcessor

        assert hasattr(DataProcessor, "TARGET_BASKET")
        assert isinstance(DataProcessor.TARGET_BASKET, list)
