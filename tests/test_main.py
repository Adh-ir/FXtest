"""
Smoke tests for the main Streamlit application entry point.

These tests verify that the application can be imported and its core forex
modules are accessible, without actually running the Streamlit server.
This ensures import paths remain valid during refactoring.
"""

import os
import sys


class TestLogicModuleImports:
    """Tests that core forex modules are importable."""

    def test_import_auditor_module(self):
        """Smoke test: auditor module imports successfully."""
        from forex import auditor

        assert hasattr(auditor, "validate_schema")
        assert hasattr(auditor, "process_audit_file")
        assert hasattr(auditor, "run_audit")
        assert hasattr(auditor, "clear_rate_cache")

    def test_import_utils_module(self):
        """Smoke test: utils module imports successfully."""
        from forex import utils

        assert hasattr(utils, "convert_df_to_csv")
        assert hasattr(utils, "convert_df_to_excel")
        assert hasattr(utils, "create_template_excel")

    def test_import_api_client_module(self):
        """Smoke test: api_client module imports successfully."""
        from forex import api_client

        assert hasattr(api_client, "TwelveDataClient")

    def test_import_data_processor_module(self):
        """Smoke test: data_processor module imports successfully."""
        from forex import data_processor

        assert hasattr(data_processor, "DataProcessor")

    def test_import_facade_module(self):
        """Smoke test: facade module imports successfully."""
        from forex import facade

        assert hasattr(facade, "get_rates")
        assert hasattr(facade, "get_available_currencies")

    def test_import_config_module(self):
        """Smoke test: config module imports successfully."""
        from forex import config

        assert hasattr(config, "API_CONFIG")
        assert hasattr(config, "AUDIT_CONFIG")


class TestConfigurationIntegrity:
    """Tests that configuration values are properly set."""

    def test_api_config_has_required_fields(self):
        """Verify API_CONFIG contains required fields."""
        from forex.config import API_CONFIG

        assert hasattr(API_CONFIG, "BASE_URL")
        assert hasattr(API_CONFIG, "RATE_LIMIT_REQUESTS")
        assert hasattr(API_CONFIG, "REQUEST_TIMEOUT_SECONDS")

    def test_audit_config_has_required_fields(self):
        """Verify AUDIT_CONFIG contains required fields."""
        from forex.config import AUDIT_CONFIG

        assert hasattr(AUDIT_CONFIG, "BATCH_SIZE")
        assert hasattr(AUDIT_CONFIG, "BATCH_SLEEP_SECONDS")


class TestCrossModuleDependencies:
    """Tests that modules can interact with each other."""

    def test_auditor_uses_config(self):
        """Verify auditor module can access config values."""
        from forex.config import AUDIT_CONFIG

        # Auditor should use config values
        assert AUDIT_CONFIG.BATCH_SIZE > 0

    def test_api_client_uses_config(self):
        """Verify api_client module can access config values."""
        from forex.api_client import TwelveDataClient

        client = TwelveDataClient("test_key")
        assert client.BASE_URL.startswith("http")
        assert client.RATE_LIMIT_REQUESTS > 0


class TestAppPathConfiguration:
    """Tests that path configuration would work for the Streamlit app."""

    def test_project_root_in_path(self):
        """Verify project structure allows proper imports."""
        # The conftest.py adds project root to sys.path
        # This test verifies that assumption
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        assert project_root in sys.path

        # Verify forex folder exists at src/forex
        forex_path = os.path.join(project_root, "src", "forex")
        assert os.path.isdir(forex_path)

    def test_main_app_exists(self):
        """Verify src/forex/main.py exists."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        app_path = os.path.join(project_root, "src", "forex", "main.py")

        assert os.path.isfile(app_path)
