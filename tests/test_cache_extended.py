from forex.cache import InMemoryCache, get_cache_backend, reset_cache_backend


class TestInMemoryCacheExtended:
    def test_get_expired_key(self):
        cache = InMemoryCache()
        cache.set("key", "value", ttl_seconds=-1)
        assert cache.get("key") is None
        assert "key" not in cache._cache

    def test_delete_key(self):
        cache = InMemoryCache()
        cache.set("key", "value")
        cache.delete("key")
        assert cache.get("key") is None

    def test_clear_cache(self):
        cache = InMemoryCache()
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_get_cache_backend_memory(self):
        reset_cache_backend()
        cache = get_cache_backend(force_backend="memory")
        assert isinstance(cache, InMemoryCache)

    def test_reset_cache_backend(self):
        cache = get_cache_backend(force_backend="memory")
        cache.set("test", "data")
        reset_cache_backend()
        # New instance should be empty
        new_cache = get_cache_backend(force_backend="memory")
        assert new_cache.get("test") is None
