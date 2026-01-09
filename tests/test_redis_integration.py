"""
Redis Integration Tests

End-to-end tests for the RedisCache implementation using testcontainers.
These tests spin up a real Redis container to verify cache behavior.

Run with: pytest tests/test_redis_integration.py -v
Requires: Docker running locally
"""

import time

import pytest

# Check if Docker is available before running tests
try:
    import docker

    client = docker.from_env()
    client.ping()
    DOCKER_AVAILABLE = True
except Exception:
    DOCKER_AVAILABLE = False

# Skip all tests in this module if Docker is not running
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker is not running or not available"),
]


class TestRedisIntegration:
    """
    Integration tests for RedisCache using a real Redis container.

    These tests verify:
    - Basic CRUD operations (get, set, delete, clear)
    - TTL expiration behavior
    - JSON serialization/deserialization
    - Key namespacing (forex:* prefix)
    """

    @pytest.fixture(scope="class")
    def redis_container(self):
        """
        Spin up a Redis container for the test class.

        Uses testcontainers to manage container lifecycle automatically.
        Container is shared across all tests in this class for efficiency.
        """
        if not DOCKER_AVAILABLE:
            pytest.skip("Docker is not running or not available")

        from testcontainers.redis import RedisContainer

        with RedisContainer("redis:7-alpine") as redis:
            yield redis

    @pytest.fixture
    def redis_cache(self, redis_container):
        """
        Create a RedisCache instance connected to the test container.

        Clears cache before each test for isolation.
        """
        from forex.cache import RedisCache, reset_cache_backend

        # Reset singleton to ensure clean state
        reset_cache_backend()

        # Create cache connected to test container
        host = redis_container.get_container_host_ip()
        port = redis_container.get_exposed_port(6379)
        url = f"redis://{host}:{port}/0"
        cache = RedisCache(redis_url=url)

        # Clear any existing data
        cache.clear()

        yield cache

        # Cleanup after test
        cache.clear()

    @pytest.fixture
    def redis_client(self, redis_container):
        """Direct Redis client for verification."""
        import redis

        host = redis_container.get_container_host_ip()
        port = redis_container.get_exposed_port(6379)
        return redis.Redis(host=host, port=int(port), decode_responses=True)

    # --- Basic CRUD Tests ---

    def test_set_and_get_string(self, redis_cache):
        """Test basic string storage and retrieval."""
        redis_cache.set("test_key", "test_value", ttl_seconds=60)
        result = redis_cache.get("test_key")

        assert result == "test_value"

    def test_set_and_get_dict(self, redis_cache):
        """Test dictionary storage with JSON serialization."""
        data = {"rate": 18.5, "currency": "ZAR", "pairs": ["USD", "EUR"]}

        redis_cache.set("complex_data", data, ttl_seconds=60)
        result = redis_cache.get("complex_data")

        assert result == data
        assert result["rate"] == 18.5
        assert result["pairs"] == ["USD", "EUR"]

    def test_set_and_get_list(self, redis_cache):
        """Test list storage with JSON serialization."""
        currencies = ["USD", "EUR", "GBP", "JPY"]

        redis_cache.set("currencies", currencies, ttl_seconds=60)
        result = redis_cache.get("currencies")

        assert result == currencies

    def test_get_nonexistent_key(self, redis_cache):
        """Test that getting a nonexistent key returns None."""
        result = redis_cache.get("does_not_exist")

        assert result is None

    def test_delete_key(self, redis_cache):
        """Test key deletion."""
        redis_cache.set("to_delete", "value", ttl_seconds=60)
        assert redis_cache.get("to_delete") == "value"

        redis_cache.delete("to_delete")

        assert redis_cache.get("to_delete") is None

    def test_clear_all_keys(self, redis_cache, redis_client):
        """Test clearing all forex-namespaced keys."""
        # Set multiple keys
        redis_cache.set("key1", "value1", ttl_seconds=60)
        redis_cache.set("key2", "value2", ttl_seconds=60)
        redis_cache.set("key3", "value3", ttl_seconds=60)

        # Verify they exist
        assert redis_cache.get("key1") == "value1"
        assert redis_cache.get("key2") == "value2"

        # Clear all
        redis_cache.clear()

        # Verify all cleared
        assert redis_cache.get("key1") is None
        assert redis_cache.get("key2") is None
        assert redis_cache.get("key3") is None

    # --- TTL Expiration Tests ---

    def test_ttl_expiration(self, redis_cache):
        """Test that values expire after TTL."""
        redis_cache.set("expiring_key", "value", ttl_seconds=1)

        # Should exist immediately
        assert redis_cache.get("expiring_key") == "value"

        # Wait for expiration
        time.sleep(1.5)

        # Should be gone
        assert redis_cache.get("expiring_key") is None

    def test_ttl_not_expired(self, redis_cache):
        """Test that values persist within TTL window."""
        redis_cache.set("persistent_key", "value", ttl_seconds=60)

        # Should still exist after small delay
        time.sleep(0.5)

        assert redis_cache.get("persistent_key") == "value"

    # --- Namespace Tests ---

    def test_key_namespacing(self, redis_cache, redis_client):
        """Test that keys are properly namespaced with 'forex:' prefix."""
        redis_cache.set("my_key", "my_value", ttl_seconds=60)

        # Check raw Redis to verify namespace
        raw_value = redis_client.get("forex:my_key")

        assert raw_value is not None
        # Value should be JSON-encoded
        assert "my_value" in raw_value

    def test_clear_only_namespaced_keys(self, redis_cache, redis_client):
        """Test that clear only removes forex-namespaced keys."""
        # Set forex key via cache
        redis_cache.set("forex_key", "forex_value", ttl_seconds=60)

        # Set non-forex key directly in Redis
        redis_client.set("other:key", "other_value")

        # Clear forex keys
        redis_cache.clear()

        # Forex key should be gone
        assert redis_cache.get("forex_key") is None

        # Non-forex key should remain
        assert redis_client.get("other:key") == "other_value"

        # Cleanup
        redis_client.delete("other:key")

    # --- Error Handling Tests ---

    def test_serialization_of_nested_structures(self, redis_cache):
        """Test complex nested data structures."""
        data = {
            "rates": [
                {"date": "2024-01-01", "rate": 18.5, "base": "USD"},
                {"date": "2024-01-02", "rate": 18.6, "base": "USD"},
            ],
            "metadata": {
                "source": "TwelveData",
                "cached_at": "2024-01-02T12:00:00",
            },
        }

        redis_cache.set("nested_data", data, ttl_seconds=60)
        result = redis_cache.get("nested_data")

        assert result == data
        assert len(result["rates"]) == 2
        assert result["rates"][0]["rate"] == 18.5

    def test_overwrite_existing_key(self, redis_cache):
        """Test that setting an existing key overwrites the value."""
        redis_cache.set("overwrite_key", "original", ttl_seconds=60)
        assert redis_cache.get("overwrite_key") == "original"

        redis_cache.set("overwrite_key", "updated", ttl_seconds=60)
        assert redis_cache.get("overwrite_key") == "updated"


