"""
Desktop Wrapper for Unified AI System.
Launches a native window with system tray integration.
"""
import sys
import threading
import time
import webview
import uvicorn
from pathlib import Path

# Add project root to path if running from source
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.interface.dashboard.server import app
from src.interface.desktop.tray import TrayIcon
from src.interface.desktop.autostart import is_autostart_enabled, toggle_autostart

PORT = 8000
HOST = "127.0.0.1"
URL = f"http://{HOST}:{PORT}"

# Global references
window = None
tray = None
server_thread = None


def start_server():
    """Start the FastAPI server in a separate thread."""
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="error")
    server = uvicorn.Server(config)
    server.run()


def show_window():
    """Show or focus the main window."""
    global window
    if window:
        try:
            window.show()
            window.restore()  # Unminimize if needed
        except Exception:
            pass


def on_quit():
    """Handle quit from tray."""
    global window
    if window:
        try:
            window.destroy()
        except Exception:
            pass
    sys.exit(0)


def on_window_close():
    """When window is closed, minimize to tray instead of quitting."""
    global window
    if window:
        window.hide()
    return False  # Prevent actual close


def main():
    """Main entry point with system tray integration."""
    global window, tray, server_thread
    
    print(f"🚀 Starting Unified AI System on {URL}...")
    print(f"📌 Auto-start on login: {'Enabled' if is_autostart_enabled() else 'Disabled'}")
    
    # Start server thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(1.5)
    
    # Create system tray icon
    tray = TrayIcon(
        on_show_window=show_window,
        on_quit=on_quit
    )
    tray.run_detached()
    print("✓ System tray icon active")
    
    # Create window
    window = webview.create_window(
        title='Unified AI System',
        url=URL,
        width=1280,
        height=800,
        resizable=True,
        min_size=(1024, 768),
        confirm_close=True
    )
    
    # Override close to minimize to tray
    window.events.closing += on_window_close
    
    print("✓ Window created")
    print("\n💡 Tip: Close the window to minimize to tray. Use tray icon to quit.\n")
    
    # Start webview (this blocks until app exits)
    webview.start(debug=False)


def main_minimal():
    """Minimal mode - tray only, no window on startup."""
    global tray, server_thread
    
    print(f"🚀 Starting Unified AI System (tray mode) on {URL}...")
    
    # Start server thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    time.sleep(1.5)
    
    # Create and run system tray (blocks)
    tray = TrayIcon(
        on_show_window=lambda: webview.create_window("Unified AI", URL, width=1280, height=800),
        on_quit=lambda: sys.exit(0)
    )
    
    print("✓ System tray mode active - use tray icon to show window")
    tray.run()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Unified AI System Desktop App")
    parser.add_argument("--tray", action="store_true", help="Start in tray-only mode")
    parser.add_argument("--enable-autostart", action="store_true", help="Enable auto-start on login")
    parser.add_argument("--disable-autostart", action="store_true", help="Disable auto-start")
    args = parser.parse_args()
    
    if args.enable_autostart:
        from src.interface.desktop.autostart import enable_autostart
        enable_autostart()
    elif args.disable_autostart:
        from src.interface.desktop.autostart import disable_autostart
        disable_autostart()
    elif args.tray:
        main_minimal()
    else:
        main()
