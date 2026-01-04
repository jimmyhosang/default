"""
Desktop Wrapper for United AI System.
Launches a native window displaying the web interface using PyWebView.
"""
import sys
import threading
import time
import webview
import uvicorn
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.interface.dashboard.server import app

PORT = 8000
HOST = "127.0.0.1"
URL = f"http://{HOST}:{PORT}"

def start_server():
    """Start the FastAPI server in a separate thread."""
    uvicorn.run(app, host=HOST, port=PORT, log_level="error")

def main():
    """Main entry point."""
    print(f"Starting Unified AI System on {URL}...")
    
    # Start server thread
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()
    
    # Wait a moment for server to start
    time.sleep(1)
    
    # Create window
    webview.create_window(
        title='Unified AI System',
        url=URL,
        width=1280,
        height=800,
        resizable=True,
        min_size=(1024, 768)
    )
    
    # Start webview (this blocks until window is closed)
    webview.start(debug=True)

if __name__ == '__main__':
    main()
