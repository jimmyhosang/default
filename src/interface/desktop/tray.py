"""
System Tray Module for Unified AI System.
Provides a menu bar icon with quick access to app controls.
"""
import threading
import requests
from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

API_BASE = "http://127.0.0.1:8000"


class TrayIcon:
    """System tray icon with status and controls."""
    
    def __init__(self, on_show_window=None, on_quit=None):
        self.on_show_window = on_show_window
        self.on_quit = on_quit
        self.icon = None
        self.running = True
        self._status = "stopped"  # stopped, running, partial
    
    def create_icon(self, color: str = "#808080") -> Image.Image:
        """Create a simple circular icon with the given color."""
        size = 64
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Draw outer circle
        draw.ellipse([4, 4, size-4, size-4], fill=color, outline='black', width=2)
        # Draw AI text
        draw.text((size//2-10, size//2-8), "AI", fill="white")
        return img
    
    def _get_status_color(self) -> str:
        """Get color based on daemon status."""
        if self._status == "running":
            return "#22c55e"  # Green
        elif self._status == "partial":
            return "#eab308"  # Yellow
        else:
            return "#808080"  # Gray
    
    def update_status(self):
        """Check daemon status and update icon."""
        try:
            res = requests.get(f"{API_BASE}/api/capture/status", timeout=2)
            data = res.json()
            running_count = sum(1 for d in data.values() if isinstance(d, dict) and d.get("running"))
            total = len([d for d in data.values() if isinstance(d, dict)])
            
            if running_count == total and total > 0:
                self._status = "running"
            elif running_count > 0:
                self._status = "partial"
            else:
                self._status = "stopped"
        except Exception:
            self._status = "stopped"
        
        # Update icon color
        if self.icon:
            self.icon.icon = self.create_icon(self._get_status_color())
    
    def _start_captures(self, icon, item):
        """Start all capture daemons."""
        try:
            requests.post(f"{API_BASE}/api/capture/start-all", timeout=5)
            self.update_status()
        except Exception as e:
            print(f"Failed to start captures: {e}")
    
    def _stop_captures(self, icon, item):
        """Stop all capture daemons."""
        try:
            requests.post(f"{API_BASE}/api/capture/stop-all", timeout=5)
            self.update_status()
        except Exception as e:
            print(f"Failed to stop captures: {e}")
    
    def _show_window(self, icon, item):
        """Show the main window."""
        if self.on_show_window:
            self.on_show_window()
    
    def _quit(self, icon, item):
        """Quit the application."""
        self.running = False
        icon.stop()
        if self.on_quit:
            self.on_quit()
    
    def _build_menu(self) -> Menu:
        """Build the tray menu."""
        return Menu(
            MenuItem("Show Window", self._show_window, default=True),
            Menu.SEPARATOR,
            MenuItem("Start Captures", self._start_captures),
            MenuItem("Stop Captures", self._stop_captures),
            Menu.SEPARATOR,
            MenuItem("Quit", self._quit),
        )
    
    def _status_updater(self):
        """Background thread to update status periodically."""
        import time
        while self.running:
            self.update_status()
            time.sleep(5)
    
    def run(self):
        """Start the system tray icon."""
        self.icon = Icon(
            name="UnifiedAI",
            icon=self.create_icon(),
            title="Unified AI System",
            menu=self._build_menu()
        )
        
        # Start status updater thread
        updater = threading.Thread(target=self._status_updater, daemon=True)
        updater.start()
        
        # Run icon (blocks)
        self.icon.run()
    
    def run_detached(self):
        """Run icon in background thread."""
        t = threading.Thread(target=self.run, daemon=True)
        t.start()
        return t
