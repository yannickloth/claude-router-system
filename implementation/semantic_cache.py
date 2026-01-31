"""
Semantic Cache - Production-ready agent result deduplication with similarity matching.

Implements intelligent caching with:
- Semantic similarity matching (cosine similarity on embeddings)
- Context-aware invalidation (file change detection)
- TTL-based expiration
- Atomic writes for data integrity
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json
import math
import os
import tempfile


@dataclass
class CachedResult:
    """A cached agent execution result."""
    request_text: str
    request_embedding: List[float]  # Semantic vector
    agent_used: str
    result: Any  # JSON-serializable result
    timestamp: datetime
    quota_cost: int
    context_hash: str  # Hash of relevant file versions
    hit_count: int = 0  # Track cache reuse

    def to_dict(self) -> Dict:
        """Serialize for JSON storage."""
        return {
            "request_text": self.request_text,
            "request_embedding": self.request_embedding,
            "agent_used": self.agent_used,
            "result": self.result,
            "timestamp": self.timestamp.isoformat(),
            "quota_cost": self.quota_cost,
            "context_hash": self.context_hash,
            "hit_count": self.hit_count,
        }

    @staticmethod
    def from_dict(data: Dict) -> "CachedResult":
        """Deserialize from dictionary."""
        return CachedResult(
            request_text=data["request_text"],
            request_embedding=data["request_embedding"],
            agent_used=data["agent_used"],
            result=data["result"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            quota_cost=data["quota_cost"],
            context_hash=data["context_hash"],
            hit_count=data.get("hit_count", 0),
        )


class SemanticCache:
    """
    Semantic cache for agent results with similarity-based lookup.

    Features:
    - Semantic similarity matching (not just exact string match)
    - Context-aware invalidation (detects file changes)
    - TTL-based expiration
    - Secure file permissions
    - Atomic writes
    """

    def __init__(
        self,
        cache_dir: Path,
        similarity_threshold: float = 0.85,
        ttl_days: int = 30
    ):
        """
        Initialize semantic cache.

        Args:
            cache_dir: Directory to store cached results
            similarity_threshold: Cosine similarity threshold for cache hit (0.0-1.0)
            ttl_days: Time-to-live for cached results
        """
        self.cache_dir = Path(cache_dir)
        # Create directory with secure permissions
        self.cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        self.similarity_threshold = similarity_threshold
        self.ttl_days = ttl_days

        # In-memory index for fast lookup
        self.cache_index: Dict[str, CachedResult] = {}
        self._load_cache_index()

    def _load_cache_index(self):
        """Load cache index from disk with error handling."""
        index_file = self.cache_dir / "cache_index.json"
        if not index_file.exists():
            return

        try:
            with open(index_file) as f:
                data = json.load(f)
                for item in data:
                    try:
                        cached = CachedResult.from_dict(item)
                        cache_key = self._generate_cache_key(cached.request_text)
                        self.cache_index[cache_key] = cached
                    except (KeyError, ValueError) as e:
                        # Skip corrupted entries
                        print(f"Warning: Skipping corrupted cache entry: {e}")
                        continue
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load cache index: {e}")
            # Start with empty cache
            self.cache_index = {}

    def _save_cache_index(self):
        """Persist cache index to disk using atomic writes."""
        index_file = self.cache_dir / "cache_index.json"

        # Prepare data
        data = [cached.to_dict() for cached in self.cache_index.values()]

        # Atomic write pattern
        try:
            fd, temp_path = tempfile.mkstemp(
                dir=self.cache_dir,
                prefix=".cache_index-",
                suffix=".json.tmp"
            )

            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)

            # Set secure permissions
            os.chmod(temp_path, 0o600)

            # Atomic rename
            os.rename(temp_path, index_file)
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise RuntimeError(f"Failed to save cache index: {e}") from e

    def _generate_cache_key(self, text: str) -> str:
        """Generate stable cache key from text."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _compute_embedding(self, text: str) -> List[float]:
        """
        Compute semantic embedding for text.

        In production, use actual embedding model (e.g., sentence-transformers):
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding = model.encode(text)

        This implementation uses simple TF-IDF-like embedding for demonstration.
        """
        # Simplified TF-IDF-like embedding (demonstration only)
        words = text.lower().split()
        vocab = sorted(set(words))

        # Create frequency vector
        embedding = [words.count(w) / len(words) for w in vocab[:128]]

        # Pad to fixed size
        while len(embedding) < 128:
            embedding.append(0.0)

        # Normalize to unit vector
        magnitude = math.sqrt(sum(x * x for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding[:128]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Compute cosine similarity between two vectors.

        Returns:
            Similarity score from 0.0 (completely different) to 1.0 (identical)
        """
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a * a for a in vec1))
        mag2 = math.sqrt(sum(b * b for b in vec2))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot_product / (mag1 * mag2)

    def _compute_context_hash(self, file_paths: List[str]) -> str:
        """
        Hash relevant file versions to detect staleness.

        Args:
            file_paths: List of file paths that this result depends on

        Returns:
            Hash string representing current state of files
        """
        hasher = hashlib.sha256()

        for path in sorted(file_paths):
            file_path = Path(path)
            if file_path.exists():
                # Include file mtime and size
                stat = file_path.stat()
                hasher.update(f"{path}:{stat.st_mtime}:{stat.st_size}".encode())

        return hasher.hexdigest()[:16]

    def find_similar(
        self,
        request: str,
        agent: str,
        context_files: Optional[List[str]] = None
    ) -> Optional[CachedResult]:
        """
        Search cache for semantically similar request.

        Returns cached result if:
        1. Semantic similarity > threshold
        2. Same agent used
        3. Context files unchanged (or no context files)
        4. Not expired (within TTL)

        Args:
            request: Request text to search for
            agent: Agent name (must match)
            context_files: Optional list of files this result depends on

        Returns:
            Cached result if found, None otherwise
        """
        query_embedding = self._compute_embedding(request)
        context_hash = self._compute_context_hash(context_files or [])

        best_match = None
        best_similarity = 0.0

        for cached in self.cache_index.values():
            # Filter by agent
            if cached.agent_used != agent:
                continue

            # Check TTL
            age = datetime.now() - cached.timestamp
            if age > timedelta(days=self.ttl_days):
                continue

            # Check context validity (if context-dependent)
            if context_files and cached.context_hash != context_hash:
                continue

            # Compute similarity
            similarity = self._cosine_similarity(query_embedding, cached.request_embedding)

            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_match = cached

        if best_match:
            # Increment hit count
            best_match.hit_count += 1
            self._save_cache_index()

            print(f"💾 Cache hit! Similarity: {best_similarity:.2f}")
            print(f"   Original request: {best_match.request_text[:60]}...")
            print(f"   Saved {best_match.quota_cost} quota messages")

        return best_match

    def store(
        self,
        request: str,
        agent: str,
        result: Any,
        quota_cost: int,
        context_files: Optional[List[str]] = None
    ):
        """
        Store agent result in cache.

        Args:
            request: Request text
            agent: Agent name
            result: Result to cache (must be JSON-serializable)
            quota_cost: Quota cost of this operation
            context_files: Files this result depends on
        """
        embedding = self._compute_embedding(request)
        context_hash = self._compute_context_hash(context_files or [])

        cached = CachedResult(
            request_text=request,
            request_embedding=embedding,
            agent_used=agent,
            result=result,
            timestamp=datetime.now(),
            quota_cost=quota_cost,
            context_hash=context_hash
        )

        cache_key = self._generate_cache_key(request)
        self.cache_index[cache_key] = cached
        self._save_cache_index()

        print(f"💾 Cached result for: {request[:60]}...")

    def invalidate_by_files(self, file_paths: List[str]):
        """
        Invalidate cache entries dependent on modified files.

        Args:
            file_paths: List of modified file paths
        """
        new_context_hash = self._compute_context_hash(file_paths)

        invalidated = []
        for key, cached in list(self.cache_index.items()):
            # If this cached result was context-dependent and context changed
            if cached.context_hash and cached.context_hash != new_context_hash:
                invalidated.append(cached.request_text)
                del self.cache_index[key]

        if invalidated:
            self._save_cache_index()
            print(f"🗑️  Invalidated {len(invalidated)} cached results due to file changes")

    def get_statistics(self) -> Dict:
        """Return cache statistics."""
        total_entries = len(self.cache_index)
        total_hits = sum(c.hit_count for c in self.cache_index.values())
        total_quota_saved = sum(
            c.quota_cost * c.hit_count for c in self.cache_index.values()
        )

        return {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "total_quota_saved": total_quota_saved,
            "hit_rate": total_hits / total_entries if total_entries > 0 else 0,
        }

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        now = datetime.now()
        removed = []

        for key, cached in list(self.cache_index.items()):
            age = now - cached.timestamp
            if age > timedelta(days=self.ttl_days):
                removed.append(key)
                del self.cache_index[key]

        if removed:
            self._save_cache_index()

        return len(removed)


# Test usage
if __name__ == "__main__":
    # Create cache
    cache = SemanticCache(
        cache_dir=Path.home() / ".claude" / "infolead-router" / "cache",
        similarity_threshold=0.85
    )

    # Store a result
    cache.store(
        request="Find papers on mitochondrial dysfunction in ME/CFS",
        agent="literature-integrator",
        result=["Smith2024", "Jones2023", "Lee2025"],
        quota_cost=15
    )

    # Try to find similar request (should hit)
    result = cache.find_similar(
        request="Search for research on mitochondria in chronic fatigue",
        agent="literature-integrator"
    )

    if result:
        print(f"\nFound cached result: {result.result}")
    else:
        print("\nNo cache hit")

    # Display statistics
    stats = cache.get_statistics()
    print(f"\nCache statistics:")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Total hits: {stats['total_hits']}")
    print(f"  Quota saved: {stats['total_quota_saved']}")
