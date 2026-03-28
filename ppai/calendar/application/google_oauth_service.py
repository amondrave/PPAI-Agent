from __future__ import annotations

import logging
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from ppai.calendar.domain.exceptions import OAuthError

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

_REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"


class GoogleOAuthService:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    def generate_auth_url(self) -> str:
        """Generate the OAuth consent URL for the user to authorize access."""
        try:
            flow = InstalledAppFlow.from_client_config(
                client_config={
                    "installed": {
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [_REDIRECT_URI],
                    }
                },
                scopes=_SCOPES,
            )
            auth_url, _ = flow.authorization_url(
                access_type="offline",
                prompt="consent",
            )
            return auth_url
        except Exception as exc:
            logger.error("Failed to generate auth URL", extra={"error": str(exc)})
            raise OAuthError(f"Error generating auth URL: {exc}") from exc

    def exchange_code(self, code: str) -> tuple[str, str, datetime]:
        """Exchange authorization code for tokens. Returns (access_token, refresh_token, expiry)."""
        try:
            flow = InstalledAppFlow.from_client_config(
                client_config={
                    "installed": {
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [_REDIRECT_URI],
                    }
                },
                scopes=_SCOPES,
            )
            flow.redirect_uri = _REDIRECT_URI
            flow.fetch_token(code=code)
            credentials = flow.credentials

            access_token = credentials.token
            refresh_token = credentials.refresh_token or ""
            expiry = credentials.expiry
            if expiry and expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry is None:
                expiry = datetime.now(timezone.utc)

            return access_token, refresh_token, expiry
        except Exception as exc:
            logger.error("Failed to exchange code", extra={"error": str(exc)})
            raise OAuthError(f"Error exchanging code: {exc}") from exc

    def refresh_token(self, refresh_token: str) -> tuple[str, datetime]:
        """Refresh an expired access token. Returns (new_access_token, new_expiry)."""
        try:
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self._client_id,
                client_secret=self._client_secret,
                scopes=_SCOPES,
            )
            from google.auth.transport.requests import Request

            credentials.refresh(Request())

            new_token = credentials.token
            expiry = credentials.expiry
            if expiry and expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry is None:
                expiry = datetime.now(timezone.utc)

            return new_token, expiry
        except Exception as exc:
            logger.error("Failed to refresh token", extra={"error": str(exc)})
            raise OAuthError(f"Error refreshing token: {exc}") from exc
