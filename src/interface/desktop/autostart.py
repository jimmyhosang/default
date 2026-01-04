"""
Auto-Start Configuration for Unified AI System.
Configures the app to launch automatically on system login.
"""
import os
import sys
from pathlib import Path
import platform

APP_ID = "com.unifiedai.system"
APP_NAME = "Unified AI System"


def get_launch_command() -> str:
    """Get the command to launch the app."""
    # When running as bundled app, use the app bundle
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        # Running from source
        project_root = Path(__file__).parent.parent.parent.parent
        python = project_root / "venv" / "bin" / "python"
        script = project_root / "src" / "interface" / "desktop" / "app.py"
        return f'"{python}" "{script}"'


def enable_autostart_macos() -> bool:
    """Enable auto-start on macOS using LaunchAgents."""
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)
    
    plist_path = launch_agents_dir / f"{APP_ID}.plist"
    command = get_launch_command()
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{APP_ID}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/sh</string>
        <string>-c</string>
        <string>{command}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>{Path.home()}/.unified-ai/launch.log</string>
    <key>StandardErrorPath</key>
    <string>{Path.home()}/.unified-ai/launch.err</string>
</dict>
</plist>
"""
    
    try:
        plist_path.write_text(plist_content)
        # Load the launch agent
        os.system(f'launchctl load "{plist_path}"')
        print(f"✓ Auto-start enabled: {plist_path}")
        return True
    except Exception as e:
        print(f"✗ Failed to enable auto-start: {e}")
        return False


def disable_autostart_macos() -> bool:
    """Disable auto-start on macOS."""
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{APP_ID}.plist"
    
    try:
        if plist_path.exists():
            os.system(f'launchctl unload "{plist_path}"')
            plist_path.unlink()
            print(f"✓ Auto-start disabled")
        return True
    except Exception as e:
        print(f"✗ Failed to disable auto-start: {e}")
        return False


def is_autostart_enabled() -> bool:
    """Check if auto-start is currently enabled."""
    if platform.system() == "Darwin":
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{APP_ID}.plist"
        return plist_path.exists()
    return False


def enable_autostart() -> bool:
    """Enable auto-start for current platform."""
    system = platform.system()
    if system == "Darwin":
        return enable_autostart_macos()
    elif system == "Linux":
        # Linux: Use ~/.config/autostart desktop file
        print("Linux auto-start not yet implemented")
        return False
    elif system == "Windows":
        # Windows: Use registry or Start Menu startup folder
        print("Windows auto-start not yet implemented")
        return False
    return False


def disable_autostart() -> bool:
    """Disable auto-start for current platform."""
    system = platform.system()
    if system == "Darwin":
        return disable_autostart_macos()
    return False


def toggle_autostart() -> bool:
    """Toggle auto-start state."""
    if is_autostart_enabled():
        return disable_autostart()
    else:
        return enable_autostart()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Manage auto-start configuration")
    parser.add_argument("action", choices=["enable", "disable", "toggle", "status"])
    args = parser.parse_args()
    
    if args.action == "enable":
        enable_autostart()
    elif args.action == "disable":
        disable_autostart()
    elif args.action == "toggle":
        toggle_autostart()
    elif args.action == "status":
        print(f"Auto-start enabled: {is_autostart_enabled()}")
