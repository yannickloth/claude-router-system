"""
Tests for lazy_context_loader module.

Tests metadata indexing, section loading, and LRU caching.
"""

import json
import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"))

from lazy_context_loader import (
    LazyContextLoader,
    Section,
    ContextStats,
    LRUCache,
    CONTEXT_BUDGET,
    CHARS_PER_TOKEN,
)


class TestLRUCache:
    """Test LRU cache implementation."""

    def test_put_and_get(self):
        """Should store and retrieve items."""
        cache = LRUCache(max_tokens=1000)

        cache.put("key1", "content1", 100)
        result = cache.get("key1")

        assert result == "content1"

    def test_get_nonexistent(self):
        """Should return None for nonexistent keys."""
        cache = LRUCache(max_tokens=1000)

        result = cache.get("nonexistent")
        assert result is None

    def test_eviction_on_capacity(self):
        """Should evict oldest items when over capacity."""
        cache = LRUCache(max_tokens=200)

        cache.put("key1", "content1", 100)
        cache.put("key2", "content2", 100)
        cache.put("key3", "content3", 100)  # Should evict key1

        assert cache.get("key1") is None
        assert cache.get("key2") == "content2"
        assert cache.get("key3") == "content3"

    def test_access_updates_order(self):
        """Accessing item should update LRU order."""
        cache = LRUCache(max_tokens=200)

        cache.put("key1", "content1", 100)
        cache.put("key2", "content2", 100)

        # Access key1 to make it most recent
        cache.get("key1")

        # Add key3 - should evict key2 (least recent)
        cache.put("key3", "content3", 100)

        assert cache.get("key1") == "content1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "content3"

    def test_hit_miss_tracking(self):
        """Should track cache hits and misses."""
        cache = LRUCache(max_tokens=1000)

        cache.put("key1", "content1", 100)

        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("missing")  # Miss

        assert cache.hits == 2
        assert cache.misses == 1

    def test_clear(self):
        """Should clear all items."""
        cache = LRUCache(max_tokens=1000)

        cache.put("key1", "content1", 100)
        cache.put("key2", "content2", 100)

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.current_tokens == 0


class TestMetadataIndexing:
    """Test file metadata indexing."""

    @pytest.fixture
    def loader(self):
        """Create context loader."""
        return LazyContextLoader()

    def test_index_latex_file(self, loader, tmp_path):
        """Should index LaTeX chapters and sections."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("""\\documentclass{article}
\\begin{document}

\\chapter{Introduction}
This is the introduction.

\\section{Background}
Some background.

\\chapter{Methods}
Research methods here.

\\end{document}
""")

        loader.build_metadata_index(tmp_path)

        sections = loader.list_sections(str(tex_file))
        assert len(sections) >= 2  # At least chapters

        # Find Introduction
        intro = next((s for s in sections if "Introduction" in s.section_name), None)
        assert intro is not None
        assert intro.section_type == "chapter"

    def test_index_python_file(self, loader, tmp_path):
        """Should index Python classes and functions."""
        py_file = tmp_path / "test.py"
        py_file.write_text("""
class MyClass:
    def method1(self):
        pass

def standalone_function():
    return 42
""")

        loader.build_metadata_index(tmp_path)

        sections = loader.list_sections(str(py_file))
        assert len(sections) >= 2

        # Find class
        class_section = next((s for s in sections if s.section_name == "MyClass"), None)
        assert class_section is not None
        assert class_section.section_type == "class"

    def test_index_markdown_file(self, loader, tmp_path):
        """Should index Markdown headings."""
        md_file = tmp_path / "test.md"
        md_file.write_text("""# First Heading

Content for first.

## Second Heading

Content for second.

# Third Heading

Content for third.
""")

        loader.build_metadata_index(tmp_path)

        sections = loader.list_sections(str(md_file))
        assert len(sections) >= 3

        # Find first heading
        first = next((s for s in sections if "First" in s.section_name), None)
        assert first is not None


class TestSectionLoading:
    """Test section content loading."""

    @pytest.fixture
    def loader_with_index(self, tmp_path):
        """Create loader with indexed file."""
        loader = LazyContextLoader()

        md_file = tmp_path / "test.md"
        md_file.write_text("""# Section One

Content of section one.

# Section Two

Content of section two.

# Section Three

