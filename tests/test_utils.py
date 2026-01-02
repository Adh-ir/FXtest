"""
Smoke tests for forex/utils.py
Tests both happy paths and edge cases for DataFrame conversion utilities.
"""

import pandas as pd


class TestConvertDfToCsv:
    """Tests for convert_df_to_csv function."""

    def test_happy_path_returns_bytes(self, sample_dataframe):
        """Happy path: should return bytes representing valid CSV."""
        from forex.utils import convert_df_to_csv

        result = convert_df_to_csv(sample_dataframe)

        assert isinstance(result, bytes)
        # Decode and check CSV structure
        csv_content = result.decode("utf-8")
        lines = csv_content.strip().split("\n")
        assert len(lines) == 4  # Header + 3 data rows
        assert "Currency Base" in lines[0]
        assert "ZAR" in lines[1]

    def test_edge_case_empty_dataframe(self, empty_dataframe):
        """Edge case: empty DataFrame should return headers only."""
        from forex.utils import convert_df_to_csv

        result = convert_df_to_csv(empty_dataframe)

        csv_content = result.decode("utf-8")
        lines = csv_content.strip().split("\n")
        assert len(lines) == 1  # Only header row
        assert "Currency Base" in lines[0]

    def test_edge_case_special_characters(self, dataframe_with_special_chars):
        """Edge case: special characters should be properly encoded."""
        from forex.utils import convert_df_to_csv

        result = convert_df_to_csv(dataframe_with_special_chars)

        csv_content = result.decode("utf-8")
        assert "5% markup & fees" in csv_content


class TestConvertDfToExcel:
    """Tests for convert_df_to_excel function."""

    def test_happy_path_returns_bytes(self, sample_dataframe):
        """Happy path: should return bytes representing valid Excel file."""
        from forex.utils import convert_df_to_excel

        result = convert_df_to_excel(sample_dataframe)

        assert isinstance(result, bytes)
        # Excel files start with PK (ZIP signature)
        assert result[:2] == b"PK"

    def test_edge_case_empty_dataframe(self, empty_dataframe):
        """Edge case: empty DataFrame should produce valid Excel bytes."""
        from forex.utils import convert_df_to_excel

        result = convert_df_to_excel(empty_dataframe)

        assert isinstance(result, bytes)
        assert result[:2] == b"PK"

    def test_edge_case_can_read_back(self, sample_dataframe):
        """Edge case: Excel output should be readable back into DataFrame."""
        import io

        from forex.utils import convert_df_to_excel

        result = convert_df_to_excel(sample_dataframe)

        # Read the Excel bytes back into a DataFrame
        df_read = pd.read_excel(io.BytesIO(result), engine="openpyxl")
        assert len(df_read) == 3
        assert list(df_read.columns) == list(sample_dataframe.columns)
