"""Test Redis caching functionality."""

import pytest
from chaosmonkey.web.cache import CacheManager, get_cache


def test_cache_manager_initialization():
    """Test cache manager can be initialized."""
    cache = CacheManager()
    assert cache is not None
    # Should work even if Redis is not available (graceful fallback)
    

def test_cache_basic_operations():
    """Test basic cache operations."""
    cache = get_cache()
    
    if not cache.enabled:
        pytest.skip("Redis not available, skipping cache tests")
    
    # Test set/get
    test_key = "test:basic"
    test_value = {"message": "Hello Cache!"}
    
    assert cache.set(test_key, test_value, ttl=60)
    result = cache.get(test_key)
    assert result == test_value
    
    # Cleanup
    cache.delete(test_key)
    assert cache.get(test_key) is None


def test_cache_hash_operations():
    """Test hash-based cache operations."""
    cache = get_cache()
    
    if not cache.enabled:
        pytest.skip("Redis not available, skipping cache tests")
    
    test_hash = "test:nodes"
    
    # Set multiple fields
    cache.set_hash(test_hash, "node-1", {"name": "Node 1", "status": "ready"})
    cache.set_hash(test_hash, "node-2", {"name": "Node 2", "status": "ready"})
    
    # Get single field
    node1 = cache.get_hash(test_hash, "node-1")
    assert node1["name"] == "Node 1"
    
    # Get all fields
    all_nodes = cache.get_all_hash(test_hash)
    assert len(all_nodes) == 2
    assert "node-1" in all_nodes
    assert "node-2" in all_nodes
    
    # Delete field
    cache.delete_hash_field(test_hash, "node-1")
    assert cache.get_hash(test_hash, "node-1") is None
    
    # Cleanup
    cache.delete(test_hash)


def test_cache_pattern_clearing():
    """Test clearing cache by pattern."""
    cache = get_cache()
    
    if not cache.enabled:
        pytest.skip("Redis not available, skipping cache tests")
    
    # Create multiple keys
    cache.set("test:key1", {"data": 1})
    cache.set("test:key2", {"data": 2})
    cache.set("other:key", {"data": 3})
    
    # Clear test:* pattern
    count = cache.clear_pattern("test:*")
    assert count >= 2
    
    # Verify test keys are gone
    assert cache.get("test:key1") is None
    assert cache.get("test:key2") is None
    
    # Verify other key still exists
    assert cache.get("other:key") is not None
    
    # Cleanup
    cache.delete("other:key")


def test_cache_graceful_fallback():
    """Test cache works gracefully when Redis is unavailable."""
    # Create cache with invalid Redis URL
    cache = CacheManager(redis_url="redis://invalid-host:9999")
    
    # Should not crash, just disable caching
    assert not cache.enabled
    
    # Operations should return False/None but not crash
    assert not cache.set("key", "value")
    assert cache.get("key") is None
    assert not cache.delete("key")
    assert cache.clear_pattern("*") == 0


def test_cache_ttl():
    """Test cache TTL expiration."""
    import time
    cache = get_cache()
    
    if not cache.enabled:
        pytest.skip("Redis not available, skipping cache tests")
    
    test_key = "test:ttl"
    test_value = {"expires": "soon"}
    
    # Set with very short TTL
    cache.set(test_key, test_value, ttl=1)
    
    # Should exist immediately
    assert cache.get(test_key) == test_value
    
    # Wait for expiration
    time.sleep(2)
    
    # Should be gone
    assert cache.get(test_key) is None


if __name__ == "__main__":
    # Run basic smoke test
    print("🧪 Running cache smoke tests...")
    
    try:
        cache = get_cache()
        print(f"✅ Cache initialized (enabled: {cache.enabled})")
        
        if cache.enabled:
            # Test basic operations
            cache.set("smoke:test", {"test": "value"}, ttl=10)
            result = cache.get("smoke:test")
            assert result == {"test": "value"}
            cache.delete("smoke:test")
            print("✅ Basic operations work")
            
            # Test hash operations
            cache.set_hash("smoke:hash", "field1", {"data": "value1"})
            result = cache.get_hash("smoke:hash", "field1")
            assert result == {"data": "value1"}
            cache.delete("smoke:hash")
            print("✅ Hash operations work")
            
            print("🎉 All smoke tests passed!")
        else:
            print("⚠️  Redis not available, but graceful fallback works!")
            
    except Exception as e:
        print(f"❌ Smoke test failed: {e}")
        raise
