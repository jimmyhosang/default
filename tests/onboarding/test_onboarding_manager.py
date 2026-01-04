"""Tests for onboarding state management."""

import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.onboarding.onboarding_manager import (
    OnboardingManager,
    OnboardingState,
    OnboardingStep,
    DeviceInfo,
    ExtensionInfo,
)


@pytest.fixture
def onboarding_manager():
    """Create an OnboardingManager with a temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_onboarding.db"
        yield OnboardingManager(db_path=db_path)


class TestOnboardingCreation:
    """Test onboarding state creation."""

    def test_create_onboarding(self, onboarding_manager):
        """Test creating onboarding state for a new user."""
        state = onboarding_manager.create_onboarding(user_id=1)

        assert state.user_id == 1
        assert state.current_step == OnboardingStep.SIGNUP
        assert state.signup_completed is True
        assert state.email_verified is False
        assert state.desktop_downloaded is False
        assert state.desktop_installed is False
        assert state.extension_installed is False
        assert state.devices == []
        assert state.extensions == []

    def test_get_onboarding_state_creates_if_missing(self, onboarding_manager):
        """Test that getting state creates it if missing."""
        state = onboarding_manager.get_onboarding_state(user_id=1)

        assert state is not None
        assert state.user_id == 1

    def test_onboarding_state_to_dict(self, onboarding_manager):
        """Test OnboardingState.to_dict() includes all fields."""
        state = onboarding_manager.create_onboarding(user_id=1)
        state_dict = state.to_dict()

        assert "user_id" in state_dict
        assert "current_step" in state_dict
        assert "all_synced" in state_dict
        assert "sync_status" in state_dict
        assert state_dict["current_step"] == "signup"


class TestOnboardingStepUpdates:
    """Test onboarding step updates."""

    def test_update_step_email_verified(self, onboarding_manager):
        """Test updating to email verified step."""
        onboarding_manager.create_onboarding(user_id=1)

        state = onboarding_manager.update_step(1, OnboardingStep.EMAIL_VERIFIED)

        assert state.current_step == OnboardingStep.EMAIL_VERIFIED
        assert state.email_verified is True

    def test_update_step_desktop_downloaded(self, onboarding_manager):
        """Test updating to desktop downloaded step."""
        onboarding_manager.create_onboarding(user_id=1)

        state = onboarding_manager.update_step(1, OnboardingStep.DESKTOP_DOWNLOADED)

        assert state.current_step == OnboardingStep.DESKTOP_DOWNLOADED
        assert state.desktop_downloaded is True

    def test_update_step_desktop_installed(self, onboarding_manager):
        """Test updating to desktop installed step."""
        onboarding_manager.create_onboarding(user_id=1)

        state = onboarding_manager.update_step(1, OnboardingStep.DESKTOP_INSTALLED)

        assert state.current_step == OnboardingStep.DESKTOP_INSTALLED
        assert state.desktop_installed is True

    def test_update_step_extension_installed(self, onboarding_manager):
        """Test updating to extension installed step."""
        onboarding_manager.create_onboarding(user_id=1)

        state = onboarding_manager.update_step(1, OnboardingStep.EXTENSION_INSTALLED)

        assert state.current_step == OnboardingStep.EXTENSION_INSTALLED
        assert state.extension_installed is True

    def test_update_step_completed(self, onboarding_manager):
        """Test updating to completed step."""
        onboarding_manager.create_onboarding(user_id=1)

        state = onboarding_manager.update_step(1, OnboardingStep.COMPLETED)

        assert state.current_step == OnboardingStep.COMPLETED
        assert state.completed_at is not None

    def test_mark_email_verified(self, onboarding_manager):
        """Test convenience method for marking email verified."""
        onboarding_manager.create_onboarding(user_id=1)

        state = onboarding_manager.mark_email_verified(1)

        assert state.email_verified is True


class TestDownloadTokens:
    """Test download token functionality."""

    def test_create_download_token(self, onboarding_manager):
        """Test creating a download token."""
        onboarding_manager.create_onboarding(user_id=1)

        token = onboarding_manager.create_download_token(1, "macos")

        assert token is not None
        assert len(token) > 20

    def test_validate_download_token_success(self, onboarding_manager):
        """Test validating a download token."""
        onboarding_manager.create_onboarding(user_id=1)
        token = onboarding_manager.create_download_token(1, "macos")

        result = onboarding_manager.validate_download_token(token)

        assert result is not None
        assert result["user_id"] == 1
        assert result["platform"] == "macos"

    def test_validate_download_token_updates_state(self, onboarding_manager):
        """Test that validating token updates onboarding state."""
        onboarding_manager.create_onboarding(user_id=1)
        token = onboarding_manager.create_download_token(1, "windows")

        onboarding_manager.validate_download_token(token)

        state = onboarding_manager.get_onboarding_state(1)
        assert state.desktop_downloaded is True

    def test_validate_download_token_single_use(self, onboarding_manager):
        """Test that token can only be used once."""
        onboarding_manager.create_onboarding(user_id=1)
        token = onboarding_manager.create_download_token(1, "linux")

        # First use should succeed
        result1 = onboarding_manager.validate_download_token(token)
        assert result1 is not None

        # Second use should fail
        result2 = onboarding_manager.validate_download_token(token)
        assert result2 is None

    def test_validate_download_token_invalid(self, onboarding_manager):
        """Test validating an invalid token."""
        result = onboarding_manager.validate_download_token("invalid_token")

        assert result is None


class TestDeviceRegistration:
    """Test desktop device registration."""

    def test_register_device(self, onboarding_manager):
        """Test registering a new device."""
        onboarding_manager.create_onboarding(user_id=1)

        device = onboarding_manager.register_device(
            user_id=1,
            device_name="John's MacBook",
            platform="macos",
            version="1.0.0",
        )

        assert device.id is not None
        assert device.user_id == 1
        assert device.device_name == "John's MacBook"
        assert device.platform == "macos"
        assert device.version == "1.0.0"
        assert device.is_active is True
        assert device.capture_enabled is True
        assert device.clipboard_enabled is True
        assert device.file_watcher_enabled is True

    def test_register_device_updates_state(self, onboarding_manager):
        """Test that registering device updates onboarding state."""
        onboarding_manager.create_onboarding(user_id=1)

        onboarding_manager.register_device(
            user_id=1,
            device_name="Test Device",
            platform="linux",
            version="1.0.0",
        )

        state = onboarding_manager.get_onboarding_state(1)
        assert state.desktop_installed is True
        assert len(state.devices) == 1

    def test_update_device_heartbeat(self, onboarding_manager):
        """Test updating device heartbeat."""
        onboarding_manager.create_onboarding(user_id=1)
        device = onboarding_manager.register_device(
            user_id=1,
            device_name="Test Device",
            platform="windows",
            version="1.0.0",
        )

        result = onboarding_manager.update_device_heartbeat(device.device_id)

        assert result is True

    def test_update_device_heartbeat_invalid(self, onboarding_manager):
        """Test updating heartbeat for non-existent device."""
        result = onboarding_manager.update_device_heartbeat("invalid_device_id")

        assert result is False

    def test_update_device_settings(self, onboarding_manager):
        """Test updating device settings."""
        onboarding_manager.create_onboarding(user_id=1)
        device = onboarding_manager.register_device(
            user_id=1,
            device_name="Test Device",
            platform="macos",
            version="1.0.0",
        )

        result = onboarding_manager.update_device_settings(
            device_id=device.device_id,
            capture_enabled=False,
            clipboard_enabled=True,
            file_watcher_enabled=False,
        )

        assert result is True


class TestExtensionRegistration:
    """Test browser extension registration."""

    def test_register_extension(self, onboarding_manager):
        """Test registering a new extension."""
        onboarding_manager.create_onboarding(user_id=1)

        extension = onboarding_manager.register_extension(
            user_id=1,
            version="1.0.0",
            browser="chrome",
        )

        assert extension.id is not None
        assert extension.user_id == 1
        assert extension.browser == "chrome"
        assert extension.version == "1.0.0"
        assert extension.is_active is True
        assert extension.history_enabled is True
        assert extension.tabs_enabled is True
        assert extension.bookmarks_enabled is True

    def test_register_extension_updates_state(self, onboarding_manager):
        """Test that registering extension updates onboarding state."""
        onboarding_manager.create_onboarding(user_id=1)

        onboarding_manager.register_extension(
            user_id=1,
            version="1.0.0",
            browser="firefox",
        )

        state = onboarding_manager.get_onboarding_state(1)
        assert state.extension_installed is True
        assert len(state.extensions) == 1

    def test_register_extension_completes_onboarding(self, onboarding_manager):
        """Test that installing both device and extension completes onboarding."""
        onboarding_manager.create_onboarding(user_id=1)

        # Register device first
        onboarding_manager.register_device(
            user_id=1,
            device_name="Test Device",
            platform="macos",
            version="1.0.0",
        )

        # Then register extension
        onboarding_manager.register_extension(
            user_id=1,
            version="1.0.0",
            browser="chrome",
        )

        state = onboarding_manager.get_onboarding_state(1)
        assert state.current_step == OnboardingStep.COMPLETED

    def test_update_extension_heartbeat(self, onboarding_manager):
        """Test updating extension heartbeat."""
        onboarding_manager.create_onboarding(user_id=1)
        extension = onboarding_manager.register_extension(
            user_id=1,
            version="1.0.0",
            browser="chrome",
        )

        result = onboarding_manager.update_extension_heartbeat(extension.extension_id)

        assert result is True

    def test_update_extension_settings(self, onboarding_manager):
        """Test updating extension settings."""
        onboarding_manager.create_onboarding(user_id=1)
        extension = onboarding_manager.register_extension(
            user_id=1,
            version="1.0.0",
            browser="chrome",
        )

        result = onboarding_manager.update_extension_settings(
            extension_id=extension.extension_id,
            history_enabled=False,
            tabs_enabled=True,
            bookmarks_enabled=False,
        )

        assert result is True


class TestSyncStatus:
    """Test sync status functionality."""

    def test_is_all_synced_false_without_devices(self, onboarding_manager):
        """Test all_synced is false without devices."""
        state = onboarding_manager.create_onboarding(user_id=1)

        assert state.is_all_synced() is False

    def test_is_all_synced_false_with_only_device(self, onboarding_manager):
        """Test all_synced is false with only device."""
        onboarding_manager.create_onboarding(user_id=1)
        onboarding_manager.register_device(
            user_id=1,
            device_name="Test Device",
            platform="macos",
            version="1.0.0",
        )

        state = onboarding_manager.get_onboarding_state(1)
        assert state.is_all_synced() is False

    def test_is_all_synced_true_with_both(self, onboarding_manager):
        """Test all_synced is true with device and extension."""
        onboarding_manager.create_onboarding(user_id=1)
        onboarding_manager.register_device(
            user_id=1,
            device_name="Test Device",
            platform="macos",
            version="1.0.0",
        )
        onboarding_manager.register_extension(
            user_id=1,
            version="1.0.0",
            browser="chrome",
        )

        state = onboarding_manager.get_onboarding_state(1)
        assert state.is_all_synced() is True

    def test_get_sync_status(self, onboarding_manager):
        """Test getting detailed sync status."""
        onboarding_manager.create_onboarding(user_id=1)
        onboarding_manager.register_device(
            user_id=1,
            device_name="Test Device",
            platform="macos",
            version="1.0.0",
        )
        onboarding_manager.register_extension(
            user_id=1,
            version="1.0.0",
            browser="chrome",
        )

        state = onboarding_manager.get_onboarding_state(1)
        sync_status = state.get_sync_status()

        assert "screen_capture" in sync_status
        assert "clipboard" in sync_status
        assert "file_watcher" in sync_status
        assert "browser_history" in sync_status
        assert "browser_tabs" in sync_status
        assert "browser_bookmarks" in sync_status

        assert sync_status["screen_capture"]["enabled"] is True
        assert sync_status["browser_history"]["enabled"] is True

    def test_get_sync_summary(self, onboarding_manager):
        """Test getting sync summary."""
        onboarding_manager.create_onboarding(user_id=1)
        onboarding_manager.register_device(
            user_id=1,
            device_name="Test Device",
            platform="macos",
            version="1.0.0",
        )
        onboarding_manager.register_extension(
            user_id=1,
            version="1.0.0",
            browser="chrome",
        )

        summary = onboarding_manager.get_sync_summary(1)

        assert summary["user_id"] == 1
        assert summary["onboarding_complete"] is True
        assert summary["all_synced"] is True
        assert summary["active_sources"] == 6
        assert summary["total_sources"] == 6
        assert summary["completion_percentage"] == 100


class TestMultipleDevicesAndExtensions:
    """Test handling multiple devices and extensions."""

    def test_multiple_devices(self, onboarding_manager):
        """Test registering multiple devices."""
        onboarding_manager.create_onboarding(user_id=1)

        device1 = onboarding_manager.register_device(
            user_id=1,
            device_name="Work Laptop",
            platform="macos",
            version="1.0.0",
        )
        device2 = onboarding_manager.register_device(
            user_id=1,
            device_name="Home Desktop",
            platform="windows",
            version="1.0.0",
        )

        state = onboarding_manager.get_onboarding_state(1)
        assert len(state.devices) == 2
        assert device1.device_id != device2.device_id

    def test_multiple_extensions(self, onboarding_manager):
        """Test registering multiple extensions."""
        onboarding_manager.create_onboarding(user_id=1)

        ext1 = onboarding_manager.register_extension(
            user_id=1,
            version="1.0.0",
            browser="chrome",
        )
        ext2 = onboarding_manager.register_extension(
            user_id=1,
            version="1.0.0",
            browser="firefox",
        )

        state = onboarding_manager.get_onboarding_state(1)
        assert len(state.extensions) == 2
        assert ext1.extension_id != ext2.extension_id
