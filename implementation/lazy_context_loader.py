"""
Lazy Context Loader - Advanced context management with LRU caching

Implements section-level file loading with metadata indexing to minimize
context overhead while maintaining high signal-to-noise ratio.

CLI Usage:
    # Build metadata index for a project
    python3 lazy_context_loader.py index /path/to/project

    # Load specific section
    python3 lazy_context_loader.py load /path/to/file.tex chapter3

    # Check context budget
    python3 lazy_context_loader.py budget

Change Driver: CONTEXT_OPTIMIZATION
Changes when: Context management strategies evolve
"""

import os
import re
import sys
import json
from collections import OrderedDict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


# Context budget limits (tokens)
CONTEXT_BUDGET = 50000      # 50k for file context
CONVERSATION_BUDGET = 150000  # 150k for conversation history
TOTAL_BUDGET = 200000        # Total Claude Code limit

# Rough token estimation (4 chars per token average)
CHARS_PER_TOKEN = 4


@dataclass
class Section:
    """File section metadata."""
    file_path: str
    section_id: str
    section_name: str
    start_line: int
    end_line: int
    estimated_tokens: int
    section_type: str  # 'chapter', 'function', 'heading', etc.


@dataclass
class ContextStats:
    """Context usage statistics."""
    loaded_sections: int
    total_tokens: int
    budget_used_percent: float
    cache_hits: int
    cache_misses: int


class LRUCache:
    """Simple LRU cache for loaded sections."""

    def __init__(self, max_tokens: int):
        """Initialize LRU cache.

        Args:
            max_tokens: Maximum tokens to keep in cache
        """
        self.max_tokens = max_tokens
        self.cache: OrderedDict[str, Tuple[str, int]] = OrderedDict()
        self.current_tokens = 0
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[str]:
        """Get item from cache, updating access order.

        Args:
            key: Cache key

        Returns:
            Cached content or None if not found
        """
        if key in self.cache:
            self.hits += 1
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            content, tokens = self.cache[key]
            return content
        else:
            self.misses += 1
            return None

    def put(self, key: str, content: str, tokens: int) -> None:
        """Add item to cache, evicting if necessary.

        Args:
            key: Cache key
            content: Content to cache
            tokens: Token count for content
        """
        # Remove if already exists
        if key in self.cache:
            _, old_tokens = self.cache[key]
            self.current_tokens -= old_tokens
            del self.cache[key]

        # Evict oldest items until we have space
        while self.current_tokens + tokens > self.max_tokens and self.cache:
            oldest_key, (_, oldest_tokens) = self.cache.popitem(last=False)
            self.current_tokens -= oldest_tokens

        # Add new item
        self.cache[key] = (content, tokens)
        self.current_tokens += tokens

    def clear(self) -> None:
        """Clear entire cache."""
        self.cache.clear()
        self.current_tokens = 0


