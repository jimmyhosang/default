#!/usr/bin/env python3
"""
Launcher script for Unified AI System.
handles dependency checks and launches the desktop app.
"""
import os
import sys
import subprocess
import shutil

def check_dependencies():
    """Check if required packages are installed."""
    try:
        import webview
        import uvicorn
        import fastapi
    except ImportError as e:
        print(f"Missing dependency: {e.name}")
        print("Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview"])

def check_frontend_build():
    """Check if frontend is built."""
    dist_dir = os.path.join("src", "interface", "web", "dist")
    if not os.path.exists(dist_dir):
        print("Frontend build not found. Building now...")
        npm_cmd = shutil.which("npm")
        if not npm_cmd:
            print("Error: npm not found. Please install Node.js to build the frontend.")
            return False
            
        web_dir = os.path.join("src", "interface", "web")
        subprocess.check_call([npm_cmd, "install"], cwd=web_dir)
        subprocess.check_call([npm_cmd, "run", "build"], cwd=web_dir)
        print("Frontend built successfully.")
    return True

if __name__ == "__main__":
    print("Initializing Unified AI System...")
    
    # 1. Check dependencies
    check_dependencies()
    
    # 2. Check frontend
    if check_frontend_build():
        # 3. Launch App
        print("Launching Desktop App...")
        # Use the current python executable to run the app module
        subprocess.call([sys.executable, "src/interface/desktop/app.py"])
    else:
        input("Press Enter to exit...")
