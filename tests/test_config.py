"""
Tests for the centralized configuration module.
"""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.config import (
    Config,
    CaptureConfig,
    StorageConfig,
    LLMConfig,
    ServerConfig,
    PrivacyConfig,
    UIConfig,
    load_config,
    save_config,
    get_config,
    reload_config,
    SETTINGS_FILE
)


class TestCaptureConfig:
    """Tests for capture configuration."""

    def test_default_values(self):
        """Test default capture config values."""
        config = CaptureConfig()

        assert config.screen_interval == 5
        assert config.clipboard_poll_interval == 0.5
        assert config.clipboard_max_size == 1024 * 1024
        assert config.file_max_size == 10 * 1024 * 1024

    def test_file_watch_directories(self):
        """Test default watch directories."""
        config = CaptureConfig()

        assert len(config.file_watch_directories) == 3
        assert any("Documents" in d for d in config.file_watch_directories)
        assert any("Desktop" in d for d in config.file_watch_directories)
        assert any("Downloads" in d for d in config.file_watch_directories)

    def test_file_extensions(self):
        """Test default file extensions."""
        config = CaptureConfig()

        assert ".txt" in config.file_extensions
        assert ".py" in config.file_extensions
        assert ".pdf" in config.file_extensions


class TestStorageConfig:
    """Tests for storage configuration."""

    def test_default_values(self):
        """Test default storage config values."""
        config = StorageConfig()

        assert config.max_records == 10000
        assert config.max_age_days == 90
        assert config.auto_cleanup is True

    def test_db_path(self):
        """Test database path is in home directory."""
        config = StorageConfig()

        assert ".unified-ai" in str(config.db_path)
        assert "capture.db" in str(config.db_path)


class TestLLMConfig:
    """Tests for LLM configuration."""

    def test_default_values(self):
        """Test default LLM config values."""
        config = LLMConfig()

        assert config.provider == "ollama"
        assert config.ollama_url == "http://localhost:11434"
        assert config.default_temperature == 0.7
        assert config.max_tokens == 4096

    def test_api_keys_empty_by_default(self):
        """Test API keys are empty by default."""
        config = LLMConfig()

        assert config.anthropic_api_key == ""
        assert config.openai_api_key == ""


class TestServerConfig:
    """Tests for server configuration."""

    def test_default_values(self):
        """Test default server config values."""
        config = ServerConfig()

        assert config.host == "127.0.0.1"
        assert config.port == 8000

    def test_cors_origins(self):
        """Test CORS origins include localhost."""
        config = ServerConfig()

        assert "http://localhost:8000" in config.cors_origins
        assert "http://127.0.0.1:8000" in config.cors_origins


class TestPrivacyConfig:
    """Tests for privacy configuration."""

    def test_default_values(self):
        """Test default privacy config values."""
        config = PrivacyConfig()

        assert config.enable_pii_detection is True
        assert config.redact_emails is True
        assert config.redact_credit_cards is True

    def test_excluded_apps(self):
        """Test excluded apps include password managers."""
        config = PrivacyConfig()

        assert "1Password" in config.excluded_apps
        assert "Bitwarden" in config.excluded_apps

    def test_excluded_windows(self):
        """Test excluded window patterns."""
        config = PrivacyConfig()

        assert "Private" in config.excluded_windows
        assert "Incognito" in config.excluded_windows


class TestUIConfig:
    """Tests for UI configuration."""

    def test_default_values(self):
        """Test default UI config values."""
        config = UIConfig()

        assert config.theme == "auto"
        assert config.start_minimized is False
        assert config.show_notifications is True
        assert config.timeline_page_size == 50


class TestMainConfig:
    """Tests for main Config class."""

    def test_all_subconfigs_present(self):
        """Test that all sub-configurations are present."""
        config = Config()

        assert isinstance(config.capture, CaptureConfig)
        assert isinstance(config.storage, StorageConfig)
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.server, ServerConfig)
        assert isinstance(config.privacy, PrivacyConfig)
        assert isinstance(config.ui, UIConfig)


class TestConfigLoading:
    """Tests for configuration loading."""

    def test_load_config_returns_config(self):
        """Test that load_config returns a Config object."""
        config = load_config()
        assert isinstance(config, Config)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-123"})
    def test_load_from_env_anthropic(self):
        """Test loading Anthropic key from environment."""
        config = load_config()
        assert config.llm.anthropic_api_key == "test-key-123"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "openai-test-key"})
    def test_load_from_env_openai(self):
        """Test loading OpenAI key from environment."""
        config = load_config()
        assert config.llm.openai_api_key == "openai-test-key"

    @patch.dict(os.environ, {"OLLAMA_URL": "http://custom:11434"})
    def test_load_from_env_ollama_url(self):
        """Test loading Ollama URL from environment."""
        config = load_config()
        assert config.llm.ollama_url == "http://custom:11434"

    def test_get_config_singleton(self):
        """Test that get_config returns same instance."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_reload_config(self):
        """Test that reload_config creates new instance."""
        config1 = get_config()
        config2 = reload_config()
        # After reload, get_config should return new instance
        config3 = get_config()
        assert config2 is config3


class TestConfigSaving:
    """Tests for configuration saving."""

    @patch('src.config.SETTINGS_FILE')
    def test_save_config(self, mock_settings_file):
        """Test saving configuration."""
        mock_path = MagicMock()
        mock_path.parent.mkdir = MagicMock()
        mock_path.write_text = MagicMock()

        with patch('src.config.SETTINGS_FILE', mock_path):
            config = Config()
            result = save_config(config)

            # Verify write was called
            mock_path.write_text.assert_called_once()
            call_args = mock_path.write_text.call_args[0][0]
            saved_data = json.loads(call_args)

            # Verify structure
            assert "capture" in saved_data
            assert "storage" in saved_data
            assert "llm" in saved_data
            assert "ui" in saved_data
