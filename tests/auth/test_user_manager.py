"""Tests for user authentication and session management."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auth.user_manager import UserManager, User, Session


@pytest.fixture
def user_manager():
    """Create a UserManager with a temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_users.db"
        yield UserManager(db_path=db_path)


class TestUserCreation:
    """Test user creation functionality."""

    def test_create_user_success(self, user_manager):
        """Test successful user creation."""
        user = user_manager.create_user(
            email="test@example.com",
            name="Test User",
            password="password123",
        )

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.email_verified is False
        assert user.verification_token is not None
        assert ":" in user.password_hash  # salt:hash format

    def test_create_user_duplicate_email(self, user_manager):
        """Test that duplicate emails are rejected."""
        user_manager.create_user(
            email="test@example.com",
            name="Test User",
            password="password123",
        )

        with pytest.raises(ValueError, match="already exists"):
            user_manager.create_user(
                email="test@example.com",
                name="Another User",
                password="different123",
            )

    def test_email_case_insensitive(self, user_manager):
        """Test that emails are case-insensitive."""
        user_manager.create_user(
            email="Test@Example.COM",
            name="Test User",
            password="password123",
        )

        with pytest.raises(ValueError, match="already exists"):
            user_manager.create_user(
                email="test@example.com",
                name="Another User",
                password="different123",
            )


class TestAuthentication:
    """Test user authentication functionality."""

    def test_authenticate_success(self, user_manager):
        """Test successful authentication."""
        user_manager.create_user(
            email="test@example.com",
            name="Test User",
            password="password123",
        )

        user = user_manager.authenticate("test@example.com", "password123")

        assert user is not None
        assert user.email == "test@example.com"

    def test_authenticate_wrong_password(self, user_manager):
        """Test authentication with wrong password."""
        user_manager.create_user(
            email="test@example.com",
            name="Test User",
            password="password123",
        )

        user = user_manager.authenticate("test@example.com", "wrongpassword")

        assert user is None

    def test_authenticate_nonexistent_user(self, user_manager):
        """Test authentication for non-existent user."""
        user = user_manager.authenticate("nobody@example.com", "password123")

        assert user is None

    def test_authenticate_email_case_insensitive(self, user_manager):
        """Test that authentication is case-insensitive for email."""
        user_manager.create_user(
            email="test@example.com",
            name="Test User",
            password="password123",
        )

        user = user_manager.authenticate("TEST@Example.COM", "password123")

        assert user is not None
        assert user.email == "test@example.com"


class TestUserRetrieval:
    """Test user retrieval functionality."""

    def test_get_user_by_id(self, user_manager):
        """Test retrieving user by ID."""
        created = user_manager.create_user(
            email="test@example.com",
            name="Test User",
            password="password123",
        )

        user = user_manager.get_user_by_id(created.id)

        assert user is not None
        assert user.email == "test@example.com"

    def test_get_user_by_id_not_found(self, user_manager):
        """Test retrieving non-existent user by ID."""
        user = user_manager.get_user_by_id(999)

        assert user is None

    def test_get_user_by_email(self, user_manager):
        """Test retrieving user by email."""
        user_manager.create_user(
            email="test@example.com",
            name="Test User",
            password="password123",
        )

        user = user_manager.get_user_by_email("test@example.com")

        assert user is not None
        assert user.name == "Test User"

    def test_get_user_by_email_not_found(self, user_manager):
        """Test retrieving non-existent user by email."""
        user = user_manager.get_user_by_email("nobody@example.com")

        assert user is None


class TestEmailVerification:
    """Test email verification functionality."""

    def test_verify_email_success(self, user_manager):
        """Test successful email verification."""
        user = user_manager.create_user(
            email="test@example.com",
            name="Test User",
            password="password123",
        )

        result = user_manager.verify_email(user.verification_token)

        assert result is True

        # Verify user is now verified
        updated = user_manager.get_user_by_id(user.id)
        assert updated.email_verified is True
        assert updated.verification_token is None

    def test_verify_email_invalid_token(self, user_manager):
        """Test email verification with invalid token."""
        result = user_manager.verify_email("invalid_token")

        assert result is False


class TestSessionManagement:
    """Test session management functionality."""

    def test_create_session(self, user_manager):
        """Test session creation."""
        user = user_manager.create_user(
            email="test@example.com",
            name="Test User",
            password="password123",
        )

        session = user_manager.create_session(user.id)

        assert session.id is not None
        assert session.user_id == user.id
        assert session.token is not None
        assert len(session.token) > 20

    def test_create_session_with_device_info(self, user_manager):
        """Test session creation with device info."""
        user = user_manager.create_user(
            email="test@example.com",
            name="Test User",
            password="password123",
        )

        session = user_manager.create_session(user.id, device_info="Chrome on macOS")

        assert session.device_info == "Chrome on macOS"

    def test_validate_session_success(self, user_manager):
        """Test successful session validation."""
        user = user_manager.create_user(
            email="test@example.com",
            name="Test User",
            password="password123",
        )
        session = user_manager.create_session(user.id)

        validated_user = user_manager.validate_session(session.token)

        assert validated_user is not None
        assert validated_user.id == user.id

    def test_validate_session_invalid_token(self, user_manager):
        """Test session validation with invalid token."""
        user = user_manager.validate_session("invalid_token")

        assert user is None

    def test_invalidate_session(self, user_manager):
        """Test session invalidation."""
        user = user_manager.create_user(
            email="test@example.com",
            name="Test User",
            password="password123",
        )
        session = user_manager.create_session(user.id)

        result = user_manager.invalidate_session(session.token)

        assert result is True

        # Session should no longer be valid
        validated = user_manager.validate_session(session.token)
        assert validated is None

    def test_invalidate_all_sessions(self, user_manager):
        """Test invalidating all sessions for a user."""
        user = user_manager.create_user(
            email="test@example.com",
            name="Test User",
            password="password123",
        )

        session1 = user_manager.create_session(user.id)
        session2 = user_manager.create_session(user.id)

        count = user_manager.invalidate_all_sessions(user.id)

        assert count == 2

        assert user_manager.validate_session(session1.token) is None
        assert user_manager.validate_session(session2.token) is None


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_password_hash_different_each_time(self, user_manager):
        """Test that the same password generates different hashes."""
        hash1 = user_manager._hash_password("password123")
        hash2 = user_manager._hash_password("password123")

        assert hash1 != hash2  # Different salts

    def test_password_verification(self, user_manager):
        """Test password verification works correctly."""
        password = "mySecurePassword123!"
        hash_value = user_manager._hash_password(password)

        assert user_manager._verify_password(password, hash_value) is True
        assert user_manager._verify_password("wrongpassword", hash_value) is False


class TestUserModel:
    """Test User model functionality."""

    def test_user_to_dict(self):
        """Test User.to_dict() excludes sensitive fields."""
        user = User(
            id=1,
            email="test@example.com",
            name="Test User",
            password_hash="secret:hash",
            created_at="2024-01-01T00:00:00",
            email_verified=True,
            verification_token="secret_token",
        )

        user_dict = user.to_dict()

        assert "password_hash" not in user_dict
        assert "verification_token" not in user_dict
        assert user_dict["email"] == "test@example.com"
        assert user_dict["name"] == "Test User"
