"""Onboarding state management for user setup flow.

This module tracks onboarding progress including:
- Account creation
- Desktop app download and installation
- Chrome extension installation
- Data collection sync status
"""

import sqlite3
import secrets
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Literal


class OnboardingStep(str, Enum):
    """Onboarding steps in order."""
    SIGNUP = "signup"
    EMAIL_VERIFIED = "email_verified"
    DESKTOP_DOWNLOADED = "desktop_downloaded"
    DESKTOP_INSTALLED = "desktop_installed"
    EXTENSION_INSTALLED = "extension_installed"
    COMPLETED = "completed"


@dataclass
class DeviceInfo:
    """Registered desktop device information."""
    id: int
    user_id: int
    device_id: str
    device_name: str
    platform: str  # 'windows', 'macos', 'linux'
    version: str
    registered_at: str
    last_seen_at: str
    is_active: bool
    capture_enabled: bool
    clipboard_enabled: bool
    file_watcher_enabled: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExtensionInfo:
    """Registered Chrome extension information."""
    id: int
    user_id: int
    extension_id: str
    version: str
    browser: str  # 'chrome', 'firefox', 'edge'
    registered_at: str
    last_seen_at: str
    is_active: bool
    history_enabled: bool
    tabs_enabled: bool
    bookmarks_enabled: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OnboardingState:
    """Current onboarding state for a user."""
    user_id: int
    current_step: OnboardingStep
    signup_completed: bool
    email_verified: bool
    desktop_downloaded: bool
    desktop_installed: bool
    extension_installed: bool
    completed_at: Optional[str]
    devices: List[DeviceInfo]
    extensions: List[ExtensionInfo]

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "current_step": self.current_step.value,
            "signup_completed": self.signup_completed,
            "email_verified": self.email_verified,
            "desktop_downloaded": self.desktop_downloaded,
            "desktop_installed": self.desktop_installed,
            "extension_installed": self.extension_installed,
            "completed_at": self.completed_at,
            "devices": [d.to_dict() for d in self.devices],
            "extensions": [e.to_dict() for e in self.extensions],
            "all_synced": self.is_all_synced(),
            "sync_status": self.get_sync_status(),
        }

    def is_all_synced(self) -> bool:
        """Check if all data collection methods are active and synced."""
        has_active_device = any(d.is_active for d in self.devices)
        has_active_extension = any(e.is_active for e in self.extensions)
        return has_active_device and has_active_extension

    def get_sync_status(self) -> dict:
        """Get detailed sync status for each data collection method."""
        active_device = next((d for d in self.devices if d.is_active), None)
        active_extension = next((e for e in self.extensions if e.is_active), None)

        return {
            "screen_capture": {
                "enabled": active_device.capture_enabled if active_device else False,
                "status": "active" if active_device and active_device.capture_enabled else "inactive",
            },
            "clipboard": {
                "enabled": active_device.clipboard_enabled if active_device else False,
                "status": "active" if active_device and active_device.clipboard_enabled else "inactive",
            },
            "file_watcher": {
                "enabled": active_device.file_watcher_enabled if active_device else False,
                "status": "active" if active_device and active_device.file_watcher_enabled else "inactive",
            },
            "browser_history": {
                "enabled": active_extension.history_enabled if active_extension else False,
                "status": "active" if active_extension and active_extension.history_enabled else "inactive",
            },
            "browser_tabs": {
                "enabled": active_extension.tabs_enabled if active_extension else False,
                "status": "active" if active_extension and active_extension.tabs_enabled else "inactive",
            },
            "browser_bookmarks": {
                "enabled": active_extension.bookmarks_enabled if active_extension else False,
                "status": "active" if active_extension and active_extension.bookmarks_enabled else "inactive",
            },
        }