class LazyContextLoader:
    """Load file sections on-demand with LRU caching."""

    def __init__(self, context_budget: int = CONTEXT_BUDGET):
        """Initialize lazy context loader.

        Args:
            context_budget: Maximum tokens for context
        """
        self.context_budget = context_budget
        self.cache = LRUCache(context_budget)
        self.metadata_index: Dict[str, List[Section]] = {}
        self.index_file: Optional[Path] = None

    def build_metadata_index(self, project_root: Path) -> None:
        """Build metadata index for all files in project.

        Args:
            project_root: Root directory of project
        """
        self.metadata_index = {}

        # Index LaTeX files
        for tex_file in project_root.rglob("*.tex"):
            sections = self._index_latex_file(tex_file)
            if sections:
                self.metadata_index[str(tex_file)] = sections

        # Index Python files
        for py_file in project_root.rglob("*.py"):
            sections = self._index_python_file(py_file)
            if sections:
                self.metadata_index[str(py_file)] = sections

        # Index Markdown files
        for md_file in project_root.rglob("*.md"):
            sections = self._index_markdown_file(md_file)
            if sections:
                self.metadata_index[str(md_file)] = sections

    def _index_latex_file(self, file_path: Path) -> List[Section]:
        """Index LaTeX file by chapters and sections.

        Args:
            file_path: Path to LaTeX file

        Returns:
            List of section metadata
        """
        sections = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            current_section = None
            section_start = 0

            for i, line in enumerate(lines, start=1):
                # Match \chapter, \section, \subsection, etc.
                match = re.match(r'\\(chapter|section|subsection)\{([^}]+)\}', line)

                if match:
                    # Save previous section if exists
                    if current_section:
                        sections.append(current_section)

                    section_type = match.group(1)
                    section_name = match.group(2)
                    section_id = f"{section_type}_{i}"

                    # Estimate tokens (will be refined when loaded)
                    estimated_tokens = 0

                    current_section = Section(
                        file_path=str(file_path),
                        section_id=section_id,
                        section_name=section_name,
                        start_line=i,
                        end_line=i,  # Will be updated
                        estimated_tokens=estimated_tokens,
                        section_type=section_type
                    )
                    section_start = i

                elif current_section:
                    # Update end line
                    current_section.end_line = i

            # Add last section
            if current_section:
                sections.append(current_section)

        except Exception as e:
            print(f"Warning: Failed to index {file_path}: {e}", file=sys.stderr)

        # Estimate token counts
        for section in sections:
            section.estimated_tokens = self._estimate_tokens(
                file_path, section.start_line, section.end_line
            )

        return sections

    def _index_python_file(self, file_path: Path) -> List[Section]:
        """Index Python file by classes and functions.

        Args:
            file_path: Path to Python file

        Returns:
            List of section metadata
        """
        sections = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for i, line in enumerate(lines, start=1):
                # Match class or function definitions
                match = re.match(r'^(class|def)\s+(\w+)', line)

                if match:
                    def_type = match.group(1)
                    name = match.group(2)
                    section_id = f"{def_type}_{name}"

                    # Find end of definition (simplified - just to next def/class)
                    end_line = i
                    for j in range(i, len(lines)):
                        if re.match(r'^(class|def)\s+', lines[j]):
                            end_line = j
                            break
                    else:
                        end_line = len(lines)

                    estimated_tokens = self._estimate_tokens(file_path, i, end_line)

                    sections.append(Section(
                        file_path=str(file_path),
                        section_id=section_id,
                        section_name=name,
                        start_line=i,
                        end_line=end_line,
                        estimated_tokens=estimated_tokens,
                        section_type=def_type
                    ))

        except Exception as e:
            print(f"Warning: Failed to index {file_path}: {e}", file=sys.stderr)

        return sections

    def _index_markdown_file(self, file_path: Path) -> List[Section]:
        """Index Markdown file by headings.

        Args:
            file_path: Path to Markdown file

        Returns:
            List of section metadata
        """
        sections = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            current_section = None

            for i, line in enumerate(lines, start=1):
                # Match headings (# Header)
                match = re.match(r'^(#{1,6})\s+(.+)$', line)

                if match:
                    # Save previous section
                    if current_section:
                        current_section.end_line = i - 1
                        sections.append(current_section)

                    level = len(match.group(1))
                    heading = match.group(2).strip()
                    section_id = f"h{level}_{i}"

                    current_section = Section(
                        file_path=str(file_path),
                        section_id=section_id,
                        section_name=heading,
                        start_line=i,
                        end_line=i,
                        estimated_tokens=0,
                        section_type=f"heading{level}"
                    )

            # Add last section
            if current_section:
                current_section.end_line = len(lines)
                sections.append(current_section)

        except Exception as e:
            print(f"Warning: Failed to index {file_path}: {e}", file=sys.stderr)

        # Estimate token counts
        for section in sections:
            section.estimated_tokens = self._estimate_tokens(
                file_path, section.start_line, section.end_line
            )

        return sections

    def _estimate_tokens(self, file_path: Path, start_line: int, end_line: int) -> int:
        """Estimate token count for file section.

        Args:
            file_path: Path to file
            start_line: Start line number
            end_line: End line number

        Returns:
            Estimated token count
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            section_text = ''.join(lines[start_line-1:end_line])
            char_count = len(section_text)
            return char_count // CHARS_PER_TOKEN

        except Exception:
            return 0

    def load_section(self, file_path: str, section_id: str) -> Optional[str]:
        """Load specific section from file.

        Args:
            file_path: Path to file
            section_id: Section identifier

        Returns:
            Section content or None if not found
        """
        cache_key = f"{file_path}:{section_id}"

        # Check cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # Find section in metadata
        sections = self.metadata_index.get(file_path, [])
        section_meta = None

        for section in sections:
            if section.section_id == section_id:
                section_meta = section
                break

        if section_meta is None:
            return None

        # Load section from file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            content = ''.join(lines[section_meta.start_line-1:section_meta.end_line])

            # Add to cache
            self.cache.put(cache_key, content, section_meta.estimated_tokens)

            return content

        except Exception as e:
            print(f"Error loading section: {e}", file=sys.stderr)
            return None

    def list_sections(self, file_path: str) -> List[Section]:
        """List all sections in a file.

        Args:
            file_path: Path to file

        Returns:
            List of section metadata
        """
        return self.metadata_index.get(file_path, [])

    def get_stats(self) -> ContextStats:
        """Get context usage statistics.

        Returns:
            Context statistics
        """
        budget_used = (self.cache.current_tokens / self.context_budget) * 100

        return ContextStats(
            loaded_sections=len(self.cache.cache),
            total_tokens=self.cache.current_tokens,
            budget_used_percent=budget_used,
            cache_hits=self.cache.hits,
            cache_misses=self.cache.misses
        )

    def save_index(self, output_file: Path) -> None:
        """Save metadata index to file.

        Args:
            output_file: Path to output JSON file
        """
        # Convert to serializable format
        index_data = {
            file_path: [asdict(section) for section in sections]
            for file_path, sections in self.metadata_index.items()
        }

        with open(output_file, 'w') as f:
            json.dump(index_data, f, indent=2)

        self.index_file = output_file

    def load_index(self, index_file: Path) -> None:
        """Load metadata index from file.

        Args:
            index_file: Path to JSON index file
        """
        with open(index_file, 'r') as f:
            index_data = json.load(f)

        # Convert back to Section objects
        self.metadata_index = {
            file_path: [Section(**section_data) for section_data in sections]
            for file_path, sections in index_data.items()
        }

        self.index_file = index_file


def main():
    """CLI interface for lazy context loader."""
    if len(sys.argv) < 2:
        print("Usage: python3 lazy_context_loader.py <command> [args]")
        print("\nCommands:")
        print("  index <project_root>        - Build metadata index")
        print("  load <file> <section_id>    - Load specific section")
        print("  list <file>                 - List sections in file")
        print("  budget                      - Show context budget usage")
        sys.exit(1)

    loader = LazyContextLoader()
    command = sys.argv[1]

    if command == "index":
        if len(sys.argv) < 3:
            print("Usage: lazy_context_loader.py index <project_root>")
            sys.exit(1)

        project_root = Path(sys.argv[2])
        print(f"Building metadata index for {project_root}...")

        loader.build_metadata_index(project_root)

        total_files = len(loader.metadata_index)
        total_sections = sum(len(sections) for sections in loader.metadata_index.values())

        print(f"Indexed {total_sections} sections across {total_files} files")

        # Save index
        index_file = project_root / ".claude-context-index.json"
        loader.save_index(index_file)
        print(f"Index saved to {index_file}")

    elif command == "load":
        if len(sys.argv) < 4:
            print("Usage: lazy_context_loader.py load <file> <section_id>")
            sys.exit(1)

        file_path = sys.argv[2]
        section_id = sys.argv[3]

        # Try to load existing index
        project_root = Path.cwd()
        index_file = project_root / ".claude-context-index.json"
        if index_file.exists():
            loader.load_index(index_file)
        else:
            print("No index found. Run 'index' command first.")
            sys.exit(1)

        content = loader.load_section(file_path, section_id)
        if content:
            print(content)
        else:
            print(f"Section '{section_id}' not found in {file_path}")

    elif command == "list":
        if len(sys.argv) < 3:
            print("Usage: lazy_context_loader.py list <file>")
            sys.exit(1)

        file_path = sys.argv[2]

        # Try to load existing index
        project_root = Path.cwd()
        index_file = project_root / ".claude-context-index.json"
        if index_file.exists():
            loader.load_index(index_file)
        else:
            print("No index found. Run 'index' command first.")
            sys.exit(1)

        sections = loader.list_sections(file_path)
        print(f"Sections in {file_path}:")
        for section in sections:
            print(f"  {section.section_id}: {section.section_name} "
                  f"(lines {section.start_line}-{section.end_line}, "
                  f"~{section.estimated_tokens} tokens)")

    elif command == "budget":
        stats = loader.get_stats()
        print(f"Context Budget Usage:")
        print(f"  Loaded sections: {stats.loaded_sections}")
        print(f"  Total tokens: {stats.total_tokens:,} / {CONTEXT_BUDGET:,}")
        print(f"  Budget used: {stats.budget_used_percent:.1f}%")
        print(f"  Cache hits: {stats.cache_hits}")
        print(f"  Cache misses: {stats.cache_misses}")

        if stats.cache_hits + stats.cache_misses > 0:
            hit_rate = (stats.cache_hits / (stats.cache_hits + stats.cache_misses)) * 100
            print(f"  Hit rate: {hit_rate:.1f}%")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
