"""
Privacy Filters - PII Detection and Redaction

This module provides utilities for detecting and redacting Personally Identifiable
Information (PII) from captured content to protect user privacy.

Supported PII types:
- Email addresses
- Phone numbers (US, international)
- Credit card numbers
- Social Security Numbers (SSN)
- IP addresses
- API keys and tokens
- Passwords (in common formats)
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PIIMatch:
    """Represents a detected PII match."""
    pii_type: str
    value: str
    start: int
    end: int
    redacted: str


# === PII Detection Patterns ===

PII_PATTERNS = {
    "email": {
        "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "redact_with": "[EMAIL REDACTED]",
        "description": "Email address"
    },
    "phone_us": {
        "pattern": r'\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        "redact_with": "[PHONE REDACTED]",
        "description": "US phone number"
    },
    "phone_intl": {
        "pattern": r'\b\+?[1-9]\d{1,14}\b',
        "redact_with": "[PHONE REDACTED]",
        "description": "International phone number"
    },
    "credit_card": {
        "pattern": r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
        "redact_with": "[CREDIT CARD REDACTED]",
        "description": "Credit card number"
    },
    "ssn": {
        "pattern": r'\b(?!000|666|9\d{2})\d{3}[-\s]?(?!00)\d{2}[-\s]?(?!0000)\d{4}\b',
        "redact_with": "[SSN REDACTED]",
        "description": "Social Security Number"
    },
    "ip_address": {
        "pattern": r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
        "redact_with": "[IP REDACTED]",
        "description": "IP address"
    },
    "api_key": {
        "pattern": r'\b(?:sk-[a-zA-Z0-9]{32,}|api[_-]?key[_-]?[=:]\s*[\'"]?[a-zA-Z0-9_-]{20,}[\'"]?)\b',
        "redact_with": "[API KEY REDACTED]",
        "description": "API key or secret"
    },
    "aws_key": {
        "pattern": r'\b(?:AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}\b',
        "redact_with": "[AWS KEY REDACTED]",
        "description": "AWS access key"
    },
    "github_token": {
        "pattern": r'\bgh[pousr]_[A-Za-z0-9_]{36,}\b',
        "redact_with": "[GITHUB TOKEN REDACTED]",
        "description": "GitHub token"
    },
    "password_field": {
        "pattern": r'(?:password|passwd|pwd)["\s:=]+["\']?[^\s"\']{8,}["\']?',
        "redact_with": "[PASSWORD REDACTED]",
        "description": "Password in field format"
    },
    "bearer_token": {
        "pattern": r'\bBearer\s+[A-Za-z0-9_-]{20,}\b',
        "redact_with": "[BEARER TOKEN REDACTED]",
        "description": "Bearer authentication token"
    },
    "jwt": {
        "pattern": r'\beyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\b',
        "redact_with": "[JWT REDACTED]",
        "description": "JSON Web Token"
    }
}


class PIIDetector:
    """
    Detects and redacts PII from text content.
    """

    def __init__(
        self,
        enabled_types: Optional[List[str]] = None,
        custom_patterns: Optional[Dict[str, Dict[str, str]]] = None
    ):
        """
        Initialize PII detector.

        Args:
            enabled_types: List of PII types to detect. If None, all types are enabled.
            custom_patterns: Additional custom patterns to add.
        """
        self.patterns = PII_PATTERNS.copy()

        if custom_patterns:
            self.patterns.update(custom_patterns)

        if enabled_types:
            self.enabled_types = set(enabled_types)
        else:
            self.enabled_types = set(self.patterns.keys())

        # Compile patterns for efficiency
        self.compiled_patterns = {}
        for pii_type, config in self.patterns.items():
            if pii_type in self.enabled_types:
                try:
                    self.compiled_patterns[pii_type] = re.compile(
                        config["pattern"],
                        re.IGNORECASE
                    )
                except re.error as e:
                    logger.warning(f"Invalid regex pattern for {pii_type}: {e}")

    def detect(self, text: str) -> List[PIIMatch]:
        """
        Detect all PII in the given text.

        Args:
            text: Text to scan for PII

        Returns:
            List of PIIMatch objects for each detection
        """
        if not text:
            return []

        matches = []

        for pii_type, pattern in self.compiled_patterns.items():
            config = self.patterns[pii_type]

            for match in pattern.finditer(text):
                matches.append(PIIMatch(
                    pii_type=pii_type,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                    redacted=config["redact_with"]
                ))

        # Sort by position
        matches.sort(key=lambda m: m.start)

        return matches

    def redact(self, text: str, pii_types: Optional[List[str]] = None) -> Tuple[str, List[PIIMatch]]:
        """
        Redact PII from text.

        Args:
            text: Text to redact
            pii_types: Specific PII types to redact. If None, redacts all enabled types.

        Returns:
            Tuple of (redacted_text, list_of_matches)
        """
        if not text:
            return text, []

        matches = self.detect(text)

        if pii_types:
            matches = [m for m in matches if m.pii_type in pii_types]

        if not matches:
            return text, []

        # Redact from end to start to preserve positions
        redacted = text
        for match in reversed(matches):
            redacted = redacted[:match.start] + match.redacted + redacted[match.end:]

        return redacted, matches

    def has_pii(self, text: str) -> bool:
        """
        Check if text contains any PII.

        Args:
            text: Text to check

        Returns:
            True if PII is detected
        """
        return len(self.detect(text)) > 0

    def get_pii_summary(self, text: str) -> Dict[str, int]:
        """
        Get a summary of PII types found in text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary mapping PII type to count
        """
        matches = self.detect(text)
        summary = {}
        for match in matches:
            summary[match.pii_type] = summary.get(match.pii_type, 0) + 1
        return summary


# === Window/App Filtering ===

def should_capture_window(
    window_title: str,
    app_name: str,
    excluded_apps: Optional[List[str]] = None,
    excluded_windows: Optional[List[str]] = None
) -> bool:
    """
    Check if content from a window should be captured.

    Args:
        window_title: Title of the window
        app_name: Name of the application
        excluded_apps: List of app names to exclude
        excluded_windows: List of window title patterns to exclude

    Returns:
        True if window should be captured, False to skip
    """
    excluded_apps = excluded_apps or [
        "1Password", "Bitwarden", "LastPass", "KeePass",
        "Keychain Access", "Keychain"
    ]

    excluded_windows = excluded_windows or [
        "Private", "Incognito", "InPrivate",
        "password", "credential", "login",
        "Credit Card", "Payment"
    ]

    # Check app name
    app_lower = app_name.lower()
    for excluded in excluded_apps:
        if excluded.lower() in app_lower:
            logger.debug(f"Skipping capture: excluded app '{app_name}'")
            return False

    # Check window title
    title_lower = window_title.lower()
    for excluded in excluded_windows:
        if excluded.lower() in title_lower:
            logger.debug(f"Skipping capture: excluded window pattern '{excluded}' in '{window_title}'")
            return False

    return True


# === Credit Card Validation ===

def luhn_check(card_number: str) -> bool:
    """
    Validate credit card number using Luhn algorithm.

    Args:
        card_number: Credit card number (digits only)

    Returns:
        True if valid according to Luhn algorithm
    """
    digits = [int(d) for d in card_number if d.isdigit()]
    if len(digits) < 13:
        return False

    # Double every second digit from right
    for i in range(len(digits) - 2, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9

    return sum(digits) % 10 == 0


# === Module-level convenience functions ===

_default_detector: Optional[PIIDetector] = None


def get_detector() -> PIIDetector:
    """Get the default PII detector instance."""
    global _default_detector
    if _default_detector is None:
        _default_detector = PIIDetector()
    return _default_detector


def detect_pii(text: str) -> List[PIIMatch]:
    """Detect PII in text using default detector."""
    return get_detector().detect(text)


def redact_pii(text: str) -> str:
    """Redact all PII from text using default detector."""
    redacted, _ = get_detector().redact(text)
    return redacted


def has_pii(text: str) -> bool:
    """Check if text contains PII using default detector."""
    return get_detector().has_pii(text)