class OnboardingManager:
    """Manages user onboarding state and device/extension registration.

    Args:
        db_path: Path to SQLite database. Defaults to ~/.unified-ai/onboarding.db
    """

    def __init__(self, db_path: Path = Path("~/.unified-ai/onboarding.db").expanduser()):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            # Onboarding state table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS onboarding_state (
                    user_id INTEGER PRIMARY KEY,
                    current_step TEXT NOT NULL DEFAULT 'signup',
                    signup_completed INTEGER DEFAULT 1,
                    email_verified INTEGER DEFAULT 0,
                    desktop_downloaded INTEGER DEFAULT 0,
                    desktop_installed INTEGER DEFAULT 0,
                    extension_installed INTEGER DEFAULT 0,
                    completed_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Registered desktop devices
            conn.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    device_id TEXT UNIQUE NOT NULL,
                    device_name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    version TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    capture_enabled INTEGER DEFAULT 1,
                    clipboard_enabled INTEGER DEFAULT 1,
                    file_watcher_enabled INTEGER DEFAULT 1
                )
            """)

            # Registered browser extensions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS extensions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    extension_id TEXT UNIQUE NOT NULL,
                    version TEXT NOT NULL,
                    browser TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    history_enabled INTEGER DEFAULT 1,
                    tabs_enabled INTEGER DEFAULT 1,
                    bookmarks_enabled INTEGER DEFAULT 1
                )
            """)

            # Download tokens for tracking downloads
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    platform TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    used_at TEXT,
                    expires_at TEXT NOT NULL
                )
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_devices_user ON devices (user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_extensions_user ON extensions (user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_download_tokens_token ON download_tokens (token)")
            conn.commit()

    def create_onboarding(self, user_id: int) -> OnboardingState:
        """Create initial onboarding state for a new user.

        Args:
            user_id: User's ID

        Returns:
            Created OnboardingState
        """
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO onboarding_state
                (user_id, current_step, signup_completed, created_at, updated_at)
                VALUES (?, 'signup', 1, ?, ?)
            """, (user_id, now, now))
            conn.commit()

        return self.get_onboarding_state(user_id)

    def get_onboarding_state(self, user_id: int) -> OnboardingState:
        """Get current onboarding state for a user.

        Args:
            user_id: User's ID

        Returns:
            OnboardingState object
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get onboarding state
            row = conn.execute(
                "SELECT * FROM onboarding_state WHERE user_id = ?", (user_id,)
            ).fetchone()

            if not row:
                return self.create_onboarding(user_id)

            # Get devices
            devices = []
            for d in conn.execute("SELECT * FROM devices WHERE user_id = ?", (user_id,)):
                devices.append(DeviceInfo(
                    id=d["id"],
                    user_id=d["user_id"],
                    device_id=d["device_id"],
                    device_name=d["device_name"],
                    platform=d["platform"],
                    version=d["version"],
                    registered_at=d["registered_at"],
                    last_seen_at=d["last_seen_at"],
                    is_active=bool(d["is_active"]),
                    capture_enabled=bool(d["capture_enabled"]),
                    clipboard_enabled=bool(d["clipboard_enabled"]),
                    file_watcher_enabled=bool(d["file_watcher_enabled"]),
                ))

            # Get extensions
            extensions = []
            for e in conn.execute("SELECT * FROM extensions WHERE user_id = ?", (user_id,)):
                extensions.append(ExtensionInfo(
                    id=e["id"],
                    user_id=e["user_id"],
                    extension_id=e["extension_id"],
                    version=e["version"],
                    browser=e["browser"],
                    registered_at=e["registered_at"],
                    last_seen_at=e["last_seen_at"],
                    is_active=bool(e["is_active"]),
                    history_enabled=bool(e["history_enabled"]),
                    tabs_enabled=bool(e["tabs_enabled"]),
                    bookmarks_enabled=bool(e["bookmarks_enabled"]),
                ))

            return OnboardingState(
                user_id=row["user_id"],
                current_step=OnboardingStep(row["current_step"]),
                signup_completed=bool(row["signup_completed"]),
                email_verified=bool(row["email_verified"]),
                desktop_downloaded=bool(row["desktop_downloaded"]),
                desktop_installed=bool(row["desktop_installed"]),
                extension_installed=bool(row["extension_installed"]),
                completed_at=row["completed_at"],
                devices=devices,
                extensions=extensions,
            )

    def update_step(self, user_id: int, step: OnboardingStep) -> OnboardingState:
        """Update onboarding step and related flags.

        Args:
            user_id: User's ID
            step: New onboarding step

        Returns:
            Updated OnboardingState
        """
        now = datetime.utcnow().isoformat()
        updates = {"current_step": step.value, "updated_at": now}

        # Set appropriate flags based on step
        if step == OnboardingStep.EMAIL_VERIFIED:
            updates["email_verified"] = 1
        elif step == OnboardingStep.DESKTOP_DOWNLOADED:
            updates["desktop_downloaded"] = 1
        elif step == OnboardingStep.DESKTOP_INSTALLED:
            updates["desktop_installed"] = 1
        elif step == OnboardingStep.EXTENSION_INSTALLED:
            updates["extension_installed"] = 1
        elif step == OnboardingStep.COMPLETED:
            updates["completed_at"] = now

        with sqlite3.connect(self.db_path) as conn:
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            conn.execute(
                f"UPDATE onboarding_state SET {set_clause} WHERE user_id = ?",
                (*updates.values(), user_id)
            )
            conn.commit()

        return self.get_onboarding_state(user_id)

    def mark_email_verified(self, user_id: int) -> OnboardingState:
        """Mark email as verified.

        Args:
            user_id: User's ID

        Returns:
            Updated OnboardingState
        """
        return self.update_step(user_id, OnboardingStep.EMAIL_VERIFIED)

    def create_download_token(
        self,
        user_id: int,
        platform: Literal["windows", "macos", "linux"]
    ) -> str:
        """Create a download token for tracking desktop app downloads.

        Args:
            user_id: User's ID
            platform: Target platform

        Returns:
            Download token
        """
        from datetime import timedelta

        token = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=24)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO download_tokens (user_id, token, platform, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, token, platform, now.isoformat(), expires_at.isoformat()))
            conn.commit()

        return token

    def validate_download_token(self, token: str) -> Optional[dict]:
        """Validate a download token and mark it as used.

        Args:
            token: Download token

        Returns:
            Token info if valid, None otherwise
        """
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM download_tokens
                WHERE token = ? AND expires_at > ? AND used_at IS NULL
            """, (token, now)).fetchone()

            if row:
                # Mark as used
                conn.execute(
                    "UPDATE download_tokens SET used_at = ? WHERE token = ?",
                    (now, token)
                )
                conn.commit()

                # Update onboarding state
                self.update_step(row["user_id"], OnboardingStep.DESKTOP_DOWNLOADED)

                return {
                    "user_id": row["user_id"],
                    "platform": row["platform"],
                }
        return None

    def register_device(
        self,
        user_id: int,
        device_name: str,
        platform: str,
        version: str
    ) -> DeviceInfo:
        """Register a new desktop device.

        Args:
            user_id: User's ID
            device_name: Human-readable device name
            platform: Platform (windows, macos, linux)
            version: App version

        Returns:
            Created DeviceInfo
        """
        device_id = secrets.token_urlsafe(16)
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO devices
                (user_id, device_id, device_name, platform, version, registered_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, device_id, device_name, platform, version, now, now))
            conn.commit()

            # Update onboarding state
            self.update_step(user_id, OnboardingStep.DESKTOP_INSTALLED)

            return DeviceInfo(
                id=cursor.lastrowid,
                user_id=user_id,
                device_id=device_id,
                device_name=device_name,
                platform=platform,
                version=version,
                registered_at=now,
                last_seen_at=now,
                is_active=True,
                capture_enabled=True,
                clipboard_enabled=True,
                file_watcher_enabled=True,
            )

    def update_device_heartbeat(self, device_id: str) -> bool:
        """Update device last seen timestamp.

        Args:
            device_id: Device ID

        Returns:
            True if device found and updated
        """
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "UPDATE devices SET last_seen_at = ?, is_active = 1 WHERE device_id = ?",
                (now, device_id)
            )
            conn.commit()
            return result.rowcount > 0

    def update_device_settings(
        self,
        device_id: str,
        capture_enabled: Optional[bool] = None,
        clipboard_enabled: Optional[bool] = None,
        file_watcher_enabled: Optional[bool] = None
    ) -> bool:
        """Update device capture settings.

        Args:
            device_id: Device ID
            capture_enabled: Screen capture enabled
            clipboard_enabled: Clipboard monitoring enabled
            file_watcher_enabled: File watching enabled

        Returns:
            True if device found and updated
        """
        updates = {}
        if capture_enabled is not None:
            updates["capture_enabled"] = int(capture_enabled)
        if clipboard_enabled is not None:
            updates["clipboard_enabled"] = int(clipboard_enabled)
        if file_watcher_enabled is not None:
            updates["file_watcher_enabled"] = int(file_watcher_enabled)

        if not updates:
            return False

        with sqlite3.connect(self.db_path) as conn:
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            result = conn.execute(
                f"UPDATE devices SET {set_clause} WHERE device_id = ?",
                (*updates.values(), device_id)
            )
            conn.commit()
            return result.rowcount > 0

    def register_extension(
        self,
        user_id: int,
        version: str,
        browser: Literal["chrome", "firefox", "edge"] = "chrome"
    ) -> ExtensionInfo:
        """Register a new browser extension.

        Args:
            user_id: User's ID
            version: Extension version
            browser: Browser type

        Returns:
            Created ExtensionInfo
        """
        extension_id = secrets.token_urlsafe(16)
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO extensions
                (user_id, extension_id, version, browser, registered_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, extension_id, version, browser, now, now))
            conn.commit()

            # Update onboarding state
            self.update_step(user_id, OnboardingStep.EXTENSION_INSTALLED)

            # Check if onboarding is complete
            state = self.get_onboarding_state(user_id)
            if state.desktop_installed and state.extension_installed:
                self.update_step(user_id, OnboardingStep.COMPLETED)

            return ExtensionInfo(
                id=cursor.lastrowid,
                user_id=user_id,
                extension_id=extension_id,
                version=version,
                browser=browser,
                registered_at=now,
                last_seen_at=now,
                is_active=True,
                history_enabled=True,
                tabs_enabled=True,
                bookmarks_enabled=True,
            )

    def update_extension_heartbeat(self, extension_id: str) -> bool:
        """Update extension last seen timestamp.

        Args:
            extension_id: Extension ID

        Returns:
            True if extension found and updated
        """
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "UPDATE extensions SET last_seen_at = ?, is_active = 1 WHERE extension_id = ?",
                (now, extension_id)
            )
            conn.commit()
            return result.rowcount > 0

    def update_extension_settings(
        self,
        extension_id: str,
        history_enabled: Optional[bool] = None,
        tabs_enabled: Optional[bool] = None,
        bookmarks_enabled: Optional[bool] = None
    ) -> bool:
        """Update extension capture settings.

        Args:
            extension_id: Extension ID
            history_enabled: Browser history capture enabled
            tabs_enabled: Tab tracking enabled
            bookmarks_enabled: Bookmarks sync enabled

        Returns:
            True if extension found and updated
        """
        updates = {}
        if history_enabled is not None:
            updates["history_enabled"] = int(history_enabled)
        if tabs_enabled is not None:
            updates["tabs_enabled"] = int(tabs_enabled)
        if bookmarks_enabled is not None:
            updates["bookmarks_enabled"] = int(bookmarks_enabled)

        if not updates:
            return False

        with sqlite3.connect(self.db_path) as conn:
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            result = conn.execute(
                f"UPDATE extensions SET {set_clause} WHERE extension_id = ?",
                (*updates.values(), extension_id)
            )
            conn.commit()
            return result.rowcount > 0

    def get_sync_summary(self, user_id: int) -> dict:
        """Get a summary of all data collection sync status.

        Args:
            user_id: User's ID

        Returns:
            Sync status summary
        """
        state = self.get_onboarding_state(user_id)
        sync_status = state.get_sync_status()

        active_sources = sum(1 for s in sync_status.values() if s["enabled"])
        total_sources = len(sync_status)

        return {
            "user_id": user_id,
            "onboarding_complete": state.current_step == OnboardingStep.COMPLETED,
            "all_synced": state.is_all_synced(),
            "active_sources": active_sources,
            "total_sources": total_sources,
            "completion_percentage": int((active_sources / total_sources) * 100),
            "sources": sync_status,
            "devices": [d.to_dict() for d in state.devices],
            "extensions": [e.to_dict() for e in state.extensions],
        }
