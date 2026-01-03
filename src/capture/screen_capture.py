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
import logging
import signal
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

# Note: Install these dependencies:
# pip install mss pytesseract pillow
# macOS: pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz

try:
    import mss
    import pytesseract
    from PIL import Image, ImageEnhance
except ImportError:
    print("Install dependencies: pip install mss pytesseract pillow")
    raise

# Platform-specific imports
try:
    from AppKit import NSWorkspace
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID
    )
    MACOS_AVAILABLE = True
except ImportError:
    MACOS_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        """Extract text from screenshot using OCR with preprocessing."""
        try:
            # Preprocess for better OCR accuracy
            # Convert to grayscale
            gray = image.convert('L')

            # Enhance contrast
            enhancer = ImageEnhance.Contrast(gray)
            enhanced = enhancer.enhance(2.0)

            # Sharpen image
            sharpener = ImageEnhance.Sharpness(enhanced)
            sharpened = sharpener.enhance(1.5)

            # Extract text with optimized config
            # PSM 3 = Fully automatic page segmentation
            custom_config = r'--oem 3 --psm 3'
            text = pytesseract.image_to_string(sharpened, config=custom_config)
            return text.strip()
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""
    
    def _get_active_window(self) -> tuple[str, str]:
        """Get active window title and application name."""
        if MACOS_AVAILABLE:
            return self._get_active_window_macos()
        else:
            logger.warning("macOS window detection not available")
            return ("Unknown Window", "Unknown App")

    def _get_active_window_macos(self) -> tuple[str, str]:
        """Get active window on macOS using AppKit and Quartz."""
        try:
            # Get active application
            workspace = NSWorkspace.sharedWorkspace()
            active_app = workspace.activeApplication()
            app_name = active_app['NSApplicationName']

            # Get window list and find frontmost window
            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID
            )

            # Find the frontmost window for the active app
            window_title = "Unknown Window"
            for window in window_list:
                if window.get('kCGWindowOwnerName') == app_name:
                    # Layer 0 is typically the frontmost window
                    if window.get('kCGWindowLayer', 1) == 0:
                        window_title = window.get('kCGWindowName', 'Untitled')
                        if window_title:  # Found a titled window
                            break

            return (window_title, app_name)
        except Exception as e:
            logger.error(f"Failed to get active window (macOS): {e}")
            return ("Unknown Window", "Unknown App")
    
    def capture_once(self) -> Optional[dict]:
        """Capture a single screenshot and process it."""
        try:
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
                    logger.debug("No significant screen change detected")
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

                logger.info(f"Captured: {app_name} - {len(extracted_text)} chars")
                return capture
        except Exception as e:
            logger.error(f"Capture failed: {e}", exc_info=True)
            return None
    
    def _store_capture(self, capture: dict):
        """Store capture in SQLite database with transaction safety."""
        try:
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
            logger.debug("Capture stored successfully")
        except Exception as e:
            logger.error(f"Failed to store capture: {e}")
            if 'conn' in locals():
                conn.close()
    
    async def run(self):
        """Run continuous capture loop with graceful shutdown."""
        self.running = True
        logger.info(f"Starting screen capture daemon (interval: {self.capture_interval}s)")
        logger.info(f"Database: {self.db_path}")
        logger.info("Press Ctrl+C to stop")

        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        capture_count = 0
        error_count = 0

        while self.running:
            try:
                capture = self.capture_once()
                if capture:
                    capture_count += 1
                    text_preview = capture['extracted_text'][:80].replace('\n', ' ')
                    logger.info(f"[#{capture_count}] {capture['active_app']}: {text_preview}...")
            except Exception as e:
                error_count += 1
                logger.error(f"Capture error ({error_count}): {e}")
                # If too many consecutive errors, slow down
                if error_count > 5:
                    logger.warning("Multiple errors detected, increasing interval")
                    await asyncio.sleep(self.capture_interval * 2)
                    error_count = 0
                    continue

            await asyncio.sleep(self.capture_interval)

        logger.info(f"Capture daemon stopped. Total captures: {capture_count}")

    async def shutdown(self):
        """Gracefully shutdown the capture daemon."""
        logger.info("Shutting down capture daemon...")
        self.running = False

    def stop(self):
        """Stop the capture loop."""
        logger.info("Stop requested")
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