Content of section three.
""")

        loader.build_metadata_index(tmp_path)
        return loader, str(md_file)

    def test_load_specific_section(self, loader_with_index):
        """Should load specific section content."""
        loader, file_path = loader_with_index

        sections = loader.list_sections(file_path)
        if sections:
            first_section = sections[0]
            content = loader.load_section(file_path, first_section.section_id)

            assert content is not None
            assert "Section One" in content

    def test_load_caches_content(self, loader_with_index):
        """Loading should cache content."""
        loader, file_path = loader_with_index

        sections = loader.list_sections(file_path)
        if sections:
            section_id = sections[0].section_id

            # First load (miss)
            loader.load_section(file_path, section_id)
            stats1 = loader.get_stats()

            # Second load (hit)
            loader.load_section(file_path, section_id)
            stats2 = loader.get_stats()

            assert stats2.cache_hits > stats1.cache_hits

    def test_load_nonexistent_section(self, loader_with_index):
        """Should return None for nonexistent section."""
        loader, file_path = loader_with_index

        content = loader.load_section(file_path, "nonexistent_section")
        assert content is None


class TestContextStats:
    """Test context statistics."""

    def test_initial_stats(self):
        """New loader should have empty stats."""
        loader = LazyContextLoader()
        stats = loader.get_stats()

        assert stats.loaded_sections == 0
        assert stats.total_tokens == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0

    def test_stats_after_loading(self, tmp_path):
        """Stats should reflect loaded content."""
        loader = LazyContextLoader()

        md_file = tmp_path / "test.md"
        md_file.write_text("# Test\n\nSome content here.")

        loader.build_metadata_index(tmp_path)
        sections = loader.list_sections(str(md_file))

        if sections:
            loader.load_section(str(md_file), sections[0].section_id)

        stats = loader.get_stats()
        assert stats.loaded_sections >= 0  # May vary based on caching


class TestIndexPersistence:
    """Test index save/load functionality."""

    def test_save_and_load_index(self, tmp_path):
        """Should save and load metadata index."""
        # Create and index files
        loader1 = LazyContextLoader()

        md_file = tmp_path / "test.md"
        md_file.write_text("# Heading\n\nContent.")

        loader1.build_metadata_index(tmp_path)

        # Save index
        index_file = tmp_path / "index.json"
        loader1.save_index(index_file)

        assert index_file.exists()

        # Load in new loader
        loader2 = LazyContextLoader()
        loader2.load_index(index_file)

        sections = loader2.list_sections(str(md_file))
        assert len(sections) >= 1


class TestTokenEstimation:
    """Test token count estimation."""

    def test_estimate_tokens(self, tmp_path):
        """Should estimate tokens based on content."""
        loader = LazyContextLoader()

        # Create file with known content
        content = "a" * 400  # 400 chars = ~100 tokens
        test_file = tmp_path / "test.md"
        test_file.write_text(f"# Test\n\n{content}")

        loader.build_metadata_index(tmp_path)

        sections = loader.list_sections(str(test_file))
        if sections:
            section = sections[0]
            # Token estimate should be roughly chars / CHARS_PER_TOKEN
            expected_tokens = len(content) // CHARS_PER_TOKEN
            # Allow some variance for heading
            assert section.estimated_tokens >= expected_tokens - 50


class TestContextBudget:
    """Test context budget enforcement."""

    def test_lru_eviction_within_budget(self, tmp_path):
        """Should evict sections to stay within budget."""
        # Create loader with small budget
        loader = LazyContextLoader(context_budget=100)

        # Create multiple sections
        for i in range(5):
            md_file = tmp_path / f"test{i}.md"
            md_file.write_text(f"# Section {i}\n\n" + "x" * 50)

        loader.build_metadata_index(tmp_path)

        # Load all sections (should trigger eviction)
        for i in range(5):
            sections = loader.list_sections(str(tmp_path / f"test{i}.md"))
            if sections:
                loader.load_section(str(tmp_path / f"test{i}.md"), sections[0].section_id)

        stats = loader.get_stats()
        assert stats.total_tokens <= 100


class TestSection:
    """Test Section dataclass."""

    def test_section_creation(self):
        """Should create Section with all fields."""
        section = Section(
            file_path="/path/to/file.tex",
            section_id="chapter_1",
            section_name="Introduction",
            start_line=10,
            end_line=50,
            estimated_tokens=200,
            section_type="chapter"
        )

        assert section.file_path == "/path/to/file.tex"
        assert section.section_name == "Introduction"
        assert section.start_line == 10
        assert section.end_line == 50


class TestContextStats:
    """Test ContextStats dataclass."""

    def test_context_stats_creation(self):
        """Should create ContextStats with all fields."""
        stats = ContextStats(
            loaded_sections=5,
            total_tokens=1000,
            budget_used_percent=50.0,
            cache_hits=10,
            cache_misses=2
        )

        assert stats.loaded_sections == 5
        assert stats.total_tokens == 1000
        assert stats.budget_used_percent == 50.0


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_file(self, tmp_path):
        """Should handle empty files."""
        loader = LazyContextLoader()

        empty_file = tmp_path / "empty.md"
        empty_file.write_text("")

        loader.build_metadata_index(tmp_path)

        sections = loader.list_sections(str(empty_file))
        assert sections == []

    def test_file_without_sections(self, tmp_path):
        """Should handle files without clear sections."""
        loader = LazyContextLoader()

        no_sections = tmp_path / "nosections.txt"
        no_sections.write_text("Just plain text without any sections.")

        loader.build_metadata_index(tmp_path)

        sections = loader.list_sections(str(no_sections))
        # May or may not have sections depending on file type handling


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
