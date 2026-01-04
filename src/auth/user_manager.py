"""User management with authentication and session handling.

This module provides user registration, authentication, and session management
for the unified AI system. It follows the local-first principle with SQLite storage.
"""

import hashlib
import secrets
import sqlite3
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Literal


@dataclass
class User:
    """User model."""
    id: int
    email: str
    name: str
    password_hash: str
    created_at: str
    email_verified: bool = False
    verification_token: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding sensitive fields."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at,
            "email_verified": self.email_verified,
        }


@dataclass
class Session:
    """User session model."""
    id: int
    user_id: int
    token: str
    created_at: str
    expires_at: str
    device_info: Optional[str] = None


class UserManager:
    """Handles user registration, authentication, and session management.

    Args:
        db_path: Path to SQLite database. Defaults to ~/.unified-ai/users.db
    """

    def __init__(self, db_path: Path = Path("~/.unified-ai/users.db").expanduser()):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    email_verified INTEGER DEFAULT 0,
                    verification_token TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    device_info TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions (token)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id)")
            conn.commit()

    def _hash_password(self, password: str, salt: Optional[str] = None) -> str:
        """Hash a password using SHA-256 with salt.

        Args:
            password: Plain text password
            salt: Optional salt, generates new one if not provided

        Returns:
            Salted hash in format 'salt:hash'
        """
        if salt is None:
            salt = secrets.token_hex(16)
        hash_value = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return f"{salt}:{hash_value}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash.

        Args:
            password: Plain text password to verify
            password_hash: Stored hash in format 'salt:hash'

        Returns:
            True if password matches
        """
        salt = password_hash.split(":")[0]
        return self._hash_password(password, salt) == password_hash

    def create_user(self, email: str, name: str, password: str) -> User:
        """Register a new user.

        Args:
            email: User's email address
            name: User's display name
            password: Plain text password

        Returns:
            Created User object

        Raises:
            ValueError: If email already exists
        """
        password_hash = self._hash_password(password)
        verification_token = secrets.token_urlsafe(32)
        created_at = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            try:
                cursor = conn.execute("""
                    INSERT INTO users (email, name, password_hash, created_at, verification_token)
                    VALUES (?, ?, ?, ?, ?)
                """, (email.lower(), name, password_hash, created_at, verification_token))
                conn.commit()

                return User(
                    id=cursor.lastrowid,
                    email=email.lower(),
                    name=name,
                    password_hash=password_hash,
                    created_at=created_at,
                    email_verified=False,
                    verification_token=verification_token,
                )
            except sqlite3.IntegrityError:
                raise ValueError(f"User with email {email} already exists")

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email.lower(),)
            ).fetchone()

            if row and self._verify_password(password, row["password_hash"]):
                return User(
                    id=row["id"],
                    email=row["email"],
                    name=row["name"],
                    password_hash=row["password_hash"],
                    created_at=row["created_at"],
                    email_verified=bool(row["email_verified"]),
                    verification_token=row["verification_token"],
                )
        return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID.

        Args:
            user_id: User's ID

        Returns:
            User object if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()

            if row:
                return User(
                    id=row["id"],
                    email=row["email"],
                    name=row["name"],
                    password_hash=row["password_hash"],
                    created_at=row["created_at"],
                    email_verified=bool(row["email_verified"]),
                    verification_token=row["verification_token"],
                )
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.

        Args:
            email: User's email address

        Returns:
            User object if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email.lower(),)
            ).fetchone()

            if row:
                return User(
                    id=row["id"],
                    email=row["email"],
                    name=row["name"],
                    password_hash=row["password_hash"],
                    created_at=row["created_at"],
                    email_verified=bool(row["email_verified"]),
                    verification_token=row["verification_token"],
                )
        return None

    def verify_email(self, token: str) -> bool:
        """Verify a user's email using verification token.

        Args:
            token: Email verification token

        Returns:
            True if verification successful
        """
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                UPDATE users SET email_verified = 1, verification_token = NULL
                WHERE verification_token = ?
            """, (token,))
            conn.commit()
            return result.rowcount > 0

    def create_session(
        self,
        user_id: int,
        device_info: Optional[str] = None,
        duration_hours: int = 24 * 7
    ) -> Session:
        """Create a new session for a user.

        Args:
            user_id: User's ID
            device_info: Optional device/browser information
            duration_hours: Session duration in hours (default 7 days)

        Returns:
            Created Session object
        """
        token = secrets.token_urlsafe(32)
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=duration_hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO sessions (user_id, token, created_at, expires_at, device_info)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, token, created_at.isoformat(), expires_at.isoformat(), device_info))
            conn.commit()

            return Session(
                id=cursor.lastrowid,
                user_id=user_id,
                token=token,
                created_at=created_at.isoformat(),
                expires_at=expires_at.isoformat(),
                device_info=device_info,
            )

    def validate_session(self, token: str) -> Optional[User]:
        """Validate a session token and return the associated user.

        Args:
            token: Session token

        Returns:
            User object if session is valid, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT s.*, u.* FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token = ? AND s.expires_at > ?
            """, (token, datetime.utcnow().isoformat())).fetchone()

            if row:
                return User(
                    id=row["id"],
                    email=row["email"],
                    name=row["name"],
                    password_hash=row["password_hash"],
                    created_at=row["created_at"],
                    email_verified=bool(row["email_verified"]),
                    verification_token=row["verification_token"],
                )
        return None

    def invalidate_session(self, token: str) -> bool:
        """Invalidate a session (logout).

        Args:
            token: Session token to invalidate

        Returns:
            True if session was invalidated
        """
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return result.rowcount > 0

    def invalidate_all_sessions(self, user_id: int) -> int:
        """Invalidate all sessions for a user.

        Args:
            user_id: User's ID

        Returns:
            Number of sessions invalidated
        """
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            conn.commit()
            return result.rowcount

    def cleanup_expired_sessions(self) -> int:
        """Remove all expired sessions.

        Returns:
            Number of sessions removed
        """
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "DELETE FROM sessions WHERE expires_at < ?",
                (datetime.utcnow().isoformat(),)
            )
            conn.commit()
            return result.rowcount
