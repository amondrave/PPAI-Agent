from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from google.oauth2.credentials import Credentials

from ppai.calendar.domain.exceptions import OAuthError

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

_DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
_TOKEN_URL = "https://oauth2.googleapis.com/token"


@dataclass
class DeviceFlowInfo:
    """Data returned by the device authorization request."""

    device_code: str
    user_code: str
    verification_url: str
    expires_in: int
    interval: int


class GoogleOAuthService:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    # ------------------------------------------------------------------
    # Device Authorization Grant — step 1: request device & user codes
    # ------------------------------------------------------------------

    def start_device_flow(self) -> DeviceFlowInfo:
        """Request device and user codes from Google's device authorization endpoint."""
        try:
            resp = requests.post(
                _DEVICE_CODE_URL,
                data={
                    "client_id": self._client_id,
                    "scope": " ".join(_SCOPES),
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            return DeviceFlowInfo(
                device_code=data["device_code"],
                user_code=data["user_code"],
                verification_url=data.get("verification_url", "https://www.google.com/device"),
                expires_in=data.get("expires_in", 1800),
                interval=data.get("interval", 5),
            )
        except requests.RequestException as exc:
            logger.error("Failed to start device flow", extra={"error": str(exc)})
            raise OAuthError(f"Error starting device flow: {exc}") from exc
        except (KeyError, ValueError) as exc:
            logger.error("Invalid device flow response", extra={"error": str(exc)})
            raise OAuthError(f"Invalid device flow response: {exc}") from exc

    # ------------------------------------------------------------------
    # Device Authorization Grant — step 2: poll for tokens
    # ------------------------------------------------------------------

    def poll_device_token(
        self,
        device_code: str,
        interval: int = 5,
        max_attempts: int = 6,
    ) -> tuple[str, str, datetime]:
        """Poll Google's token endpoint until the user authorizes.

        Returns (access_token, refresh_token, expiry).
        Raises OAuthError if authorization times out or is denied.
        """
        for attempt in range(max_attempts):
            if attempt > 0:
                time.sleep(interval)

            try:
                resp = requests.post(
                    _TOKEN_URL,
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    },
                    timeout=15,
                )
                data = resp.json()

                if resp.status_code == 200 and "access_token" in data:
                    access_token = data["access_token"]
                    refresh_token = data.get("refresh_token", "")
                    expires_in = data.get("expires_in", 3600)
                    expiry = datetime.now(timezone.utc).replace(
                        microsecond=0,
                    )
                    expiry = expiry.replace(
                        second=expiry.second + expires_in,
                    ) if expires_in < 60 else datetime.fromtimestamp(
                        time.time() + expires_in, tz=timezone.utc,
                    )
                    return access_token, refresh_token, expiry

                error = data.get("error", "")
                if error == "authorization_pending":
                    continue
                if error == "slow_down":
                    interval += 1
                    continue
                if error in ("access_denied", "expired_token"):
                    raise OAuthError(f"Device authorization failed: {error}")

            except requests.RequestException as exc:
                logger.warning("Token poll network error", extra={"error": str(exc)})
                continue

        raise OAuthError("Device authorization timed out — user did not authorize in time")

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
