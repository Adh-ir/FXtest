from unittest.mock import MagicMock

import pytest

# --- Mocking Examples & Patterns ---


@pytest.fixture
def mock_api_client():
    """
    Example fixture for mocking an external API client.
    Usage: def test_fetch_data(mock_api_client): ...
    """
    mock = MagicMock()
    # Configure default behavior
    mock.get_rates.return_value = {"USD": 1.0, "EUR": 0.85}
    return mock


@pytest.fixture
def mock_db_connection():
    """
    Example fixture for mocking a database connection.
    Ensures tests don't touch real DB.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


@pytest.fixture
def sample_data_file(tmp_path):
    """
    Creates a temporary sample file for file I/O testing.
    """
    d = tmp_path / "data"
    d.mkdir()
    p = d / "test.csv"
    p.write_text("Date,Open,High,Low,Close\n2023-01-01,1.0,1.1,0.9,1.0")
    return p


# --- Global Configuration ---


@pytest.fixture(autouse=True)
def no_requests(monkeypatch):
    """
    Guardrail: Prevent ANY real HTTP requests during tests.
    If code tries to call requests.get, it will fail.
    """
    monkeypatch.delattr("requests.sessions.Session.request", raising=False)


@pytest.fixture
def mock_api_key():
    return "test_api_key_12345"


@pytest.fixture
def valid_audit_dataframe():
    import pandas as pd

    return pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-02"],
            "Base Currency": ["USD", "EUR"],
            "Source Currency": ["EUR", "GBP"],
            "User Rate": [0.92, 0.86],
        }
    )


@pytest.fixture
def invalid_audit_dataframe():
    import pandas as pd

    return pd.DataFrame(
        {
            "Values": [1, 2, 3]  # Missing required columns
        }
    )


@pytest.fixture
def sample_dataframe():
    import pandas as pd

    return pd.DataFrame(
        {
            "Currency Base": ["USD", "EUR", "GBP"],
            "Currency Source": ["ZAR", "USD", "EUR"],
            "Date": ["2023-01-01", "2023-01-02", "2023-01-03"],
            "Exchange Rate": [18.5, 1.1, 0.85],
        }
    )


@pytest.fixture
def empty_dataframe():
    import pandas as pd

    return pd.DataFrame(columns=["Currency Base", "Currency Source", "Date", "Exchange Rate"])


@pytest.fixture
def dataframe_with_special_chars():
    import pandas as pd

    return pd.DataFrame(
        {
            "Currency Base": ["USD"],
            "Currency Source": ["ZAR"],
            "Date": ["2023-01-01"],
            "Exchange Rate": [18.5],
            "Notes": ["5% markup & fees"],
        }
    )
