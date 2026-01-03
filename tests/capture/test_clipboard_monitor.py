"""
Tests for clipboard monitor module.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.capture.clipboard_monitor import ClipboardMonitor


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def monitor(temp_db):
    """Create a ClipboardMonitor instance with temporary database."""
    return ClipboardMonitor(db_path=temp_db, poll_interval=0.1)


class TestClipboardMonitor:
    """Test suite for ClipboardMonitor class."""

    def test_init_database(self, monitor, temp_db):
        """Test that database is initialized correctly."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Check that tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='clipboard_history'
        """)
        assert cursor.fetchone() is not None

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='clipboard_fts'
        """)
        assert cursor.fetchone() is not None

        conn.close()

    def test_compute_content_hash(self, monitor):
        """Test content hashing."""
        content1 = "Hello, world!"
        content2 = "Hello, world!"
        content3 = "Different content"

        hash1 = monitor._compute_content_hash(content1)
        hash2 = monitor._compute_content_hash(content2)
        hash3 = monitor._compute_content_hash(content3)

        assert hash1 == hash2
        assert hash1 != hash3

    def test_classify_content_text(self, monitor):
        """Test classification of plain text."""
        text = "This is just regular text content."
        assert monitor._classify_content(text) == "text"

    def test_classify_content_url(self, monitor):
        """Test classification of URLs."""
        urls = [
            "https://example.com",
            "http://github.com/user/repo",
            "www.google.com"
        ]
        for url in urls:
            assert monitor._classify_content(url) == "url"

    def test_classify_content_email(self, monitor):
        """Test classification of email addresses."""
        emails = [
            "user@example.com",
            "test.user+tag@domain.co.uk"
        ]
        for email in emails:
            assert monitor._classify_content(email) == "email"

    def test_classify_content_phone(self, monitor):
        """Test classification of phone numbers."""
        phones = [
            "+1 (555) 123-4567",
            "555-123-4567",
            "+44 20 7123 4567"
        ]
        for phone in phones:
            assert monitor._classify_content(phone) == "phone"

    def test_classify_content_path(self, monitor):
        """Test classification of file paths."""
        paths = [
            "/home/user/documents/file.txt",
            "C:\\Users\\User\\Documents\\file.txt",
            "~/Downloads/image.png"
        ]
        for path in paths:
            assert monitor._classify_content(path) == "path"

    def test_classify_content_code_python(self, monitor):
        """Test classification of Python code."""
        code = """
def hello_world():
    print("Hello, world!")
    return True
"""
        assert monitor._classify_content(code) == "code"

    def test_classify_content_code_javascript(self, monitor):
        """Test classification of JavaScript code."""
        code = """
function greet(name) {
    console.log(`Hello, ${name}!`);
}
"""
        assert monitor._classify_content(code) == "code"

    def test_classify_content_code_with_braces(self, monitor):
        """Test classification of code with braces."""
        code = "const obj = { key: 'value', num: 42 };"
        assert monitor._classify_content(code) == "code"

    def test_classify_content_json(self, monitor):
        """Test classification of JSON data."""
        json_data = '{"name": "John", "age": 30, "city": "New York"}'
        assert monitor._classify_content(json_data) == "data"

    def test_classify_content_csv(self, monitor):
        """Test classification of CSV data."""
        csv_data = """name,age,city
John,30,New York
Jane,25,Los Angeles
Bob,35,Chicago"""
        assert monitor._classify_content(csv_data) == "data"

    @patch('pyperclip.paste')
    def test_capture_once_new_content(self, mock_paste, monitor):
        """Test capturing new clipboard content."""
        mock_paste.return_value = "Test content"

        entry = monitor.capture_once()

        assert entry is not None
        assert entry['content'] == "Test content"
        assert entry['content_type'] == "text"
        assert 'timestamp' in entry
        assert 'content_hash' in entry

    @patch('pyperclip.paste')
    def test_capture_once_duplicate(self, mock_paste, monitor):
        """Test that duplicate content is not captured."""
        mock_paste.return_value = "Test content"

        # First capture
        entry1 = monitor.capture_once()
        assert entry1 is not None

        # Second capture with same content
        entry2 = monitor.capture_once()
        assert entry2 is None

    @patch('pyperclip.paste')
    def test_capture_once_empty(self, mock_paste, monitor):
        """Test that empty clipboard is not captured."""
        mock_paste.return_value = ""

        entry = monitor.capture_once()
        assert entry is None

    @patch('pyperclip.paste')
    def test_capture_once_none(self, mock_paste, monitor):
        """Test that None clipboard is not captured."""
        mock_paste.return_value = None

        entry = monitor.capture_once()
        assert entry is None

    @patch('pyperclip.paste')
    def test_store_entry(self, mock_paste, monitor, temp_db):
        """Test storing entry in database."""
        mock_paste.return_value = "Stored content"

        monitor.capture_once()

        # Verify it was stored
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT content, content_type FROM clipboard_history")
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == "Stored content"
        assert row[1] == "text"

        conn.close()

    @patch('pyperclip.paste')
    def test_search(self, mock_paste, monitor):
        """Test searching clipboard history."""
        # Add some test data
        test_items = [
            "Python programming tutorial",
            "JavaScript best practices",
            "Python data structures"
        ]

        for item in test_items:
            mock_paste.return_value = item
            monitor.capture_once()

        # Search for "Python"
        results = monitor.search("Python")

        assert len(results) == 2
        assert all("Python" in r['content'] for r in results)

    @patch('pyperclip.paste')
    def test_search_with_type_filter(self, mock_paste, monitor):
        """Test searching with content type filter."""
        # Add mixed content
        mock_paste.return_value = "https://example.com"
        monitor.capture_once()

        mock_paste.return_value = "Regular text content"
        monitor.capture_once()

        # Search for URLs only
        results = monitor.search("example", content_type="url")

        assert len(results) == 1
        assert results[0]['type'] == "url"

    @patch('pyperclip.paste')
    def test_get_recent(self, mock_paste, monitor):
        """Test getting recent clipboard entries."""
        # Add test data
        for i in range(5):
            mock_paste.return_value = f"Content {i}"
            monitor.capture_once()

        results = monitor.get_recent(limit=3)

        assert len(results) == 3
        assert results[0]['content'] == "Content 4"  # Most recent
        assert results[2]['content'] == "Content 2"

    @patch('pyperclip.paste')
    def test_get_recent_with_type_filter(self, mock_paste, monitor):
        """Test getting recent entries with type filter."""
        # Add mixed content
        mock_paste.return_value = "https://example.com"
        monitor.capture_once()

        mock_paste.return_value = "Regular text"
        monitor.capture_once()

        mock_paste.return_value = "http://another.com"
        monitor.capture_once()

        results = monitor.get_recent(limit=10, content_type="url")

        assert len(results) == 2
        assert all(r['type'] == "url" for r in results)

    @patch('pyperclip.paste')
    def test_get_stats(self, mock_paste, monitor):
        """Test getting statistics."""
        # Add test data
        test_data = [
            ("https://example.com", "url"),
            ("Regular text", "text"),
            ("http://another.com", "url"),
            ("def test(): pass", "code")
        ]

        for content, _ in test_data:
            mock_paste.return_value = content
            monitor.capture_once()

        stats = monitor.get_stats()

        assert stats['total_entries'] == 4
        assert stats['unique_entries'] == 4
        assert 'by_type' in stats
        assert stats['by_type']['url'] == 2
        assert stats['by_type']['text'] == 1
        assert stats['by_type']['code'] == 1

    @patch('pyperclip.paste')
    def test_max_content_length(self, mock_paste, monitor):
        """Test that content is truncated when too long."""
        long_content = "A" * 2_000_000  # 2MB
        mock_paste.return_value = long_content

        entry = monitor.capture_once()

        assert entry is not None
        assert len(entry['content']) <= monitor.max_content_length + 20  # +20 for truncation message
        assert "[truncated]" in entry['content']

    def test_is_duplicate(self, monitor):
        """Test duplicate detection."""
        hash1 = "abc123"
        hash2 = "def456"

        monitor.last_hash = hash1

        assert monitor._is_duplicate(hash1) is True
        assert monitor._is_duplicate(hash2) is False

    def test_stop(self, monitor):
        """Test stopping the monitor."""
        monitor.running = True
        monitor.stop()
        assert monitor.running is False


