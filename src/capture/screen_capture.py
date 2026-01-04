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
import platform
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Note: Install these dependencies:
# pip install mss pytesseract pillow

try:
    import mss
    import pytesseract
    from PIL import Image
except ImportError:
    print("Install dependencies: pip install mss pytesseract pillow")
    raise


class CaptureMode(Enum):
    """Screen capture mode options."""
    PRIMARY = "primary"       # Capture primary monitor only
    ALL = "all"               # Capture all monitors
    SPECIFIC = "specific"     # Capture specific monitor by index
    COMBINED = "combined"     # Capture all monitors as single stitched image


@dataclass
class MonitorInfo:
    """Information about a single monitor."""
    index: int
    left: int
    top: int
    width: int
    height: int
    is_primary: bool = False
    name: str = ""

    @property
    def size(self) -> Tuple[int, int]:
        return (self.width, self.height)

    @property
    def position(self) -> Tuple[int, int]:
        return (self.left, self.top)


@dataclass
class CaptureResult:
    """Result from a multi-monitor capture."""
    monitor_index: int
    image: Image.Image
    hash: str
    timestamp: str
    extracted_text: str
    window_title: str
    app_name: str
    monitor_info: MonitorInfo


def get_monitors() -> List[MonitorInfo]:
    """Get information about all available monitors."""
    monitors = []
    with mss.mss() as sct:
        # sct.monitors[0] is the "all monitors" virtual screen
        # sct.monitors[1:] are individual monitors
        for i, mon in enumerate(sct.monitors[1:], start=1):
            monitors.append(MonitorInfo(
                index=i,
                left=mon["left"],
                top=mon["top"],
                width=mon["width"],
                height=mon["height"],
                is_primary=(i == 1),
                name=f"Monitor {i}"
            ))
    return monitors


def get_monitor_count() -> int:
    """Get the number of available monitors."""
    with mss.mss() as sct:
        return len(sct.monitors) - 1  # Exclude virtual "all monitors"


def get_active_window_linux() -> Tuple[str, str]:
    """Get active window info on Linux using xdotool."""
    try:
        # Get active window ID
        window_id = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True,
            text=True,
            timeout=2
        ).stdout.strip()

        if not window_id:
            return ("Unknown Window", "Unknown App")

        # Get window title
        window_title = subprocess.run(
            ["xdotool", "getwindowname", window_id],
            capture_output=True,
            text=True,
            timeout=2
        ).stdout.strip()

        # Get window PID and then application name
        window_pid = subprocess.run(
            ["xdotool", "getwindowpid", window_id],
            capture_output=True,
            text=True,
            timeout=2
        ).stdout.strip()

        app_name = "Unknown App"
        if window_pid:
            try:
                # Get process name from /proc
                comm_path = Path(f"/proc/{window_pid}/comm")
                if comm_path.exists():
                    app_name = comm_path.read_text().strip()
            except Exception:
                pass

        return (window_title or "Unknown Window", app_name)
    except FileNotFoundError:
        logger.warning("xdotool not found. Install with: sudo apt install xdotool")
        return ("Unknown Window", "Unknown App")
    except Exception as e:
        logger.debug(f"Linux active window detection failed: {e}")
        return ("Unknown Window", "Unknown App")


