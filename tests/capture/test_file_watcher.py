"""
Tests for file watcher module.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.capture.file_watcher import FileWatcher, FileEventHandler


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
def temp_watch_dir():
    """Create a temporary directory to watch."""
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    import shutil
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def watcher(temp_db, temp_watch_dir):
    """Create a FileWatcher instance with temporary database and directory."""
    return FileWatcher(watch_dirs=[temp_watch_dir], db_path=temp_db)


class TestFileWatcher:
    """Test suite for FileWatcher class."""

    def test_init_database(self, watcher, temp_db):
        """Test that database is initialized correctly."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Check that tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='file_history'
        """)
        assert cursor.fetchone() is not None

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='file_content_fts'
        """)
        assert cursor.fetchone() is not None

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='file_versions'
        """)
        assert cursor.fetchone() is not None

        conn.close()

    def test_should_ignore(self, watcher):
        """Test ignore patterns."""
        assert watcher._should_ignore(Path("/home/user/project/node_modules/package.json"))
        assert watcher._should_ignore(Path("/home/user/project/.git/config"))
        assert watcher._should_ignore(Path("/home/user/project/__pycache__/module.pyc"))
        assert not watcher._should_ignore(Path("/home/user/project/src/main.py"))

    def test_should_process_text_files(self, watcher, temp_watch_dir):
        """Test that text files should be processed."""
        test_file = temp_watch_dir / "test.txt"
        test_file.write_text("test content")
        assert watcher._should_process(test_file)

    def test_should_process_code_files(self, watcher, temp_watch_dir):
        """Test that code files should be processed."""
        code_files = ["test.py", "test.js", "test.java", "test.cpp"]
        for filename in code_files:
            test_file = temp_watch_dir / filename
            test_file.write_text("code content")
            assert watcher._should_process(test_file)

    def test_should_not_process_large_files(self, watcher, temp_watch_dir):
        """Test that files exceeding max size are not processed."""
        large_file = temp_watch_dir / "large.txt"
        # Create a file larger than max_file_size
        with open(large_file, 'w') as f:
            f.write('x' * (watcher.max_file_size + 1))
        assert not watcher._should_process(large_file)

    def test_should_not_process_unsupported_files(self, watcher, temp_watch_dir):
        """Test that unsupported file types are not processed."""
        unsupported = temp_watch_dir / "test.exe"
        unsupported.write_bytes(b"binary content")
        assert not watcher._should_process(unsupported)

    def test_compute_file_hash(self, watcher):
        """Test file hash computation."""
        content1 = "Hello, world!"
        content2 = "Hello, world!"
        content3 = "Different content"

        hash1 = watcher._compute_file_hash(content1)
        hash2 = watcher._compute_file_hash(content2)
        hash3 = watcher._compute_file_hash(content3)

        assert hash1 == hash2
        assert hash1 != hash3

    def test_classify_file_type(self, watcher):
        """Test file type classification."""
        assert watcher._classify_file_type(Path("test.txt")) == "text"
        assert watcher._classify_file_type(Path("test.md")) == "text"
        assert watcher._classify_file_type(Path("test.py")) == "code"
        assert watcher._classify_file_type(Path("test.js")) == "code"
        assert watcher._classify_file_type(Path("test.pdf")) == "pdf"
        assert watcher._classify_file_type(Path("test.docx")) == "document"

    def test_extract_text_from_txt(self, watcher, temp_watch_dir):
        """Test text extraction from plain text files."""
        test_file = temp_watch_dir / "test.txt"
        content = "This is a test file.\nWith multiple lines."
        test_file.write_text(content)

        extracted = watcher._extract_text_from_txt(test_file)
        assert extracted == content

    def test_extract_text_from_txt_with_encoding_issues(self, watcher, temp_watch_dir):
        """Test text extraction handles encoding issues."""
        test_file = temp_watch_dir / "test.txt"
        # Write binary data that's not valid UTF-8
        test_file.write_bytes(b'\xff\xfe')

        extracted = watcher._extract_text_from_txt(test_file)
        # Should handle gracefully, not crash
        assert isinstance(extracted, str)

    def test_process_file_created(self, watcher, temp_watch_dir, temp_db):
        """Test processing file creation."""
        test_file = temp_watch_dir / "new_file.txt"
        test_file.write_text("New file content")

        result = watcher.process_file(test_file, "created")

        assert result is not None
        assert result['operation'] == "created"
        assert result['file_name'] == "new_file.txt"
        assert result['content'] == "New file content"
        assert result['file_type'] == "text"

        # Verify it was stored in database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT file_name, operation FROM file_history")
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == "new_file.txt"
        assert row[1] == "created"

        conn.close()

    def test_process_file_modified(self, watcher, temp_watch_dir, temp_db):
        """Test processing file modification."""
        test_file = temp_watch_dir / "modified_file.txt"
        test_file.write_text("Original content")

        # First creation
        watcher.process_file(test_file, "created")

        # Then modification
        test_file.write_text("Modified content")
        result = watcher.process_file(test_file, "modified")

        assert result is not None
        assert result['operation'] == "modified"
        assert result['content'] == "Modified content"

        # Check that version was stored
        versions = watcher.get_file_versions(str(test_file.absolute()))
        assert len(versions) == 1
        assert versions[0]['version'] == 1

    def test_process_file_deleted(self, watcher, temp_watch_dir):
        """Test processing file deletion."""
        test_file = temp_watch_dir / "deleted_file.txt"

        result = watcher.process_file(test_file, "deleted")

        assert result is not None
        assert result['operation'] == "deleted"
        assert result['content'] is None
        assert result['content_hash'] is None

    def test_process_file_ignores_unsupported(self, watcher, temp_watch_dir):
        """Test that unsupported files are ignored."""
        test_file = temp_watch_dir / "test.exe"
        test_file.write_bytes(b"binary")

        result = watcher.process_file(test_file, "created")
        assert result is None

    def test_get_version_number(self, watcher, temp_watch_dir):
        """Test version numbering."""
        test_file = temp_watch_dir / "versioned.txt"
        test_file.write_text("Version 1")
        file_path = str(test_file.absolute())

        # First version should be 1
        assert watcher._get_version_number(file_path) == 1

        # Store a version
        watcher._store_version(file_path, "hash1", 100, "2024-01-01T00:00:00")

        # Next version should be 2
        assert watcher._get_version_number(file_path) == 2

    def test_store_version(self, watcher, temp_watch_dir, temp_db):
        """Test storing file versions."""
        test_file = temp_watch_dir / "versioned.txt"
        test_file.write_text("Content")
        file_path = str(test_file.absolute())

        watcher._store_version(file_path, "hash123", 1024, "2024-01-01T00:00:00")

        # Verify it was stored
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT file_path, version, content_hash, file_size
            FROM file_versions
            WHERE file_path = ?
        """, (file_path,))
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == file_path
        assert row[1] == 1
        assert row[2] == "hash123"
        assert row[3] == 1024

        conn.close()

    def test_search(self, watcher, temp_watch_dir):
        """Test searching file content."""
        # Create test files
        file1 = temp_watch_dir / "python_tutorial.txt"
        file1.write_text("Python programming tutorial")
        watcher.process_file(file1, "created")

        file2 = temp_watch_dir / "javascript_guide.txt"
        file2.write_text("JavaScript best practices")
        watcher.process_file(file2, "created")

        file3 = temp_watch_dir / "python_data.txt"
        file3.write_text("Python data structures")
        watcher.process_file(file3, "created")

        # Search for "Python"
        results = watcher.search("Python")

        assert len(results) == 2
        assert all("Python" in r['content'] for r in results)

    def test_search_with_type_filter(self, watcher, temp_watch_dir):
        """Test searching with file type filter."""
        # Create mixed file types
        txt_file = temp_watch_dir / "test.txt"
        txt_file.write_text("Text file content")
        watcher.process_file(txt_file, "created")

        py_file = temp_watch_dir / "test.py"
        py_file.write_text("def test(): pass")
        watcher.process_file(py_file, "created")

        # Search for code files only
        results = watcher.search("test", file_type="code")

        assert len(results) == 1
        assert results[0]['file_type'] == "code"

    def test_get_file_versions(self, watcher, temp_watch_dir):
        """Test getting file version history."""
        test_file = temp_watch_dir / "versioned.txt"
        file_path = str(test_file.absolute())

        # Create multiple versions
        test_file.write_text("Version 1")
        watcher.process_file(test_file, "created")

        test_file.write_text("Version 2")
        watcher.process_file(test_file, "modified")

        test_file.write_text("Version 3")
        watcher.process_file(test_file, "modified")

        # Get version history
        versions = watcher.get_file_versions(file_path)

        assert len(versions) == 2  # Only modifications create versions
        assert versions[0]['version'] == 2  # Most recent first
        assert versions[1]['version'] == 1

    def test_get_stats(self, watcher, temp_watch_dir):
        """Test getting statistics."""
        # Create test files
        txt_file = temp_watch_dir / "test.txt"
        txt_file.write_text("Text content")
        watcher.process_file(txt_file, "created")

        py_file = temp_watch_dir / "test.py"
        py_file.write_text("code")
        watcher.process_file(py_file, "created")

        txt_file.write_text("Modified")
        watcher.process_file(txt_file, "modified")

        stats = watcher.get_stats()

        assert stats['total_events'] == 3
        assert stats['unique_files'] == 2
        assert 'by_operation' in stats
        assert stats['by_operation']['created'] == 2
        assert stats['by_operation']['modified'] == 1
        assert 'by_type' in stats
        assert stats['by_type']['text'] == 2
        assert stats['by_type']['code'] == 1

    def test_multiple_file_modifications(self, watcher, temp_watch_dir):
        """Test tracking multiple modifications to same file."""
        test_file = temp_watch_dir / "changelog.txt"
        file_path = str(test_file.absolute())

        # Create and modify file multiple times
        contents = [
            "Version 1.0.0",
            "Version 1.1.0",
            "Version 1.2.0",
            "Version 2.0.0"
        ]

        test_file.write_text(contents[0])
        watcher.process_file(test_file, "created")

        for content in contents[1:]:
            test_file.write_text(content)
            watcher.process_file(test_file, "modified")

        # Check version history
        versions = watcher.get_file_versions(file_path)
        assert len(versions) == 3  # 3 modifications

    def test_code_file_types(self, watcher, temp_watch_dir):
        """Test various code file type processing."""
        code_files = {
            "script.py": "def main(): pass",
            "app.js": "function app() {}",
            "component.tsx": "const App = () => <div></div>;",
            "Main.java": "public class Main {}",
            "config.yaml": "key: value"
        }

        for filename, content in code_files.items():
            file_path = temp_watch_dir / filename
            file_path.write_text(content)
            result = watcher.process_file(file_path, "created")

            assert result is not None
            assert result['file_type'] == "code"
            assert result['content'] == content


