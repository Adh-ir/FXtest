"""
Centralized Configuration Module

Contains all constants and configuration values for the Forex Rate Extractor.
Consolidates hardcoded values from across the codebase for easier maintenance.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class APIConfig:
    """Configuration for Twelve Data API interactions."""

    BASE_URL: str = "https://api.twelvedata.com"
    RATE_LIMIT_REQUESTS: int = 8
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    REQUEST_TIMEOUT_SECONDS: int = 30
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_SECONDS: int = 60


@dataclass(frozen=True)
class AuditConfig:
    """Configuration for audit processing."""

    BATCH_SIZE: int = 5
    BATCH_SLEEP_SECONDS: int = 65
    DEFAULT_VARIANCE_THRESHOLD: float = 5.0


@dataclass(frozen=True)
class CacheConfig:
    """Configuration for caching behavior."""

    RATE_TTL_SECONDS: int = 1800  # 30 minutes
    CURRENCY_TTL_SECONDS: int = 86400  # 24 hours
    COOKIE_EXPIRY_DAYS: int = 7


@dataclass(frozen=True)
class UIConfig:
    """Configuration for UI constants."""

    TOP_CURRENCIES: tuple = (
        "ZAR",
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "AUD",
        "CAD",
        "CHF",
        "CNY",
        "NZD",
    )
    COOKIE_NAME: str = "twelve_data_api_key"


# Singleton instances for easy import
API_CONFIG = APIConfig()
AUDIT_CONFIG = AuditConfig()
CACHE_CONFIG = CacheConfig()
UI_CONFIG = UIConfig()
