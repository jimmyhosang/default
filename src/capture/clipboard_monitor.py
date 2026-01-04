"""
Clipboard Monitor Module - System of Record Foundation
Monitors clipboard operations, classifies content, and stores history in SQLite.

Usage:
    python -m src.capture.clipboard_monitor

This module captures all clipboard operations and enables semantic search
across clipboard history, linking to source applications when possible.
"""

import asyncio
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal
import json
import re
import platform

# Note: Install these dependencies:
# pip install pyperclip

try:
    import pyperclip
except ImportError:
    print("Install dependencies: pip install pyperclip")
    raise


ContentType = Literal["text", "code", "url", "data", "email", "phone", "path"]


class ClipboardMonitor:
    """
    Monitors clipboard operations in real-time and stores history.
    Designed to be efficient and privacy-conscious.
    """

    def __init__(
        self,
        db_path: Path = Path("~/.unified-ai/capture.db").expanduser(),
        poll_interval: float = 0.5,  # seconds
        max_content_length: int = 1_000_000,  # 1MB text limit
    ):
        self.db_path = db_path
        self.poll_interval = poll_interval
        self.max_content_length = max_content_length
        self.last_hash: Optional[str] = None
        self.running = False

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for clipboard history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clipboard_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL,
                source_app TEXT,
                metadata JSON,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_clipboard_timestamp
            ON clipboard_history(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_clipboard_type
            ON clipboard_history(content_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_clipboard_hash
            ON clipboard_history(content_hash)
        """)

        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS clipboard_fts USING fts5(
                content,
                content='clipboard_history',
                content_rowid='id'
            )
        """)

        conn.commit()
        conn.close()

    def _compute_content_hash(self, content: str) -> str:
        """Compute hash for duplicate detection."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _is_duplicate(self, content_hash: str) -> bool:
        """Check if content is duplicate of last clipboard entry."""
        return content_hash == self.last_hash

    def _classify_content(self, content: str) -> ContentType:
        """
        Classify clipboard content type.

        Args:
            content: The clipboard text content

        Returns:
            Content type classification
        """
        if not content or len(content.strip()) == 0:
            return "text"

        content_lower = content.strip().lower()

        # Check for URLs
        url_pattern = r'^https?://[^\s]+$|^www\.[^\s]+$'
        if re.match(url_pattern, content_lower):
            return "url"

        # Check for email addresses
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, content.strip()):
            return "email"

        # Check for phone numbers
        phone_pattern = r'^\+?[\d\s\-\(\)]{10,}$'
        if re.match(phone_pattern, content.strip()):
            return "phone"

        # Check for file paths
        path_pattern = r'^(/|[A-Za-z]:\\|~/).*$'
        if re.match(path_pattern, content.strip()):
            # Verify it looks like a real path
            if '/' in content or '\\' in content:
                return "path"

        # Check for structured data (JSON, XML, CSV)
        if content.strip().startswith(('{', '[', '<')):
            try:
                json.loads(content)
                return "data"
            except (json.JSONDecodeError, ValueError):
                if content.strip().startswith('<'):
                    return "data"  # Likely XML

        # CSV-like data
        if ',' in content and '\n' in content:
            lines = content.strip().split('\n')
            if len(lines) > 1:
                # Check if lines have similar comma counts
                comma_counts = [line.count(',') for line in lines[:5]]
                if len(set(comma_counts)) == 1 and comma_counts[0] > 0:
                    return "data"

        # Check for code - multiple heuristics
        code_indicators = [
            r'\bdef\s+\w+\s*\(',  # Python function
            r'\bfunction\s+\w+\s*\(',  # JavaScript function
            r'\bclass\s+\w+',  # Class definition
            r'\bimport\s+\w+',  # Import statement
            r'\bfrom\s+\w+\s+import',  # Python import
            r'\bconst\s+\w+\s*=',  # JavaScript const
            r'\blet\s+\w+\s*=',  # JavaScript let
            r'\bvar\s+\w+\s*=',  # JavaScript var
            r'=>',  # Arrow function
            r'\{[\s\S]*\}',  # Code blocks (with newlines)
            r'[\{\}\[\];]',  # Code punctuation
        ]

        # Count lines and check for code patterns
        lines = content.split('\n')
        if len(lines) > 2:
            # Multi-line content with indentation suggests code
            indented_lines = sum(1 for line in lines if line.startswith((' ', '\t')))
            if indented_lines > len(lines) * 0.3:  # 30% indented
                return "code"

        # Check for code patterns
        for pattern in code_indicators:
            if re.search(pattern, content):
                return "code"

        # Default to text
        return "text"

    def _get_source_app(self) -> str:
        """
        Get the application that copied to clipboard.
        Platform-specific implementation.
        """
        system = platform.system()

        try:
            if system == "Darwin":  # macOS
                # Try to get active app using AppleScript
                import subprocess
                result = subprocess.run(
                    ['osascript', '-e', 'tell application "System Events" to get name of first application process whose frontmost is true'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0:
                    return result.stdout.strip()

            elif system == "Linux":
                # Try to get active window using xdotool
                import subprocess
                result = subprocess.run(
                    ['xdotool', 'getactivewindow', 'getwindowname'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0:
                    return result.stdout.strip()

            elif system == "Windows":
                # Try to get active window using win32gui
                try:
                    import win32gui
                    window = win32gui.GetForegroundWindow()
                    return win32gui.GetWindowText(window)
                except ImportError:
                    pass

        except Exception:
            pass

        return "Unknown"

    def capture_once(self) -> Optional[dict]:
        """Capture current clipboard content and process it."""
        try:
            # Get clipboard content
            content = pyperclip.paste()

            # Validate content
            if content is None or len(content) == 0:
                return None

            # Check size limit
            if len(content) > self.max_content_length:
                content = content[:self.max_content_length] + "... [truncated]"

            # Check for duplicates
            content_hash = self._compute_content_hash(content)
            if self._is_duplicate(content_hash):
                return None

            self.last_hash = content_hash

            # Classify content
            content_type = self._classify_content(content)

            # Get source application
            source_app = self._get_source_app()

            # Create clipboard entry
            entry = {
                'timestamp': datetime.now().isoformat(),
                'content_hash': content_hash,
                'content': content,
                'content_type': content_type,
                'source_app': source_app,
                'metadata': {
                    'content_length': len(content),
                    'line_count': content.count('\n') + 1,
                }
            }

            # Store in database
            self._store_entry(entry)

            return entry

        except Exception as e:
            print(f"Clipboard capture error: {e}")
            return None

    def _store_entry(self, entry: dict):
        """Store clipboard entry in SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO clipboard_history
            (timestamp, content_hash, content, content_type, source_app, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry['timestamp'],
            entry['content_hash'],
            entry['content'],
            entry['content_type'],
            entry['source_app'],
            json.dumps(entry['metadata'])
        ))

        # Update FTS index
        cursor.execute("""
            INSERT INTO clipboard_fts(rowid, content)
            VALUES (last_insert_rowid(), ?)
        """, (entry['content'],))

        conn.commit()
        conn.close()

    async def run(self):
        """Run continuous clipboard monitoring loop."""
        self.running = True
        print(f"Starting clipboard monitor (poll interval: {self.poll_interval}s)")
        print(f"Database: {self.db_path}")
        print("Press Ctrl+C to stop")

        while self.running:
            try:
                entry = self.capture_once()
                if entry:
                    content_preview = entry['content'][:80].replace('\n', ' ')
                    print(f"[{entry['timestamp'][:19]}] {entry['content_type']:8s} from {entry['source_app']}: {content_preview}...")
            except Exception as e:
                print(f"Monitor error: {e}")

            await asyncio.sleep(self.poll_interval)

    def stop(self):
        """Stop the monitoring loop."""
        self.running = False

    def search(
        self,
        query: str,
        content_type: Optional[ContentType] = None,
        limit: int = 20
    ) -> list[dict]:
        """
        Search clipboard history using full-text search.

        Args:
            query: Search query string
            content_type: Optional filter by content type
            limit: Maximum number of results

        Returns:
            List of matching clipboard entries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if content_type:
            cursor.execute("""
                SELECT c.id, c.timestamp, c.content, c.content_type, c.source_app
                FROM clipboard_history c
                JOIN clipboard_fts fts ON c.id = fts.rowid
                WHERE clipboard_fts MATCH ? AND c.content_type = ?
                ORDER BY c.timestamp DESC
                LIMIT ?
            """, (query, content_type, limit))
        else:
            cursor.execute("""
                SELECT c.id, c.timestamp, c.content, c.content_type, c.source_app
                FROM clipboard_history c
                JOIN clipboard_fts fts ON c.id = fts.rowid
                WHERE clipboard_fts MATCH ?
                ORDER BY c.timestamp DESC
                LIMIT ?
            """, (query, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'timestamp': row[1],
                'content': row[2],
                'type': row[3],
                'source_app': row[4]
            })

        conn.close()
        return results

    def get_recent(
        self,
        limit: int = 20,
        content_type: Optional[ContentType] = None
    ) -> list[dict]:
        """
        Get recent clipboard entries.

        Args:
            limit: Maximum number of results
            content_type: Optional filter by content type

        Returns:
            List of recent clipboard entries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if content_type:
            cursor.execute("""
                SELECT id, timestamp, content, content_type, source_app
                FROM clipboard_history
                WHERE content_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (content_type, limit))
        else:
            cursor.execute("""
                SELECT id, timestamp, content, content_type, source_app
                FROM clipboard_history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'timestamp': row[1],
                'content': row[2],
                'type': row[3],
                'source_app': row[4]
            })

        conn.close()
        return results

    def get_stats(self) -> dict:
        """Get statistics about clipboard history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT content_hash) as unique_entries,
                COUNT(DISTINCT source_app) as unique_apps
            FROM clipboard_history
        """)

        row = cursor.fetchone()
        stats = {
            'total_entries': row[0],
            'unique_entries': row[1],
            'unique_apps': row[2]
        }

        cursor.execute("""
            SELECT content_type, COUNT(*) as count
            FROM clipboard_history
            GROUP BY content_type
            ORDER BY count DESC
        """)

        stats['by_type'] = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()
        return stats


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clipboard Monitor for Unified AI System")
    parser.add_argument("--search", type=str, help="Search clipboard history")
    parser.add_argument("--type", type=str, choices=["text", "code", "url", "data", "email", "phone", "path"],
                       help="Filter by content type")
    parser.add_argument("--recent", type=int, metavar="N", help="Show N recent clipboard entries")
    parser.add_argument("--stats", action="store_true", help="Show clipboard history statistics")
    parser.add_argument("--interval", type=float, default=0.5, help="Poll interval in seconds")
    args = parser.parse_args()

    monitor = ClipboardMonitor(poll_interval=args.interval)

    if args.search:
        results = monitor.search(args.search, content_type=args.type)
        print(f"\nFound {len(results)} results:")
        for r in results:
            print(f"\n[{r['timestamp']}] {r['type']} from {r['source_app']}")
            print(f"  {r['content'][:200]}...")

    elif args.recent:
        results = monitor.get_recent(limit=args.recent, content_type=args.type)
        print(f"\nShowing {len(results)} recent entries:")
        for r in results:
            print(f"\n[{r['timestamp']}] {r['type']} from {r['source_app']}")
            print(f"  {r['content'][:200]}...")

    elif args.stats:
        stats = monitor.get_stats()
        print("\nClipboard History Statistics:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Unique entries: {stats['unique_entries']}")
        print(f"  Unique apps: {stats['unique_apps']}")
        print(f"\nBy content type:")
        for content_type, count in stats['by_type'].items():
            print(f"  {content_type}: {count}")

    else:
        try:
            asyncio.run(monitor.run())
        except KeyboardInterrupt:
            print("\nClipboard monitor stopped.")
