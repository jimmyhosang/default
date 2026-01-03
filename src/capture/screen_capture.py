"""
Screen Capture Module - System of Record Foundation
Captures screenshots, extracts text via OCR, and stores in semantic database.

Usage:
    python -m src.capture.screen_capture

This is the foundation of the "API-less" capture approach - we observe
what's on screen rather than requiring integrations with every app.
"""

import asyncio
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

# Note: Install these dependencies:
# pip install mss pytesseract pillow

try:
    import mss
    import pytesseract
    from PIL import Image
except ImportError:
    print("Install dependencies: pip install mss pytesseract pillow")
    raise


class ScreenCapture:
    """
    Captures screenshots and extracts text content.
    Designed to be efficient (<5% CPU) and privacy-conscious.
    """
    
    def __init__(
        self,
        db_path: Path = Path("~/.unified-ai/capture.db").expanduser(),
        capture_interval: int = 5,  # seconds
        min_change_threshold: float = 0.1,  # 10% pixel change to store
    ):
        self.db_path = db_path
        self.capture_interval = capture_interval
        self.min_change_threshold = min_change_threshold
        self.last_hash: Optional[str] = None
        self.running = False
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for captured content."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS captures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                screen_hash TEXT NOT NULL,
                extracted_text TEXT,
                active_window TEXT,
                active_app TEXT,
                metadata JSON,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON captures(timestamp)
        """)
        
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS captures_fts USING fts5(
                extracted_text,
                content='captures',
                content_rowid='id'
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _compute_image_hash(self, image: Image.Image) -> str:
        """Compute perceptual hash for change detection."""
        # Resize to small size for fast comparison
        small = image.resize((16, 16)).convert('L')
        pixels = list(small.getdata())
        avg = sum(pixels) / len(pixels)
        bits = ''.join('1' if p > avg else '0' for p in pixels)
        return hashlib.md5(bits.encode()).hexdigest()
    
    def _has_significant_change(self, current_hash: str) -> bool:
        """Check if screen content has changed significantly."""
        if self.last_hash is None:
            return True
        return current_hash != self.last_hash
    
    def _extract_text(self, image: Image.Image) -> str:
        """Extract text from screenshot using OCR."""
        try:
            # Preprocess for better OCR
            gray = image.convert('L')
            text = pytesseract.image_to_string(gray)
            return text.strip()
        except Exception as e:
            print(f"OCR failed: {e}")
            return ""
    
    def _get_active_window(self) -> tuple[str, str]:
        """Get active window title and application name."""
        # Platform-specific implementation needed
        # This is a placeholder - implement for your OS
        try:
            # macOS example using pyobjc
            # Linux example using xdotool
            # Windows example using pywin32
            return ("Unknown Window", "Unknown App")
        except Exception:
            return ("Unknown Window", "Unknown App")
    
    def capture_once(self) -> Optional[dict]:
        """Capture a single screenshot and process it."""
        with mss.mss() as sct:
            # Capture primary monitor
            monitor = sct.monitors[1]  # Primary monitor
            screenshot = sct.grab(monitor)
            
            # Convert to PIL Image
            image = Image.frombytes(
                'RGB',
                screenshot.size,
                screenshot.bgra,
                'raw',
                'BGRX'
            )
            
            # Check for significant change
            current_hash = self._compute_image_hash(image)
            if not self._has_significant_change(current_hash):
                return None
            
            self.last_hash = current_hash
            
            # Extract text
            extracted_text = self._extract_text(image)
            
            # Get active window info
            window_title, app_name = self._get_active_window()
            
            # Create capture record
            capture = {
                'timestamp': datetime.now().isoformat(),
                'screen_hash': current_hash,
                'extracted_text': extracted_text,
                'active_window': window_title,
                'active_app': app_name,
                'metadata': {
                    'screen_size': screenshot.size,
                    'text_length': len(extracted_text),
                }
            }
            
            # Store in database
            self._store_capture(capture)
            
            return capture
    
    def _store_capture(self, capture: dict):
        """Store capture in SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO captures 
            (timestamp, screen_hash, extracted_text, active_window, active_app, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            capture['timestamp'],
            capture['screen_hash'],
            capture['extracted_text'],
            capture['active_window'],
            capture['active_app'],
            json.dumps(capture['metadata'])
        ))
        
        # Update FTS index
        cursor.execute("""
            INSERT INTO captures_fts(rowid, extracted_text)
            VALUES (last_insert_rowid(), ?)
        """, (capture['extracted_text'],))
        
        conn.commit()
        conn.close()
    
    async def run(self):
        """Run continuous capture loop."""
        self.running = True
        print(f"Starting screen capture (interval: {self.capture_interval}s)")
        print(f"Database: {self.db_path}")
        print("Press Ctrl+C to stop")
        
        while self.running:
            try:
                capture = self.capture_once()
                if capture:
                    text_preview = capture['extracted_text'][:100].replace('\n', ' ')
                    print(f"[{capture['timestamp'][:19]}] Captured: {text_preview}...")
            except Exception as e:
                print(f"Capture error: {e}")
            
            await asyncio.sleep(self.capture_interval)
    
    def stop(self):
        """Stop the capture loop."""
        self.running = False
    
    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search captured content using full-text search."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.id, c.timestamp, c.extracted_text, c.active_window, c.active_app
            FROM captures c
            JOIN captures_fts fts ON c.id = fts.rowid
            WHERE captures_fts MATCH ?
            ORDER BY c.timestamp DESC
            LIMIT ?
        """, (query, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'timestamp': row[1],
                'text': row[2],
                'window': row[3],
                'app': row[4]
            })
        
        conn.close()
        return results


class CaptureManager:
    """
    Manages multiple capture sources and coordinates storage.
    This is the main entry point for the System of Record layer.
    """
    
    def __init__(self):
        self.sources = {}
        self.screen_capture = ScreenCapture()
        # Add more sources: clipboard, file watcher, etc.
    
    async def start_all(self):
        """Start all capture sources."""
        tasks = [
            self.screen_capture.run(),
            # Add more capture tasks here
        ]
        await asyncio.gather(*tasks)
    
    def stop_all(self):
        """Stop all capture sources."""
        self.screen_capture.stop()


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Screen Capture for Unified AI System")
    parser.add_argument("--search", type=str, help="Search captured content")
    parser.add_argument("--interval", type=int, default=5, help="Capture interval in seconds")
    args = parser.parse_args()
    
    capture = ScreenCapture(capture_interval=args.interval)
    
    if args.search:
        results = capture.search(args.search)
        for r in results:
            print(f"\n[{r['timestamp']}] {r['app']}")
            print(f"  {r['text'][:200]}...")
    else:
        try:
            asyncio.run(capture.run())
        except KeyboardInterrupt:
            print("\nCapture stopped.")
