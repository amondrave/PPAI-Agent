from __future__ import annotations


class CalendarError(Exception):
    """Base exception for calendar module errors."""


class OAuthError(CalendarError):
    """Raised when OAuth flow fails."""


class TokenExpiredError(CalendarError):
    """Raised when the OAuth token has expired and cannot be refreshed."""


class TokenRevokedError(CalendarError):
    """Raised when the OAuth token has been revoked by the user."""


class PlanGenerationError(CalendarError):
    """Raised when day plan generation fails."""
