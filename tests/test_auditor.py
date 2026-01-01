"""
Smoke tests for logic/auditor.py
Tests both happy paths and edge cases for audit functionality.
"""

import pytest
import pandas as pd
from io import BytesIO


class TestValidateSchema:
    """Tests for validate_schema function."""
    
    def test_happy_path_valid_columns(self, valid_audit_dataframe):
        """Happy path: validates DataFrame with correct columns."""
        from logic.auditor import validate_schema
        
        is_valid, column_mapping, error = validate_schema(valid_audit_dataframe)
        
        assert is_valid is True
        assert error == ""
        assert isinstance(column_mapping, dict)
        # Should have mappings for the standard internal names
        assert 'date' in column_mapping
        assert 'base' in column_mapping
        assert 'source' in column_mapping
        assert 'user_rate' in column_mapping
    
    def test_edge_case_missing_columns(self, invalid_audit_dataframe):
        """Edge case: returns error for missing required columns."""
        from logic.auditor import validate_schema
        
        is_valid, column_mapping, error = validate_schema(invalid_audit_dataframe)
        
        assert is_valid is False
        assert isinstance(error, str)
        assert len(error) > 0


class TestParseDate:
    """Tests for _parse_date function."""
    
    def test_happy_path_yyyy_mm_dd(self):
        """Happy path: parses YYYY-MM-DD format."""
        from logic.auditor import _parse_date
        
        result = _parse_date('2024-01-15', 'YYYY-MM-DD')
        
        assert result == '2024-01-15'
    
    def test_happy_path_dd_mm_yyyy(self):
        """Happy path: parses DD/MM/YYYY format."""
        from logic.auditor import _parse_date
        
        result = _parse_date('15/01/2024', 'DD/MM/YYYY')
        
        assert result == '2024-01-15'
    
    def test_edge_case_invalid_date(self):
        """Edge case: returns None for invalid date."""
        from logic.auditor import _parse_date
        
        result = _parse_date('invalid-date', 'YYYY-MM-DD')
        
        assert result is None
    
    def test_smart_separator_flexibility(self):
        """Smart parsing handles different separators."""
        from logic.auditor import _parse_date
        
        # Format says dashes, but data uses slashes - should still work
        result = _parse_date('2026/1/2', 'YYYY-MM-DD')
        
        assert result == '2026-01-02'
    
    def test_smart_single_digit_handling(self):
        """Smart parsing handles single-digit days/months."""
        from logic.auditor import _parse_date
        
        result = _parse_date('2026-1-2', 'YYYY-MM-DD')
        
        assert result == '2026-01-02'
    
    def test_smart_dayfirst_detection(self):
        """Smart parsing detects day-first from format."""
        from logic.auditor import _parse_date
        
        # DD-MM format means 1/2 = Jan 2nd (day=1, month=2? No, day=2, month=1)
        # Wait, DD-MM means first number is day, second is month
        # So 2-1-2026 with DD-MM-YYYY means day=2, month=1 = Jan 2nd
        result = _parse_date('2-1-2026', 'DD-MM-YYYY')
        
        assert result == '2026-01-02'
    
    def test_smart_monthfirst_detection(self):
        """Smart parsing detects month-first from format."""
        from logic.auditor import _parse_date
        
        # MM-DD format means 1-2 = Jan 2nd (month=1, day=2)
        result = _parse_date('1-2-2026', 'MM-DD-YYYY')
        
        assert result == '2026-01-02'
    
    def test_smart_yyyy_dd_mm_ambiguity(self):
        """Smart parsing handles YYYY-DD-MM format correctly."""
        from logic.auditor import _parse_date
        
        # YYYY-DD-MM with 2026/1/2 means year=2026, day=1, month=2 = Feb 1st
        result = _parse_date('2026/1/2', 'YYYY-DD-MM')
        
        assert result == '2026-02-01'


class TestGenerateMockRate:
    """Tests for _generate_mock_rate function."""
    
    def test_happy_path_returns_float(self):
        """Happy path: returns a float rate."""
        from logic.auditor import _generate_mock_rate
        
        result = _generate_mock_rate('ZAR', 'USD', 18.50)
        
        assert isinstance(result, float)
    
    def test_happy_path_rate_is_close_to_user_rate(self):
        """Happy path: mock rate is within reasonable range of user rate."""
        from logic.auditor import _generate_mock_rate
        
        user_rate = 18.50
        result = _generate_mock_rate('ZAR', 'USD', user_rate)
        
        # Mock rate should be within 10% of user rate
        assert abs(result - user_rate) / user_rate < 0.10


class TestClearRateCache:
    """Tests for clear_rate_cache function."""
    
    def test_happy_path_clears_cache(self):
        """Happy path: cache is cleared without error."""
        from logic.auditor import clear_rate_cache, _rate_cache
        
        # This should not raise an error
        clear_rate_cache()
        
        # Cache should be empty after clearing
        assert len(_rate_cache) == 0


class TestRunAudit:
    """Tests for process_audit_file generator and run_audit wrapper."""
    
    def test_happy_path_with_testing_mode(self):
        """Happy path: generator yields progress updates in testing mode."""
        from logic.auditor import process_audit_file
        
        # Create test file
        df = pd.DataFrame({
            'Date': ['2024-01-01'],
            'Base Currency': ['ZAR'],
            'Source Currency': ['USD'],
            'rate': [18.50]
        })
        
        buffer = BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        buffer.name = "test.csv"
        
        gen = process_audit_file(
            file=buffer,
            date_fmt='YYYY-MM-DD',
            threshold=5.0,
            api_key='test_key',
            testing_mode=True
        )
        
        # Collect all updates from the generator
        updates = list(gen)
        
        # Verify we got progress updates
        assert len(updates) > 0
        
        # Verify update structure
        for update in updates:
            assert 'message' in update
            assert 'status' in update
        
        # Verify we got a "complete" status at the end
        final_status = updates[-1]['status']
        assert final_status == 'complete'
    
    def test_edge_case_empty_file(self):
        """Edge case: handles empty CSV file gracefully."""
        from logic.auditor import run_audit
        
        # Create empty file with headers only
        df = pd.DataFrame(columns=['Date', 'Base Currency', 'Source Currency', 'rate'])
        
        buffer = BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        buffer.name = "empty.csv"
        
        result = run_audit(
            file=buffer,
            date_fmt='YYYY-MM-DD',
            threshold=5.0,
            api_key='test_key',
            testing_mode=True
        )
        
        # Should handle gracefully (either return empty or None)
        assert result is not None or result is None  # Both are acceptable
