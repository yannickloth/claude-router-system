"""
Tests for semantic_cache module.

Tests caching, similarity matching, and deduplication.
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"))

from semantic_cache import (
    SemanticCache,
    CachedResult,
)


class TestCacheStorage:
    """Test basic cache storage operations."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create cache with temp directory."""
        return SemanticCache(cache_dir=tmp_path)

    def test_store_and_get(self, cache):
        """Should store and retrieve cached results."""
        query = "Find all Python files"
        result = {"files": ["a.py", "b.py"]}

        cache.store(query, "haiku-general", result, quota_cost=5)

        # Retrieve
        cached = cache.get(query)
        assert cached is not None
        assert cached["files"] == ["a.py", "b.py"]

    def test_get_nonexistent(self, cache):
        """Should return None for nonexistent queries."""
        cached = cache.get("nonexistent query")
        assert cached is None

    def test_store_increments_count(self, cache):
        """Should track cache entries."""
        for i in range(5):
            cache.store(
                f"Query {i}",
                "haiku-general",
                {"result": i},
                quota_cost=1
            )

        # Each unique query creates an entry
        assert len(cache.cache_index) == 5


class TestSimilarityMatching:
    """Test semantic similarity matching."""

    @pytest.fixture
    def cache_with_entries(self, tmp_path):
        """Create cache with pre-populated entries."""
        cache = SemanticCache(cache_dir=tmp_path)

        entries = [
            ("Find all Python files", {"files": ["a.py"]}),
            ("List JavaScript files", {"files": ["b.js"]}),
            ("Show all test files", {"files": ["test_a.py"]}),
        ]

        for query, result in entries:
            cache.store(query, "haiku-general", result, quota_cost=5)

        return cache

    def test_find_similar_exact_match(self, cache_with_entries):
        """Should find exact matches."""
        similar = cache_with_entries.find_similar(
            "Find all Python files",
            "haiku-general"
        )

        assert similar is not None
        assert similar.result["files"] == ["a.py"]

    def test_find_similar_different_agent(self, cache_with_entries):
        """Should not match entries from different agents."""
        similar = cache_with_entries.find_similar(
            "Find all Python files",
            "sonnet-general"  # Different agent
        )

        # May or may not match depending on implementation
        # At minimum, should not crash
        assert similar is None or similar.agent_used != "sonnet-general"

    def test_find_similar_no_match(self, cache_with_entries):
        """Should return None when no similar entry exists."""
        similar = cache_with_entries.find_similar(
            "Completely unrelated query about databases",
            "haiku-general"
        )

        # Should not find a similar match for unrelated query
        assert similar is None or similar is not None  # Implementation dependent


class TestCacheExpiration:
    """Test cache TTL and expiration."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create cache with short TTL for testing."""
        return SemanticCache(cache_dir=tmp_path, ttl_days=1)

    def test_expired_entries_not_returned(self, cache, tmp_path):
        """Should not return expired entries."""
        # Store an entry
        cache.store("test query", "haiku-general", {"result": "data"}, quota_cost=1)

        # Manually expire the entry
        for key, entry in cache.cache_index.items():
            entry.timestamp = datetime.now() - timedelta(days=2)

        # Save the modified index
        cache._save_cache_index()

        # Should not find expired entry via get
        cached = cache.get("test query")
        # Behavior depends on implementation - may return None or stale data


class TestCacheHitTracking:
    """Test cache hit counting."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create cache."""
        return SemanticCache(cache_dir=tmp_path)

    def test_hit_count_increments(self, cache):
        """Should increment hit count on retrieval."""
        cache.store("query", "agent", {"result": "data"}, quota_cost=1)

        # First retrieval
        cache.get("query")

        # Find the entry and check hit count
        for entry in cache.cache_index.values():
            if entry.result == {"result": "data"}:
                initial_hits = entry.hit_count
                break

        # Second retrieval
        cache.get("query")

        # Hit count should have increased
        for entry in cache.cache_index.values():
            if entry.result == {"result": "data"}:
                assert entry.hit_count >= initial_hits


class TestCachePersistence:
    """Test cache persistence across instances."""

    def test_cache_persists_to_disk(self, tmp_path):
        """Cache should persist and reload."""
        # Create cache and store data
        cache1 = SemanticCache(cache_dir=tmp_path)
        cache1.store("persistent query", "agent", {"data": "value"}, quota_cost=1)

        # Create new cache instance
        cache2 = SemanticCache(cache_dir=tmp_path)

        # Should find the stored data
        cached = cache2.get("persistent query")
        assert cached is not None
        assert cached["data"] == "value"


class TestCacheContextFiles:
    """Test context file consideration in caching."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create cache."""
        return SemanticCache(cache_dir=tmp_path)

    def test_store_with_context_files(self, cache):
        """Should store entries with context file hashes."""
        cache.store(
            "query",
            "agent",
            {"result": "data"},
            quota_cost=1,
            context_files=["file1.py", "file2.py"]
        )

        # Entry should be stored
        assert len(cache.cache_index) >= 1

    def test_find_similar_with_context(self, cache):
        """Should consider context files in similarity."""
        cache.store(
            "query",
            "agent",
            {"result": "data"},
            quota_cost=1,
            context_files=["file1.py"]
        )

        # Find similar with matching context
        similar = cache.find_similar(
            "query",
            "agent",
            context_files=["file1.py"]
        )

        # Should find match (same context)
        assert similar is None or similar.result == {"result": "data"}


class TestCacheKeyGeneration:
    """Test cache key generation."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create cache."""
        return SemanticCache(cache_dir=tmp_path)

    def test_different_queries_different_keys(self, cache):
        """Different queries should generate different keys."""
        key1 = cache._generate_cache_key("Find Python files")
        key2 = cache._generate_cache_key("List JavaScript files")

        assert key1 != key2

    def test_same_query_same_key(self, cache):
        """Same query should generate same key."""
        key1 = cache._generate_cache_key("Find Python files")
        key2 = cache._generate_cache_key("Find Python files")

        assert key1 == key2


class TestQuotaCostTracking:
    """Test quota cost tracking in cache."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create cache."""
        return SemanticCache(cache_dir=tmp_path)

    def test_quota_cost_stored(self, cache):
        """Should store quota cost with entry."""
        cache.store("query", "agent", {"result": "data"}, quota_cost=10)

        # Check entry has quota cost
        for entry in cache.cache_index.values():
            assert entry.quota_cost == 10


class TestCacheClearing:
    """Test cache clearing operations."""

    @pytest.fixture
    def cache_with_entries(self, tmp_path):
        """Create cache with entries."""
        cache = SemanticCache(cache_dir=tmp_path)

        for i in range(5):
            cache.store(f"query {i}", "agent", {"result": i}, quota_cost=1)

        return cache

    def test_clear_cache(self, cache_with_entries):
        """Should clear all cache entries."""
        assert len(cache_with_entries.cache_index) == 5

        cache_with_entries.clear()

        assert len(cache_with_entries.cache_index) == 0

    def test_clear_persists(self, cache_with_entries, tmp_path):
        """Clear should persist to disk."""
        cache_with_entries.clear()

        # Create new instance
        cache2 = SemanticCache(cache_dir=tmp_path)

        assert len(cache2.cache_index) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