class TestFileEventHandler:
    """Test suite for FileEventHandler class."""

    def test_on_created(self, watcher, temp_watch_dir, capsys):
        """Test file creation event handling."""
        handler = FileEventHandler(watcher)

        test_file = temp_watch_dir / "new.txt"
        test_file.write_text("test")

        # Create mock event
        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = str(test_file)

        handler.on_created(mock_event)

        # Check console output
        captured = capsys.readouterr()
        assert "Created: new.txt" in captured.out

    def test_on_modified(self, watcher, temp_watch_dir, capsys):
        """Test file modification event handling."""
        handler = FileEventHandler(watcher)

        test_file = temp_watch_dir / "modified.txt"
        test_file.write_text("test")

        # Create mock event
        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = str(test_file)

        handler.on_modified(mock_event)

        # Check console output
        captured = capsys.readouterr()
        assert "Modified: modified.txt" in captured.out

    def test_on_deleted(self, watcher, temp_watch_dir, capsys):
        """Test file deletion event handling."""
        handler = FileEventHandler(watcher)

        test_file = temp_watch_dir / "deleted.txt"

        # Create mock event
        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = str(test_file)

        handler.on_deleted(mock_event)

        # Check console output
        captured = capsys.readouterr()
        assert "Deleted: deleted.txt" in captured.out

    def test_ignore_directory_events(self, watcher, temp_watch_dir):
        """Test that directory events are ignored."""
        handler = FileEventHandler(watcher)

        # Create mock directory event
        mock_event = MagicMock()
        mock_event.is_directory = True
        mock_event.src_path = str(temp_watch_dir / "subdir")

        # These should not crash and should not process
        handler.on_created(mock_event)
        handler.on_modified(mock_event)
        handler.on_deleted(mock_event)


class TestMarkdownFiles:
    """Test markdown file processing."""

    @pytest.fixture
    def watcher(self, temp_db, temp_watch_dir):
        return FileWatcher(watch_dirs=[temp_watch_dir], db_path=temp_db)

    def test_markdown_file_processing(self, watcher, temp_watch_dir):
        """Test processing markdown files."""
        md_file = temp_watch_dir / "README.md"
        md_content = """# Project Title

## Description
This is a test project.

## Features
- Feature 1
- Feature 2
"""
        md_file.write_text(md_content)

        result = watcher.process_file(md_file, "created")

        assert result is not None
        assert result['file_type'] == "text"
        assert result['content'] == md_content
        assert "Project Title" in result['content']

    def test_search_markdown_content(self, watcher, temp_watch_dir):
        """Test searching markdown content."""
        md_file = temp_watch_dir / "docs.md"
        md_file.write_text("# Documentation\n\nPython API reference")
        watcher.process_file(md_file, "created")

        results = watcher.search("API reference")
        assert len(results) == 1
        assert "Python API reference" in results[0]['content']
