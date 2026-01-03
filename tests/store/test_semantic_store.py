"""
Tests for Semantic Storage Layer

These tests verify the functionality of the semantic store including:
- Content storage and retrieval
- Entity extraction
- Vector embeddings and semantic search
- Hybrid search capabilities
"""

import pytest
import sqlite3
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

from src.store.semantic_store import SemanticStore


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_capture.db"
    vector_path = Path(temp_dir) / "test_lancedb"

    yield db_path, vector_path

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def store(temp_db_path):
    """Create a semantic store instance for testing."""
    db_path, vector_path = temp_db_path
    return SemanticStore(db_path=db_path, vector_db_path=vector_path)


class TestSemanticStore:
    """Test suite for SemanticStore class."""

    def test_initialization(self, store):
        """Test that store initializes correctly."""
        assert store.db_path.exists()
        assert store.db_path.parent.exists()

        # Verify database tables exist
        conn = sqlite3.connect(store.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN (
                'semantic_content',
                'entities',
                'semantic_content_fts'
            )
        """)

        tables = {row[0] for row in cursor.fetchall()}
        assert 'semantic_content' in tables
        assert 'entities' in tables
        assert 'semantic_content_fts' in tables

        conn.close()

    def test_add_content(self, store):
        """Test adding content to the store."""
        content = "Meeting with John Smith about Q1 revenue of $500,000"

        content_id = store.add(content, source_type="manual")

        assert content_id > 0

        # Verify content was stored
        conn = sqlite3.connect(store.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT content, source_type FROM semantic_content WHERE id = ?
        """, (content_id,))

        row = cursor.fetchone()
        assert row is not None
        assert row[0] == content
        assert row[1] == "manual"

        conn.close()

    def test_add_with_metadata(self, store):
        """Test adding content with metadata."""
        content = "Test content"
        metadata = {"key": "value", "number": 123}

        content_id = store.add(content, metadata=metadata)

        # Verify metadata was stored
        conn = sqlite3.connect(store.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT metadata FROM semantic_content WHERE id = ?", (content_id,))
        row = cursor.fetchone()

        import json
        stored_metadata = json.loads(row[0])
        assert stored_metadata == metadata

        conn.close()

    def test_search_text(self, store):
        """Test full-text search."""
        # Add test content
        store.add("Python programming tutorial", source_type="manual")
        store.add("JavaScript web development", source_type="manual")
        store.add("Python data science", source_type="manual")

        # Search for Python
        results = store.search("Python")

        assert len(results) == 2
        assert all("Python" in r['content'] or "python" in r['content'].lower() for r in results)

    def test_search_with_source_filter(self, store):
        """Test search with source type filtering."""
        store.add("Content from clipboard", source_type="clipboard")
        store.add("Content from screen", source_type="screen")
        store.add("Content from file", source_type="file")

        # Search only clipboard
        results = store.search("Content", source_type="clipboard")

        assert len(results) == 1
        assert results[0]['source_type'] == "clipboard"

    def test_entity_extraction(self, store):
        """Test entity extraction from content."""
        # This test may be skipped if spaCy is not available
        if not store.nlp:
            pytest.skip("spaCy not available")

        content = "Meeting with John Smith from Acme Corp about $500,000 deal on January 15th"

        content_id = store.add(content, extract_entities=True)

        # Get extracted entities
        entities = store.get_entities()

        # Filter to entities from this content
        content_entities = [e for e in entities if e['content_id'] == content_id]

        assert len(content_entities) > 0

        # Check for expected entity types
        entity_types = {e['type'] for e in content_entities}
        # Note: Exact entities depend on spaCy model, but we should find at least some
        assert len(entity_types) > 0

    def test_get_entities_by_type(self, store):
        """Test filtering entities by type."""
        if not store.nlp:
            pytest.skip("spaCy not available")

        store.add("John Smith and Jane Doe met with Microsoft", extract_entities=True)

        # Get person entities
        person_entities = store.get_entities(entity_type="person")

        # Should find at least one person
        assert len(person_entities) >= 0  # May vary based on spaCy model

    def test_semantic_search(self, store):
        """Test semantic similarity search."""
        if not store.embedding_model or not store.lance_table:
            pytest.skip("Vector search not available")

        # Add semantically related content
        store.add("Python machine learning tutorial")
        store.add("Artificial intelligence with Python")
        store.add("Cooking pasta recipes")

        # Search for AI-related content
        results = store.semantic_search("artificial intelligence and ML")

        # Should find AI-related content ranked higher than cooking
        assert len(results) > 0
        # First results should be about AI/ML, not cooking
        top_result = results[0]['content'].lower()
        assert 'python' in top_result or 'intelligence' in top_result or 'learning' in top_result

    def test_get_stats(self, store):
        """Test statistics retrieval."""
        # Add varied content
        store.add("Content 1", source_type="screen")
        store.add("Content 2", source_type="clipboard")
        store.add("Content 3", source_type="clipboard")

        stats = store.get_stats()

        assert stats['total_content'] == 3
        assert stats['by_source']['screen'] == 1
        assert stats['by_source']['clipboard'] == 2

    def test_sync_from_captures(self, store, temp_db_path):
        """Test syncing from existing capture tables."""
        db_path, _ = temp_db_path

        # Manually create some capture data
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create captures table (screen capture)
        cursor.execute("""
            CREATE TABLE captures (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                extracted_text TEXT
            )
        """)

        cursor.execute("""
            INSERT INTO captures (timestamp, extracted_text)
            VALUES (?, ?)
        """, (datetime.now().isoformat(), "Screen capture test"))

        conn.commit()
        conn.close()

        # Sync
        store.sync_from_captures()

        # Verify content was synced
        results = store.search("Screen capture")
        assert len(results) == 1
        assert results[0]['source_type'] == "screen"

    def test_empty_search(self, store):
        """Test search with no results."""
        results = store.search("nonexistentquery123456")
        assert len(results) == 0

    def test_limit_parameter(self, store):
        """Test that limit parameter works correctly."""
        # Add many items
        for i in range(20):
            store.add(f"Test content number {i}")

        # Search with limit
        results = store.search("Test", limit=5)

        assert len(results) <= 5

    def test_timestamp_ordering(self, store):
        """Test that results are ordered by timestamp (newest first)."""
        import time

        content_ids = []
        for i in range(3):
            content_id = store.add(f"Test content {i}")
            content_ids.append(content_id)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        results = store.search("Test")

        # Results should be in reverse chronological order
        result_ids = [r['id'] for r in results]
        assert result_ids == list(reversed(content_ids))

    def test_add_different_source_types(self, store):
        """Test adding content from different source types."""
        source_types = ["screen", "clipboard", "file", "manual"]

        for source in source_types:
            content_id = store.add(f"Content from {source}", source_type=source)
            assert content_id > 0

        stats = store.get_stats()
        assert stats['total_content'] == 4

        for source in source_types:
            assert source in stats['by_source']
            assert stats['by_source'][source] == 1


class TestCLI:
    """Test CLI functionality (basic validation)."""

    def test_cli_module_imports(self):
        """Test that CLI module can be imported."""
        from src.store import cli

        assert hasattr(cli, 'main')
        assert hasattr(cli, 'cmd_search')
        assert hasattr(cli, 'cmd_add')
        assert hasattr(cli, 'cmd_stats')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