class TestContentClassification:
    """Additional tests for content type classification edge cases."""

    @pytest.fixture
    def monitor(self, temp_db):
        return ClipboardMonitor(db_path=temp_db)

    def test_classify_empty_string(self, monitor):
        """Test classification of empty string."""
        assert monitor._classify_content("") == "text"
        assert monitor._classify_content("   ") == "text"

    def test_classify_multiline_code(self, monitor):
        """Test classification of multi-line indented code."""
        code = """
    def calculate(x, y):
        result = x + y
        return result
        """
        assert monitor._classify_content(code) == "code"

    def test_classify_arrow_function(self, monitor):
        """Test classification of arrow functions."""
        code = "const add = (a, b) => a + b;"
        assert monitor._classify_content(code) == "code"

    def test_classify_import_statement(self, monitor):
        """Test classification of import statements."""
        imports = [
            "import os",
            "from pathlib import Path",
            "import React from 'react';"
        ]
        for imp in imports:
            assert monitor._classify_content(imp) == "code"

    def test_classify_xml_data(self, monitor):
        """Test classification of XML data."""
        xml = "<root><item>value</item></root>"
        assert monitor._classify_content(xml) == "data"

    def test_classify_mixed_content(self, monitor):
        """Test classification of mixed content defaults to text."""
        mixed = "Check out https://example.com for more info"
        # This contains a URL but isn't purely a URL
        # Classification may vary, but should handle gracefully
        result = monitor._classify_content(mixed)
        assert result in ["text", "url"]
