"""
File System Watcher Module - System of Record Foundation
Monitors file system operations, extracts text content, and stores in SQLite.

Usage:
    python -m src.capture.file_watcher

This module watches specified directories for file changes and extracts
content from various file types for semantic search and version tracking.
"""

import asyncio
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal, Set
import json
import mimetypes

# Note: Install these dependencies:
# pip install watchdog python-docx PyPDF2

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
except ImportError:
    print("Install dependencies: pip install watchdog")
    raise

# Optional dependencies for different file types
try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: PyPDF2 not installed. PDF extraction disabled.")

try:
    import docx
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False
    print("Warning: python-docx not installed. DOCX extraction disabled.")


FileOperation = Literal["created", "modified", "deleted"]


class FileWatcher:
    """
    Monitors file system operations and extracts content.
    Designed to be efficient and privacy-conscious.
    """

    # File extensions to monitor
    TEXT_EXTENSIONS = {'.txt', '.md', '.markdown', '.rst'}
    CODE_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h',
        '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
        '.r', '.m', '.sh', '.bash', '.zsh', '.fish', '.sql', '.html',
        '.css', '.scss', '.sass', '.less', '.xml', '.json', '.yaml', '.yml',
        '.toml', '.ini', '.conf', '.cfg'
    }
    DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.doc'}

    def __init__(
        self,
        watch_dirs: Optional[list[Path]] = None,
        db_path: Path = Path("~/.unified-ai/capture.db").expanduser(),
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        ignore_patterns: Optional[Set[str]] = None,
    ):
        """
        Initialize file watcher.

        Args:
            watch_dirs: Directories to monitor (defaults to Documents, Desktop, Downloads)
            db_path: Path to SQLite database
            max_file_size: Maximum file size to process in bytes
            ignore_patterns: Set of patterns to ignore (e.g., {'node_modules', '.git'})
        """
        if watch_dirs is None:
            home = Path.home()
            watch_dirs = [
                home / "Documents",
                home / "Desktop",
                home / "Downloads",
            ]

        self.watch_dirs = [d.expanduser() for d in watch_dirs]
        self.db_path = db_path
        self.max_file_size = max_file_size
        self.ignore_patterns = ignore_patterns or {
            'node_modules', '.git', '.venv', 'venv', '__pycache__',
            '.idea', '.vscode', 'dist', 'build', '.DS_Store'
        }
        self.running = False
        self.observer: Optional[Observer] = None

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for file tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                operation TEXT NOT NULL,
                content_hash TEXT,
                content TEXT,
                file_type TEXT,
                file_size INTEGER,
                metadata JSON,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_path ON file_history(file_path)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON file_history(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_operation ON file_history(operation)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_type ON file_history(file_type)
        """)

        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS file_content_fts USING fts5(
                content,
                file_name,
                file_path,
                content='file_history',
                content_rowid='id'
            )
        """)

        # Version tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                version INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                file_size INTEGER,
                UNIQUE(file_path, version)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_version_path ON file_versions(file_path)
        """)

        conn.commit()
        conn.close()

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored based on ignore patterns."""
        path_parts = path.parts
        return any(pattern in path_parts for pattern in self.ignore_patterns)

    def _should_process(self, path: Path) -> bool:
        """
        Determine if file should be processed.

        Args:
            path: File path to check

        Returns:
            True if file should be processed
        """
        if not path.is_file():
            return False

        if self._should_ignore(path):
            return False

        # Check file size
        try:
            if path.stat().st_size > self.max_file_size:
                return False
        except OSError:
            return False

        # Check if it's a supported file type
        suffix = path.suffix.lower()
        return (
            suffix in self.TEXT_EXTENSIONS or
            suffix in self.CODE_EXTENSIONS or
            suffix in self.DOCUMENT_EXTENSIONS
        )

    def _compute_file_hash(self, content: str) -> str:
        """Compute hash for content versioning."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _classify_file_type(self, path: Path) -> str:
        """
        Classify file type based on extension.

        Args:
            path: File path

        Returns:
            File type classification
        """
        suffix = path.suffix.lower()

        if suffix in self.TEXT_EXTENSIONS:
            return "text"
        elif suffix in self.CODE_EXTENSIONS:
            return "code"
        elif suffix == '.pdf':
            return "pdf"
        elif suffix in {'.docx', '.doc'}:
            return "document"
        else:
            return "unknown"

    def _extract_text_from_txt(self, path: Path) -> str:
        """Extract text from plain text files."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                return f"[Error reading file: {e}]"
        except Exception as e:
            return f"[Error reading file: {e}]"

    def _extract_text_from_pdf(self, path: Path) -> str:
        """
        Extract text from PDF files.

        Args:
            path: Path to PDF file

        Returns:
            Extracted text content
        """
        if not PDF_SUPPORT:
            return "[PDF extraction not available - install PyPDF2]"

        try:
            reader = PdfReader(path)
            text_parts = []

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            return '\n\n'.join(text_parts)
        except Exception as e:
            return f"[Error extracting PDF: {e}]"

    def _extract_text_from_docx(self, path: Path) -> str:
        """
        Extract text from DOCX files.

        Args:
            path: Path to DOCX file

        Returns:
            Extracted text content
        """
        if not DOCX_SUPPORT:
            return "[DOCX extraction not available - install python-docx]"

        try:
            doc = docx.Document(path)
            text_parts = []

            for paragraph in doc.paragraphs:
                if paragraph.text:
                    text_parts.append(paragraph.text)

            return '\n\n'.join(text_parts)
        except Exception as e:
            return f"[Error extracting DOCX: {e}]"

    def _extract_text(self, path: Path) -> str:
        """
        Extract text content from file based on type.

        Args:
            path: File path

        Returns:
            Extracted text content
        """
        suffix = path.suffix.lower()

        if suffix in self.TEXT_EXTENSIONS or suffix in self.CODE_EXTENSIONS:
            return self._extract_text_from_txt(path)
        elif suffix == '.pdf':
            return self._extract_text_from_pdf(path)
        elif suffix in {'.docx', '.doc'}:
            return self._extract_text_from_docx(path)
        else:
            return "[Unsupported file type]"

    def _get_version_number(self, file_path: str) -> int:
        """
        Get next version number for file.

        Args:
            file_path: File path

        Returns:
            Next version number
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT MAX(version) FROM file_versions WHERE file_path = ?
        """, (file_path,))

        result = cursor.fetchone()
        conn.close()

        max_version = result[0] if result[0] is not None else 0
        return max_version + 1

    def _store_version(
        self,
        file_path: str,
        content_hash: str,
        file_size: int,
        timestamp: str
    ):
        """
        Store file version information.

        Args:
            file_path: File path
            content_hash: Content hash
            file_size: File size in bytes
            timestamp: Timestamp of version
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        version = self._get_version_number(file_path)

        cursor.execute("""
            INSERT INTO file_versions
            (file_path, version, content_hash, timestamp, file_size)
            VALUES (?, ?, ?, ?, ?)
        """, (file_path, version, content_hash, timestamp, file_size))

        conn.commit()
        conn.close()

    def process_file(
        self,
        path: Path,
        operation: FileOperation
    ) -> Optional[dict]:
        """
        Process a file system event.

        Args:
            path: File path
            operation: Type of operation (created, modified, deleted)

        Returns:
            Event record or None if not processed
        """
        if operation == "deleted":
            # For deletion, we can't check if file exists or check size
            # But we should still check if extension is one we care about and not ignored
            if self._should_ignore(path):
                return None
            
            suffix = path.suffix.lower()
            if not (suffix in self.TEXT_EXTENSIONS or 
                   suffix in self.CODE_EXTENSIONS or 
                   suffix in self.DOCUMENT_EXTENSIONS):
                return None
        elif not self._should_process(path):
            return None

        timestamp = datetime.now().isoformat()
        file_path = str(path.absolute())
        file_name = path.name
        file_type = self._classify_file_type(path)

        # For deletions, we can't extract content
        if operation == "deleted":
            event = {
                'timestamp': timestamp,
                'file_path': file_path,
                'file_name': file_name,
                'operation': operation,
                'content_hash': None,
                'content': None,
                'file_type': file_type,
                'file_size': None,
                'metadata': {}
            }
        else:
            # Extract content for created/modified files
            try:
                content = self._extract_text(path)
                content_hash = self._compute_file_hash(content)
                file_size = path.stat().st_size

                event = {
                    'timestamp': timestamp,
                    'file_path': file_path,
                    'file_name': file_name,
                    'operation': operation,
                    'content_hash': content_hash,
                    'content': content,
                    'file_type': file_type,
                    'file_size': file_size,
                    'metadata': {
                        'extension': path.suffix,
                        'content_length': len(content),
                    }
                }

                # Store version for modified files
                if operation == "modified":
                    self._store_version(file_path, content_hash, file_size, timestamp)

            except Exception as e:
                print(f"Error processing {path}: {e}")
                return None

        # Store in database
        self._store_event(event)

        return event

    def _store_event(self, event: dict):
        """Store file event in SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO file_history
            (timestamp, file_path, file_name, operation, content_hash,
             content, file_type, file_size, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event['timestamp'],
            event['file_path'],
            event['file_name'],
            event['operation'],
            event['content_hash'],
            event['content'],
            event['file_type'],
            event['file_size'],
            json.dumps(event['metadata'])
        ))

        # Update FTS index if there's content
        if event['content']:
            cursor.execute("""
                INSERT INTO file_content_fts(rowid, content, file_name, file_path)
                VALUES (last_insert_rowid(), ?, ?, ?)
            """, (event['content'], event['file_name'], event['file_path']))

        conn.commit()
        conn.close()

    async def run(self):
        """Run continuous file monitoring."""
        self.running = True

        # Verify watch directories exist
        existing_dirs = []
        for directory in self.watch_dirs:
            if directory.exists():
                existing_dirs.append(directory)
                print(f"Watching: {directory}")
            else:
                print(f"Warning: Directory does not exist: {directory}")

        if not existing_dirs:
            print("Error: No valid directories to watch")
            return

        print(f"Database: {self.db_path}")
        print("Press Ctrl+C to stop")

        # Create event handler
        event_handler = FileEventHandler(self)

        # Create observer
        self.observer = Observer()

        for directory in existing_dirs:
            self.observer.schedule(event_handler, str(directory), recursive=True)

        self.observer.start()

        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop the file monitoring."""
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def search(
        self,
        query: str,
        file_type: Optional[str] = None,
        limit: int = 20
    ) -> list[dict]:
        """
        Search file content using full-text search.

        Args:
            query: Search query string
            file_type: Optional filter by file type
            limit: Maximum number of results

        Returns:
            List of matching file entries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if file_type:
            cursor.execute("""
                SELECT f.id, f.timestamp, f.file_path, f.file_name,
                       f.operation, f.file_type, f.content
                FROM file_history f
                JOIN file_content_fts fts ON f.id = fts.rowid
                WHERE file_content_fts MATCH ? AND f.file_type = ?
                ORDER BY f.timestamp DESC
                LIMIT ?
            """, (query, file_type, limit))
        else:
            cursor.execute("""
                SELECT f.id, f.timestamp, f.file_path, f.file_name,
                       f.operation, f.file_type, f.content
                FROM file_history f
                JOIN file_content_fts fts ON f.id = fts.rowid
                WHERE file_content_fts MATCH ?
                ORDER BY f.timestamp DESC
                LIMIT ?
            """, (query, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'timestamp': row[1],
                'file_path': row[2],
                'file_name': row[3],
                'operation': row[4],
                'file_type': row[5],
                'content': row[6]
            })

        conn.close()
        return results

    def get_file_versions(self, file_path: str) -> list[dict]:
        """
        Get version history for a file.

        Args:
            file_path: File path

        Returns:
            List of file versions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT version, content_hash, timestamp, file_size
            FROM file_versions
            WHERE file_path = ?
            ORDER BY version DESC
        """, (file_path,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'version': row[0],
                'content_hash': row[1],
                'timestamp': row[2],
                'file_size': row[3]
            })

        conn.close()
        return results

    def get_stats(self) -> dict:
        """Get statistics about file monitoring."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_events,
                COUNT(DISTINCT file_path) as unique_files
            FROM file_history
        """)

        row = cursor.fetchone()
        stats = {
            'total_events': row[0],
            'unique_files': row[1]
        }

        cursor.execute("""
            SELECT operation, COUNT(*) as count
            FROM file_history
            GROUP BY operation
            ORDER BY count DESC
        """)

        stats['by_operation'] = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT file_type, COUNT(*) as count
            FROM file_history
            WHERE file_type IS NOT NULL
            GROUP BY file_type
            ORDER BY count DESC
        """)

        stats['by_type'] = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()
        return stats


class FileEventHandler(FileSystemEventHandler):
    """Handler for file system events."""

    def __init__(self, watcher: FileWatcher):
        self.watcher = watcher
        super().__init__()

    def on_created(self, event: FileSystemEvent):
        """Handle file creation."""
        if not event.is_directory:
            path = Path(event.src_path)
            result = self.watcher.process_file(path, "created")
            if result:
                print(f"[{result['timestamp'][:19]}] Created: {result['file_name']} ({result['file_type']})")

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification."""
        if not event.is_directory:
            path = Path(event.src_path)
            result = self.watcher.process_file(path, "modified")
            if result:
                print(f"[{result['timestamp'][:19]}] Modified: {result['file_name']} ({result['file_type']})")

    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion."""
        if not event.is_directory:
            path = Path(event.src_path)
            result = self.watcher.process_file(path, "deleted")
            if result:
                print(f"[{result['timestamp'][:19]}] Deleted: {result['file_name']} ({result['file_type']})")


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="File Watcher for Unified AI System")
    parser.add_argument("--search", type=str, help="Search file content")
    parser.add_argument("--type", type=str, help="Filter by file type")
    parser.add_argument("--versions", type=str, help="Show version history for file path")
    parser.add_argument("--stats", action="store_true", help="Show file monitoring statistics")
    parser.add_argument("--dirs", type=str, nargs='+', help="Directories to watch")
    args = parser.parse_args()

    # Prepare watch directories
    watch_dirs = None
    if args.dirs:
        watch_dirs = [Path(d) for d in args.dirs]

    watcher = FileWatcher(watch_dirs=watch_dirs)

    if args.search:
        results = watcher.search(args.search, file_type=args.type)
        print(f"\nFound {len(results)} results:")
        for r in results:
            print(f"\n[{r['timestamp']}] {r['file_name']} ({r['file_type']})")
            print(f"  Path: {r['file_path']}")
            print(f"  Content preview: {r['content'][:200]}...")

    elif args.versions:
        versions = watcher.get_file_versions(args.versions)
        print(f"\nVersion history for: {args.versions}")
        print(f"Total versions: {len(versions)}\n")
        for v in versions:
            print(f"Version {v['version']}:")
            print(f"  Timestamp: {v['timestamp']}")
            print(f"  Hash: {v['content_hash'][:16]}...")
            print(f"  Size: {v['file_size']} bytes")
            print()

    elif args.stats:
        stats = watcher.get_stats()
        print("\nFile Monitoring Statistics:")
        print(f"  Total events: {stats['total_events']}")
        print(f"  Unique files: {stats['unique_files']}")
        print(f"\nBy operation:")
        for operation, count in stats['by_operation'].items():
            print(f"  {operation}: {count}")
        print(f"\nBy file type:")
        for file_type, count in stats['by_type'].items():
            print(f"  {file_type}: {count}")

    else:
        try:
            asyncio.run(watcher.run())
        except KeyboardInterrupt:
            print("\nFile watcher stopped.")
