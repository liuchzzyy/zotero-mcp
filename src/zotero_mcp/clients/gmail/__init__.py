"""Gmail client - Gmail API integration."""

from .client import DEFAULT_CREDENTIALS_PATH, GmailClient

__all__ = [
    "GmailClient",
    "DEFAULT_CREDENTIALS_PATH",
]
