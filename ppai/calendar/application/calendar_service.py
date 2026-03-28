from __future__ import annotations

import logging
from datetime import datetime, timezone

from cryptography.fernet import Fernet

from ppai.calendar.application.google_oauth_service import GoogleOAuthService
from ppai.calendar.application.ports import CalendarAuthRepository, CalendarProvider
from ppai.calendar.domain.entities import CalendarAuth, CalendarEvent
from ppai.calendar.domain.exceptions import OAuthError, TokenExpiredError

logger = logging.getLogger(__name__)


class CalendarService:
    def __init__(
        self,
        auth_repo: CalendarAuthRepository,
        calendar_provider: CalendarProvider,
        oauth_service: GoogleOAuthService,
        fernet_key: str,
    ) -> None:
        self._auth_repo = auth_repo
        self._calendar_provider = calendar_provider
        self._oauth_service = oauth_service
        if fernet_key:
            self._fernet = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
        else:
            self._fernet = None
            logger.warning("FERNET_ENCRYPTION_KEY not set; calendar encryption disabled")

    def connect(self, user_id: str, auth_code: str) -> bool:
        """Exchange auth code for tokens, encrypt them, and save CalendarAuth."""
        try:
            access_token, refresh_token, expiry = self._oauth_service.exchange_code(auth_code)

            auth = CalendarAuth(
                user_id=user_id,
                access_token=self._encrypt_token(access_token),
                refresh_token=self._encrypt_token(refresh_token),
                token_expiry=expiry,
                calendar_connected=True,
            )
            self._auth_repo.save(auth)
            logger.info("Calendar connected", extra={"user_id": user_id})
            return True
        except OAuthError:
            logger.warning("OAuth connect failed", extra={"user_id": user_id})
            return False
        except Exception as exc:
            logger.error("Unexpected error connecting calendar", extra={"user_id": user_id, "error": str(exc)})
            return False

    def get_events_today(self, user_id: str) -> list[CalendarEvent]:
        """Fetch today's events from Google Calendar."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.get_events_for_date(user_id, today)

    def get_events_for_date(self, user_id: str, date: str) -> list[CalendarEvent]:
        """Fetch events for a specific date from Google Calendar."""
        auth = self._auth_repo.get(user_id)
        if auth is None or not auth.calendar_connected:
            return []

        try:
            auth = self._ensure_valid_token(auth)
            # Decrypt tokens for the provider
            decrypted_auth = CalendarAuth(
                user_id=auth.user_id,
                access_token=self._decrypt_token(auth.access_token),
                refresh_token=self._decrypt_token(auth.refresh_token),
                token_expiry=auth.token_expiry,
                calendar_connected=auth.calendar_connected,
                created_at=auth.created_at,
                updated_at=auth.updated_at,
            )
            return self._calendar_provider.get_events(decrypted_auth, date)
        except TokenExpiredError:
            logger.warning("Token expired and refresh failed", extra={"user_id": user_id})
            return []
        except Exception as exc:
            logger.error("Error fetching events", extra={"user_id": user_id, "error": str(exc)})
            return []

    def create_calendar_event(
        self,
        user_id: str,
        title: str,
        start: str,
        end: str,
        description: str | None = None,
        timezone_name: str = "UTC",
    ) -> str | None:
        """Create a calendar event. Returns event_id or None on failure."""
        auth = self._auth_repo.get(user_id)
        if auth is None or not auth.calendar_connected:
            return None

        try:
            auth = self._ensure_valid_token(auth)
            decrypted_auth = CalendarAuth(
                user_id=auth.user_id,
                access_token=self._decrypt_token(auth.access_token),
                refresh_token=self._decrypt_token(auth.refresh_token),
                token_expiry=auth.token_expiry,
                calendar_connected=auth.calendar_connected,
                created_at=auth.created_at,
                updated_at=auth.updated_at,
            )
            return self._calendar_provider.create_event(
                decrypted_auth, title, start, end, description,
                timezone_name=timezone_name,
            )
        except Exception as exc:
            logger.error("Error creating calendar event", extra={"user_id": user_id, "error": str(exc)})
            return None

    def is_connected(self, user_id: str) -> bool:
        """Check if user has a connected calendar."""
        auth = self._auth_repo.get(user_id)
        return auth is not None and auth.calendar_connected

    def _ensure_valid_token(self, auth: CalendarAuth) -> CalendarAuth:
        """Refresh the access token if expired, save updated auth."""
        now = datetime.now(timezone.utc)
        if auth.token_expiry > now:
            return auth

        try:
            decrypted_refresh = self._decrypt_token(auth.refresh_token)
            new_access_token, new_expiry = self._oauth_service.refresh_token(decrypted_refresh)

            auth.access_token = self._encrypt_token(new_access_token)
            auth.token_expiry = new_expiry
            auth.updated_at = now
            self._auth_repo.save(auth)
            return auth
        except OAuthError as exc:
            raise TokenExpiredError(f"Token refresh failed: {exc}") from exc

    def _encrypt_token(self, token: str) -> str:
        """Encrypt a token string using Fernet."""
        return self._fernet.encrypt(token.encode()).decode()

    def _decrypt_token(self, encrypted: str) -> str:
        """Decrypt a Fernet-encrypted token string."""
        return self._fernet.decrypt(encrypted.encode()).decode()