class TestRedisCacheBackendFactory:
    """
    Test the get_cache_backend factory with Redis.
    """

    @pytest.fixture(scope="class")
    def redis_container(self):
        """Spin up a Redis container for the test class."""
        if not DOCKER_AVAILABLE:
            pytest.skip("Docker is not running or not available")

        from testcontainers.redis import RedisContainer

        with RedisContainer("redis:7-alpine") as redis:
            yield redis

    def test_force_redis_backend(self, redis_container, monkeypatch):
        """Test forcing Redis backend via environment variable."""
        from forex.cache import get_cache_backend, reset_cache_backend

        reset_cache_backend()

        # Set environment to use Redis
        host = redis_container.get_container_host_ip()
        port = redis_container.get_exposed_port(6379)
        url = f"redis://{host}:{port}/0"
        monkeypatch.setenv("REDIS_URL", url)
        monkeypatch.setenv("CACHE_BACKEND", "redis")

        cache = get_cache_backend()

        # Verify it's a Redis cache (has _client attribute)
        assert hasattr(cache, "_client")

        # Test basic operation
        cache.set("factory_test", "value", ttl_seconds=30)
        assert cache.get("factory_test") == "value"

        # Cleanup
        cache.clear()
        reset_cache_backend()

    def test_force_memory_backend(self, monkeypatch):
        """Test forcing in-memory backend via parameter."""
        from forex.cache import InMemoryCache, get_cache_backend, reset_cache_backend

        reset_cache_backend()

        cache = get_cache_backend(force_backend="memory")

        assert isinstance(cache, InMemoryCache)

        reset_cache_backend()
