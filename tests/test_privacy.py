"""
Tests for the privacy/PII detection module.
"""

import pytest
from src.utils.privacy import (
    PIIDetector,
    PIIMatch,
    detect_pii,
    redact_pii,
    has_pii,
    should_capture_window,
    luhn_check
)


class TestPIIDetection:
    """Tests for PII detection functionality."""

    def test_detect_email(self):
        """Test email detection."""
        text = "Contact me at john.doe@example.com for more info"
        matches = detect_pii(text)

        assert len(matches) >= 1
        email_matches = [m for m in matches if m.pii_type == "email"]
        assert len(email_matches) == 1
        assert email_matches[0].value == "john.doe@example.com"

    def test_detect_multiple_emails(self):
        """Test detection of multiple emails."""
        text = "Send to alice@test.com or bob@example.org"
        matches = detect_pii(text)

        email_matches = [m for m in matches if m.pii_type == "email"]
        assert len(email_matches) == 2

    def test_detect_phone_us(self):
        """Test US phone number detection."""
        text = "Call me at 555-123-4567 or (555) 987-6543"
        matches = detect_pii(text)

        phone_matches = [m for m in matches if "phone" in m.pii_type]
        assert len(phone_matches) >= 2

    def test_detect_ssn(self):
        """Test Social Security Number detection."""
        text = "My SSN is 123-45-6789"
        matches = detect_pii(text)

        ssn_matches = [m for m in matches if m.pii_type == "ssn"]
        assert len(ssn_matches) == 1
        assert "123-45-6789" in ssn_matches[0].value

    def test_detect_credit_card(self):
        """Test credit card detection."""
        # Visa test number
        text = "Card: 4111111111111111"
        matches = detect_pii(text)

        cc_matches = [m for m in matches if m.pii_type == "credit_card"]
        assert len(cc_matches) == 1

    def test_detect_ip_address(self):
        """Test IP address detection."""
        text = "Server at 192.168.1.100"
        matches = detect_pii(text)

        ip_matches = [m for m in matches if m.pii_type == "ip_address"]
        assert len(ip_matches) == 1
        assert ip_matches[0].value == "192.168.1.100"

    def test_detect_api_key(self):
        """Test API key detection."""
        text = "api_key=sk-1234567890abcdefghij1234567890ab"
        matches = detect_pii(text)

        api_matches = [m for m in matches if m.pii_type == "api_key"]
        assert len(api_matches) >= 1

    def test_detect_jwt(self):
        """Test JWT token detection."""
        text = "Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        matches = detect_pii(text)

        jwt_matches = [m for m in matches if m.pii_type == "jwt"]
        assert len(jwt_matches) == 1

    def test_no_pii(self):
        """Test text without PII."""
        text = "Hello world, this is a normal sentence."
        matches = detect_pii(text)
        assert len(matches) == 0

    def test_empty_text(self):
        """Test empty text."""
        assert detect_pii("") == []
        assert detect_pii(None) == []


class TestPIIRedaction:
    """Tests for PII redaction functionality."""

    def test_redact_email(self):
        """Test email redaction."""
        text = "Contact john@example.com for help"
        redacted = redact_pii(text)

        assert "john@example.com" not in redacted
        assert "[EMAIL REDACTED]" in redacted

    def test_redact_multiple_pii(self):
        """Test redacting multiple PII types."""
        text = "Email: test@example.com, Phone: 555-123-4567"
        redacted = redact_pii(text)

        assert "test@example.com" not in redacted
        assert "555-123-4567" not in redacted

    def test_redact_preserves_context(self):
        """Test that redaction preserves surrounding text."""
        text = "Before john@example.com after"
        redacted = redact_pii(text)

        assert redacted.startswith("Before ")
        assert redacted.endswith(" after")


class TestPIIDetector:
    """Tests for PIIDetector class."""

    def test_custom_enabled_types(self):
        """Test detector with only specific types enabled."""
        detector = PIIDetector(enabled_types=["email"])
        text = "Email: test@example.com, Phone: 555-123-4567"

        matches = detector.detect(text)
        assert all(m.pii_type == "email" for m in matches)

    def test_has_pii(self):
        """Test has_pii convenience method."""
        assert has_pii("Contact test@example.com")
        assert not has_pii("Hello world")

    def test_get_pii_summary(self):
        """Test PII summary generation."""
        detector = PIIDetector()
        text = "Emails: a@b.com, c@d.com, Phone: 555-1234"

        summary = detector.get_pii_summary(text)
        assert "email" in summary
        assert summary["email"] == 2


class TestWindowFiltering:
    """Tests for window/app filtering."""

    def test_exclude_password_manager(self):
        """Test that password managers are excluded."""
        assert not should_capture_window("Vault", "1Password")
        assert not should_capture_window("Login", "Bitwarden")
        assert not should_capture_window("Passwords", "LastPass")

    def test_exclude_private_windows(self):
        """Test that private/incognito windows are excluded."""
        assert not should_capture_window("Private Browsing", "Firefox")
        assert not should_capture_window("Incognito - Google", "Chrome")

    def test_exclude_password_in_title(self):
        """Test that windows with password in title are excluded."""
        assert not should_capture_window("Enter Password", "App")
        assert not should_capture_window("Login Credentials", "Browser")

    def test_allow_normal_windows(self):
        """Test that normal windows are allowed."""
        assert should_capture_window("Document.txt", "TextEdit")
        assert should_capture_window("GitHub - Project", "Chrome")
        assert should_capture_window("Terminal", "iTerm2")


class TestLuhnCheck:
    """Tests for credit card Luhn validation."""

    def test_valid_card_numbers(self):
        """Test valid credit card numbers."""
        # Visa test number
        assert luhn_check("4111111111111111")
        # Mastercard test number
        assert luhn_check("5500000000000004")
        # Amex test number
        assert luhn_check("340000000000009")

    def test_invalid_card_numbers(self):
        """Test invalid credit card numbers."""
        assert not luhn_check("1234567890123456")
        assert not luhn_check("4111111111111112")

    def test_too_short(self):
        """Test numbers that are too short."""
        assert not luhn_check("123456")
