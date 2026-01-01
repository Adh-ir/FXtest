"""
Shared pytest fixtures for Forex Rate Extractor tests.
"""

import pytest
import pandas as pd
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure logic module is importable
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# --- Basic Fixtures ---

@pytest.fixture
def mock_api_key():
    """Provides a test API key."""
    return "test_api_key_12345"


@pytest.fixture
def sample_dataframe():
    """Provides a sample DataFrame for testing utils."""
    return pd.DataFrame({
        'Currency Base': ['ZAR', 'ZAR', 'ZAR'],
        'Currency Source': ['USD', 'EUR', 'GBP'],
        'Date': ['2024-01-01', '2024-01-01', '2024-01-01'],
        'Exchange Rate': [18.50, 20.25, 23.75]
    })


@pytest.fixture
def empty_dataframe():
    """Provides an empty DataFrame with standard columns."""
    return pd.DataFrame(columns=['Currency Base', 'Currency Source', 'Date', 'Exchange Rate'])


@pytest.fixture
def dataframe_with_special_chars():
    """Provides a DataFrame with special characters for encoding tests."""
    return pd.DataFrame({
        'Currency Base': ['ZAR'],
        'Currency Source': ['USD'],
        'Note': ['Rate includes 5% markup & fees'],
        'Exchange Rate': [18.50]
    })


# --- Mocked API Client Fixtures ---

@pytest.fixture
def mock_twelve_data_client():
    """Provides a mocked TwelveDataClient."""
    mock_client = MagicMock()
    
    # Mock fetch_time_series response
    mock_client.fetch_time_series.return_value = {
        'meta': {
            'symbol': 'USD/ZAR',
            'interval': '1day',
            'currency_base': 'USD',
            'currency_quote': 'ZAR'
        },
        'values': [
            {'datetime': '2024-01-01', 'open': '18.45', 'high': '18.60', 'low': '18.40', 'close': '18.50'},
            {'datetime': '2024-01-02', 'open': '18.50', 'high': '18.70', 'low': '18.45', 'close': '18.65'}
        ]
    }
    
    # Mock fetch_exchange_rate response
    mock_client.fetch_exchange_rate.return_value = {
        'symbol': 'USD/ZAR',
        'rate': 18.50,
        'timestamp': 1704067200
    }
    
    # Mock fetch_available_pairs response
    mock_client.fetch_available_pairs.return_value = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD']
    
    return mock_client


@pytest.fixture
def mock_api_response_error():
    """Provides a mock error response from the API."""
    return {
        'code': 400,
        'message': 'Invalid API key',
        'status': 'error'
    }


# --- Audit Fixtures ---

@pytest.fixture
def valid_audit_dataframe():
    """Provides a DataFrame with valid audit schema."""
    return pd.DataFrame({
        'Date': ['2024-01-01', '2024-01-02'],
        'Base Currency': ['ZAR', 'ZAR'],
        'Source Currency': ['USD', 'EUR'],
        'rate': [18.50, 20.25]
    })


@pytest.fixture
def invalid_audit_dataframe():
    """Provides a DataFrame with missing required columns."""
    return pd.DataFrame({
        'SomeColumn': ['value1', 'value2'],
        'AnotherColumn': [1, 2]
    })
