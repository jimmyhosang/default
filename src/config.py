"""
Centralized Configuration System for Unified AI System

This module provides a single source of truth for all configuration values.
Configuration is loaded from:
1. Default values (hardcoded)
2. Environment variables
3. Settings file (~/.unified-ai/settings.json)

Priority: Settings file > Environment variables > Defaults
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


# === Default Configuration Values ===

@dataclass
class CaptureConfig:
    """Configuration for capture modules."""
    screen_interval: int = 5  # seconds between captures
    screen_min_change_threshold: float = 0.1  # 10% pixel change to store
    clipboard_poll_interval: float = 0.5  # seconds between clipboard checks
    clipboard_max_size: int = 1024 * 1024  # 1MB max clipboard content
    file_watch_directories: List[str] = field(default_factory=lambda: [
        str(Path.home() / "Documents"),
        str(Path.home() / "Desktop"),
        str(Path.home() / "Downloads"),
    ])
    file_max_size: int = 10 * 1024 * 1024  # 10MB max file size
    file_extensions: List[str] = field(default_factory=lambda: [
        ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
        ".html", ".css", ".xml", ".csv", ".pdf", ".docx", ".doc"
    ])


@dataclass
class StorageConfig:
    """Configuration for storage layer."""
    db_path: Path = field(default_factory=lambda: Path.home() / ".unified-ai" / "capture.db")
    vector_db_path: Path = field(default_factory=lambda: Path.home() / ".unified-ai" / "lancedb")
    max_records: int = 10000  # Maximum records before cleanup
    max_age_days: int = 90  # Days before automatic cleanup
    auto_cleanup: bool = True


@dataclass
class LLMConfig:
    """Configuration for LLM integration."""
    provider: str = "ollama"  # ollama, anthropic, openai
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_temperature: float = 0.7
    max_tokens: int = 4096
    # Model routing
    fast_model: str = "llama3.2:3b"
    balanced_model: str = "mistral"
    powerful_model: str = "claude-3-5-sonnet-20241022"


@dataclass
class ServerConfig:
    """Configuration for dashboard server."""
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: List[str] = field(default_factory=lambda: [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ])


@dataclass
class PrivacyConfig:
    """Configuration for privacy features."""
    enable_pii_detection: bool = True
    redact_emails: bool = True
    redact_phone_numbers: bool = True
    redact_credit_cards: bool = True
    redact_ssn: bool = True
    excluded_apps: List[str] = field(default_factory=lambda: [
        "1Password", "Bitwarden", "LastPass", "KeePass",
        "Terminal", "iTerm", "Keychain Access"
    ])
    excluded_windows: List[str] = field(default_factory=lambda: [
        "Private", "Incognito", "password", "credential"
    ])


@dataclass
class UIConfig:
    """Configuration for UI settings."""
    theme: str = "auto"  # auto, light, dark
    start_minimized: bool = False
    show_notifications: bool = True
    timeline_page_size: int = 50


@dataclass
class Config:
    """Main configuration container."""
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    ui: UIConfig = field(default_factory=UIConfig)


# === Configuration Loading ===

SETTINGS_FILE = Path.home() / ".unified-ai" / "settings.json"


def _load_from_env(config: Config) -> None:
    """Load configuration from environment variables."""
    # LLM config
    if os.environ.get("ANTHROPIC_API_KEY"):
        config.llm.anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]
    if os.environ.get("OPENAI_API_KEY"):
        config.llm.openai_api_key = os.environ["OPENAI_API_KEY"]
    if os.environ.get("OLLAMA_URL"):
        config.llm.ollama_url = os.environ["OLLAMA_URL"]

    # Server config
    if os.environ.get("UNIFIED_AI_HOST"):
        config.server.host = os.environ["UNIFIED_AI_HOST"]
    if os.environ.get("UNIFIED_AI_PORT"):
        config.server.port = int(os.environ["UNIFIED_AI_PORT"])

    # Storage config
    if os.environ.get("UNIFIED_AI_DB_PATH"):
        config.storage.db_path = Path(os.environ["UNIFIED_AI_DB_PATH"])


def _load_from_file(config: Config) -> None:
    """Load configuration from settings file."""
    if not SETTINGS_FILE.exists():
        return

    try:
        settings = json.loads(SETTINGS_FILE.read_text())

        # Capture settings
        if "capture" in settings:
            cap = settings["capture"]
            if "screen_interval" in cap:
                config.capture.screen_interval = cap["screen_interval"]
            if "clipboard_enabled" in cap:
                pass  # Boolean flag, not interval
            if "watch_directories" in cap:
                config.capture.file_watch_directories = [
                    str(Path(d).expanduser()) for d in cap["watch_directories"]
                ]

        # Storage settings
        if "storage" in settings:
            stor = settings["storage"]
            if "max_captures" in stor:
                config.storage.max_records = stor["max_captures"]
            if "max_days" in stor:
                config.storage.max_age_days = stor["max_days"]
            if "auto_cleanup" in stor:
                config.storage.auto_cleanup = stor["auto_cleanup"]

        # LLM settings
        if "llm" in settings:
            llm = settings["llm"]
            if "provider" in llm:
                config.llm.provider = llm["provider"]
            if "ollama_model" in llm:
                config.llm.ollama_model = llm["ollama_model"]
            if "ollama_url" in llm:
                config.llm.ollama_url = llm["ollama_url"]
            if "anthropic_api_key" in llm and llm["anthropic_api_key"]:
                config.llm.anthropic_api_key = llm["anthropic_api_key"]
            if "openai_api_key" in llm and llm["openai_api_key"]:
                config.llm.openai_api_key = llm["openai_api_key"]

        # UI settings
        if "ui" in settings:
            ui = settings["ui"]
            if "theme" in ui:
                config.ui.theme = ui["theme"]
            if "start_minimized" in ui:
                config.ui.start_minimized = ui["start_minimized"]
            if "show_notifications" in ui:
                config.ui.show_notifications = ui["show_notifications"]

    except Exception as e:
        logger.warning(f"Failed to load settings file: {e}")


def load_config() -> Config:
    """
    Load configuration from all sources.

    Priority: Settings file > Environment variables > Defaults
    """
    config = Config()

    # Load from environment first
    _load_from_env(config)

    # Load from file (overrides env)
    _load_from_file(config)

    return config


def save_config(config: Config) -> bool:
    """Save configuration to settings file."""
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

        settings = {
            "capture": {
                "screen_interval": config.capture.screen_interval,
                "clipboard_enabled": True,
                "file_watch_enabled": True,
                "watch_directories": config.capture.file_watch_directories,
            },
            "storage": {
                "max_captures": config.storage.max_records,
                "max_days": config.storage.max_age_days,
                "auto_cleanup": config.storage.auto_cleanup,
            },
            "llm": {
                "provider": config.llm.provider,
                "ollama_model": config.llm.ollama_model,
                "ollama_url": config.llm.ollama_url,
                "anthropic_api_key": config.llm.anthropic_api_key,
                "openai_api_key": config.llm.openai_api_key,
            },
            "ui": {
                "theme": config.ui.theme,
                "start_minimized": config.ui.start_minimized,
                "show_notifications": config.ui.show_notifications,
            }
        }

        SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
        return True
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        return False


# === Global Config Instance ===

_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> Config:
    """Reload configuration from sources."""
    global _config
    _config = load_config()
    return _config