def get_active_window_macos() -> Tuple[str, str]:
    """Get active window info on macOS using AppleScript."""
    try:
        # Get frontmost application name
        app_script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                return frontApp
            end tell
        '''
        app_result = subprocess.run(
            ["osascript", "-e", app_script],
            capture_output=True,
            text=True,
            timeout=2
        )
        app_name = app_result.stdout.strip() or "Unknown App"

        # Get window title (more complex, app-specific)
        title_script = f'''
            tell application "System Events"
                tell process "{app_name}"
                    try
                        set windowTitle to name of front window
                        return windowTitle
                    on error
                        return ""
                    end try
                end tell
            end tell
        '''
        title_result = subprocess.run(
            ["osascript", "-e", title_script],
            capture_output=True,
            text=True,
            timeout=2
        )
        window_title = title_result.stdout.strip() or app_name

        return (window_title, app_name)
    except Exception as e:
        logger.debug(f"macOS active window detection failed: {e}")
        return ("Unknown Window", "Unknown App")


def get_active_window_windows() -> Tuple[str, str]:
    """Get active window info on Windows using ctypes."""
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        # Get foreground window handle
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ("Unknown Window", "Unknown App")

        # Get window title
        length = user32.GetWindowTextLengthW(hwnd) + 1
        buffer = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, buffer, length)
        window_title = buffer.value or "Unknown Window"

        # Get process ID
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        # Get process name
        app_name = "Unknown App"
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010

        handle = kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
            False,
            pid.value
        )
        if handle:
            try:
                # Get executable path
                exe_path = ctypes.create_unicode_buffer(260)
                psapi = ctypes.windll.psapi
                if psapi.GetModuleBaseNameW(handle, None, exe_path, 260):
                    app_name = exe_path.value
            finally:
                kernel32.CloseHandle(handle)

        return (window_title, app_name)
    except Exception as e:
        logger.debug(f"Windows active window detection failed: {e}")
        return ("Unknown Window", "Unknown App")


def get_active_window() -> Tuple[str, str]:
    """Get active window title and application name (cross-platform)."""
    system = platform.system()

    if system == "Linux":
        return get_active_window_linux()
    elif system == "Darwin":  # macOS
        return get_active_window_macos()
    elif system == "Windows":
        return get_active_window_windows()
    else:
        logger.warning(f"Unsupported platform for active window detection: {system}")
        return ("Unknown Window", "Unknown App")


class ScreenCapture:
    """
    Captures screenshots and extracts text content.
    Designed to be efficient (<5% CPU) and privacy-conscious.
    Supports multi-monitor capture with various modes.
    """

    def __init__(
        self,
        db_path: Path = Path("~/.unified-ai/capture.db").expanduser(),
        capture_interval: int = 5,  # seconds
        min_change_threshold: float = 0.1,  # 10% pixel change to store
        capture_mode: CaptureMode = CaptureMode.PRIMARY,
        specific_monitors: Optional[List[int]] = None,  # For SPECIFIC mode
    ):
        self.db_path = db_path
        self.capture_interval = capture_interval
        self.min_change_threshold = min_change_threshold
        self.capture_mode = capture_mode
        self.specific_monitors = specific_monitors or [1]  # Default to primary

        # Track last hash per monitor for change detection
        self.last_hashes: Dict[int, str] = {}
        self.running = False

        # Cache monitor info
        self._monitors: Optional[List[MonitorInfo]] = None

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @property
    def monitors(self) -> List[MonitorInfo]:
        """Get cached monitor information."""
        if self._monitors is None:
            self._monitors = get_monitors()
        return self._monitors

    def refresh_monitors(self) -> List[MonitorInfo]:
        """Refresh and return monitor information."""
        self._monitors = get_monitors()
        return self._monitors
    
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
    
    def _has_significant_change(self, current_hash: str, monitor_index: int = 1) -> bool:
        """Check if screen content has changed significantly for a specific monitor."""
        if monitor_index not in self.last_hashes:
            return True
        return current_hash != self.last_hashes[monitor_index]
    
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
    
    def _get_active_window(self) -> Tuple[str, str]:
        """Get active window title and application name."""
        return get_active_window()
    
    def _capture_monitor(self, monitor_index: int) -> Optional[CaptureResult]:
        """Capture a single monitor by index."""
        with mss.mss() as sct:
            if monitor_index < 1 or monitor_index >= len(sct.monitors):
                logger.warning(f"Invalid monitor index: {monitor_index}")
                return None

            monitor = sct.monitors[monitor_index]
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
            if not self._has_significant_change(current_hash, monitor_index):
                return None

            self.last_hashes[monitor_index] = current_hash

            # Extract text
            extracted_text = self._extract_text(image)

            # Get active window info
            window_title, app_name = self._get_active_window()

            # Get monitor info
            monitor_info = MonitorInfo(
                index=monitor_index,
                left=monitor["left"],
                top=monitor["top"],
                width=monitor["width"],
                height=monitor["height"],
                is_primary=(monitor_index == 1),
                name=f"Monitor {monitor_index}"
            )

            return CaptureResult(
                monitor_index=monitor_index,
                image=image,
                hash=current_hash,
                timestamp=datetime.now().isoformat(),
                extracted_text=extracted_text,
                window_title=window_title,
                app_name=app_name,
                monitor_info=monitor_info
            )

    def _stitch_images(self, images: List[Tuple[Image.Image, MonitorInfo]]) -> Image.Image:
        """Stitch multiple monitor images into a single combined image."""
        if not images:
            raise ValueError("No images to stitch")

        if len(images) == 1:
            return images[0][0]

        # Calculate bounding box for all monitors
        min_left = min(info.left for _, info in images)
        min_top = min(info.top for _, info in images)
        max_right = max(info.left + info.width for _, info in images)
        max_bottom = max(info.top + info.height for _, info in images)

        # Create combined image
        combined_width = max_right - min_left
        combined_height = max_bottom - min_top
        combined = Image.new('RGB', (combined_width, combined_height), (0, 0, 0))

        # Paste each monitor image at correct position
        for img, info in images:
            x = info.left - min_left
            y = info.top - min_top
            combined.paste(img, (x, y))

        return combined

    def capture_all_monitors(self) -> List[CaptureResult]:
        """Capture all available monitors individually."""
        results = []
        monitor_count = get_monitor_count()

        for i in range(1, monitor_count + 1):
            result = self._capture_monitor(i)
            if result:
                results.append(result)

        return results

    def capture_combined(self) -> Optional[dict]:
        """Capture all monitors as a single stitched image."""
        with mss.mss() as sct:
            # Use monitor[0] which is the virtual screen containing all monitors
            monitor = sct.monitors[0]
            screenshot = sct.grab(monitor)

            # Convert to PIL Image
            image = Image.frombytes(
                'RGB',
                screenshot.size,
                screenshot.bgra,
                'raw',
                'BGRX'
            )

            # Check for significant change (use index 0 for combined)
            current_hash = self._compute_image_hash(image)
            if not self._has_significant_change(current_hash, 0):
                return None

            self.last_hashes[0] = current_hash

            # Extract text
            extracted_text = self._extract_text(image)

            # Get active window info
            window_title, app_name = self._get_active_window()

            capture = {
                'timestamp': datetime.now().isoformat(),
                'screen_hash': current_hash,
                'extracted_text': extracted_text,
                'active_window': window_title,
                'active_app': app_name,
                'metadata': {
                    'screen_size': screenshot.size,
                    'text_length': len(extracted_text),
                    'monitor_count': get_monitor_count(),
                    'capture_mode': 'combined',
                }
            }

            self._store_capture(capture)
            return capture

    def capture_once(self) -> Optional[dict]:
        """Capture screenshot(s) based on configured capture mode."""
        if self.capture_mode == CaptureMode.COMBINED:
            return self.capture_combined()

        elif self.capture_mode == CaptureMode.ALL:
            results = self.capture_all_monitors()
            if not results:
                return None

            # Store each result and return summary
            for result in results:
                capture = {
                    'timestamp': result.timestamp,
                    'screen_hash': result.hash,
                    'extracted_text': result.extracted_text,
                    'active_window': result.window_title,
                    'active_app': result.app_name,
                    'metadata': {
                        'screen_size': result.monitor_info.size,
                        'text_length': len(result.extracted_text),
                        'monitor_index': result.monitor_index,
                        'capture_mode': 'all',
                    }
                }
                self._store_capture(capture)

            # Return first result for compatibility
            first = results[0]
            return {
                'timestamp': first.timestamp,
                'screen_hash': first.hash,
                'extracted_text': first.extracted_text,
                'active_window': first.window_title,
                'active_app': first.app_name,
                'metadata': {
                    'monitors_captured': len(results),
                    'capture_mode': 'all',
                }
            }

        elif self.capture_mode == CaptureMode.SPECIFIC:
            results = []
            for monitor_idx in self.specific_monitors:
                result = self._capture_monitor(monitor_idx)
                if result:
                    results.append(result)
                    capture = {
                        'timestamp': result.timestamp,
                        'screen_hash': result.hash,
                        'extracted_text': result.extracted_text,
                        'active_window': result.window_title,
                        'active_app': result.app_name,
                        'metadata': {
                            'screen_size': result.monitor_info.size,
                            'text_length': len(result.extracted_text),
                            'monitor_index': result.monitor_index,
                            'capture_mode': 'specific',
                        }
                    }
                    self._store_capture(capture)

            if not results:
                return None

            first = results[0]
            return {
                'timestamp': first.timestamp,
                'screen_hash': first.hash,
                'extracted_text': first.extracted_text,
                'active_window': first.window_title,
                'active_app': first.app_name,
                'metadata': {
                    'monitors_captured': len(results),
                    'capture_mode': 'specific',
                }
            }

        else:  # CaptureMode.PRIMARY (default)
            result = self._capture_monitor(1)
            if not result:
                return None

            capture = {
                'timestamp': result.timestamp,
                'screen_hash': result.hash,
                'extracted_text': result.extracted_text,
                'active_window': result.window_title,
                'active_app': result.app_name,
                'metadata': {
                    'screen_size': result.monitor_info.size,
                    'text_length': len(result.extracted_text),
                    'monitor_index': 1,
                    'capture_mode': 'primary',
                }
            }

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

    def __init__(
        self,
        enable_screen: bool = True,
        enable_clipboard: bool = True,
        enable_file_watcher: bool = True
    ):
        self.sources = {}
        self.enable_screen = enable_screen
        self.enable_clipboard = enable_clipboard
        self.enable_file_watcher = enable_file_watcher

        if enable_screen:
            self.screen_capture = ScreenCapture()

        if enable_clipboard:
            from .clipboard_monitor import ClipboardMonitor
            self.clipboard_monitor = ClipboardMonitor()

        if enable_file_watcher:
            from .file_watcher import FileWatcher
            self.file_watcher = FileWatcher()

    async def start_all(self):
        """Start all capture sources."""
        tasks = []

        if self.enable_screen:
            tasks.append(self.screen_capture.run())

        if self.enable_clipboard:
            tasks.append(self.clipboard_monitor.run())

        if self.enable_file_watcher:
            tasks.append(self.file_watcher.run())

        await asyncio.gather(*tasks)

    def stop_all(self):
        """Stop all capture sources."""
        if self.enable_screen:
            self.screen_capture.stop()

        if self.enable_clipboard:
            self.clipboard_monitor.stop()

        if self.enable_file_watcher:
            self.file_watcher.stop()


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Screen Capture for Unified AI System")
    parser.add_argument("--search", type=str, help="Search captured content")
    parser.add_argument("--interval", type=int, default=5, help="Capture interval in seconds")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["primary", "all", "specific", "combined"],
        default="primary",
        help="Capture mode: primary (default), all monitors, specific monitors, or combined"
    )
    parser.add_argument(
        "--monitors",
        type=str,
        help="Comma-separated list of monitor indices for 'specific' mode (e.g., '1,2')"
    )
    parser.add_argument(
        "--list-monitors",
        action="store_true",
        help="List available monitors and exit"
    )
    args = parser.parse_args()

    # List monitors if requested
    if args.list_monitors:
        monitors = get_monitors()
        print(f"\nAvailable monitors ({len(monitors)} total):\n")
        for mon in monitors:
            primary_label = " (primary)" if mon.is_primary else ""
            print(f"  Monitor {mon.index}{primary_label}")
            print(f"    Position: ({mon.left}, {mon.top})")
            print(f"    Size: {mon.width} x {mon.height}")
            print()
        exit(0)

    # Parse capture mode
    mode_map = {
        "primary": CaptureMode.PRIMARY,
        "all": CaptureMode.ALL,
        "specific": CaptureMode.SPECIFIC,
        "combined": CaptureMode.COMBINED,
    }
    capture_mode = mode_map[args.mode]

    # Parse specific monitors
    specific_monitors = None
    if args.monitors:
        try:
            specific_monitors = [int(m.strip()) for m in args.monitors.split(",")]
        except ValueError:
            print("Error: --monitors must be comma-separated integers (e.g., '1,2')")
            exit(1)

    capture = ScreenCapture(
        capture_interval=args.interval,
        capture_mode=capture_mode,
        specific_monitors=specific_monitors
    )

    if args.search:
        results = capture.search(args.search)
        for r in results:
            print(f"\n[{r['timestamp']}] {r['app']}")
            print(f"  {r['text'][:200]}...")
    else:
        print(f"Capture mode: {args.mode}")
        if args.mode == "specific" and specific_monitors:
            print(f"Monitoring: {specific_monitors}")
        try:
            asyncio.run(capture.run())
        except KeyboardInterrupt:
            print("\nCapture stopped.")
