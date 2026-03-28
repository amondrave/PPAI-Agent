from __future__ import annotations

import logging
import time
from urllib.parse import urlencode

from datetime import datetime, timezone

import requests
from google.oauth2.credentials import Credentials

from ppai.calendar.domain.exceptions import OAuthError

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_REDIRECT_URI = "http://localhost"


class GoogleOAuthService:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    # ------------------------------------------------------------------
    # Desktop App OAuth — step 1: generate authorization URL
    # ------------------------------------------------------------------

    def generate_auth_url(self) -> str:
        """Generate the Google OAuth consent URL for a Desktop app client."""
        params = {
            "client_id": self._client_id,
            "redirect_uri": _REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    # ------------------------------------------------------------------
    # Desktop App OAuth — step 2: exchange authorization code for tokens
    # ------------------------------------------------------------------

    def exchange_code(self, auth_code: str) -> tuple[str, str, datetime]:
        """Exchange an authorization code for access and refresh tokens.

        Returns (access_token, refresh_token, expiry).
        Raises OAuthError on failure.
        """
        try:
            resp = requests.post(
                _TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": auth_code,
                    "grant_type": "authorization_code",
                    "redirect_uri": _REDIRECT_URI,
                },
                timeout=15,
            )
            data = resp.json()

            if resp.status_code != 200 or "access_token" not in data:
                error = data.get("error", "unknown_error")
                error_desc = data.get("error_description", "")
                raise OAuthError(f"Token exchange failed: {error} — {error_desc}")

            access_token = data["access_token"]
            refresh_token = data.get("refresh_token", "")
            expires_in = data.get("expires_in", 3600)
            expiry = datetime.fromtimestamp(
                time.time() + expires_in, tz=timezone.utc,
            )
            return access_token, refresh_token, expiry

        except requests.RequestException as exc:
            logger.error("Token exchange network error", extra={"error": str(exc)})
            raise OAuthError(f"Error exchanging auth code: {exc}") from exc

    # ------------------------------------------------------------------
    # Token refresh (unchanged — works for any grant type)
    # ------------------------------------------------------------------

    def refresh_token(self, refresh_token: str) -> tuple[str, datetime]:
        """Refresh an expired access token. Returns (new_access_token, new_expiry)."""
        try:
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri=_TOKEN_URL,
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
