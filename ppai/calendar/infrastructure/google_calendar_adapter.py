from __future__ import annotations

import logging
from datetime import datetime, timezone

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from ppai.calendar.domain.entities import CalendarAuth, CalendarEvent

logger = logging.getLogger(__name__)

_PPAI_PREFIX = "[PPAI]"
_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


class GoogleCalendarAdapter:
    """Implements CalendarProvider using the Google Calendar API."""

    def get_events(self, auth: CalendarAuth, date: str, timezone_name: str = "UTC") -> list[CalendarEvent]:
        """Query primary calendar for events on the given date (YYYY-MM-DD)."""
        try:
            service = self._build_service(auth)
            # Use timezone-aware boundaries so we get correct events for user's local day
            time_min = f"{date}T00:00:00"
            time_max = f"{date}T23:59:59"

            result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    timeZone=timezone_name,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events: list[CalendarEvent] = []
            for item in result.get("items", []):
                start_raw = item.get("start", {})
                end_raw = item.get("end", {})

                is_all_day = "date" in start_raw and "dateTime" not in start_raw

                if is_all_day:
                    start_dt = datetime.strptime(start_raw["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    end_dt = datetime.strptime(end_raw["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                else:
                    start_dt = datetime.fromisoformat(start_raw.get("dateTime", f"{date}T00:00:00Z"))
                    end_dt = datetime.fromisoformat(end_raw.get("dateTime", f"{date}T23:59:59Z"))

                events.append(
                    CalendarEvent(
                        event_id=item.get("id", ""),
                        title=item.get("summary", "(sin titulo)"),
                        start=start_dt,
                        end=end_dt,
                        is_all_day=is_all_day,
                        source="google",
                    )
                )

            return events
        except Exception as exc:
            logger.error("Failed to fetch Google Calendar events", extra={"error": str(exc)})
            return []

    def create_event(
        self,
        auth: CalendarAuth,
        title: str,
        start: str,
        end: str,
        description: str | None = None,
        timezone_name: str = "UTC",
    ) -> str:
        """Create a calendar event with [PPAI] prefix. Returns the event_id."""
        try:
            service = self._build_service(auth)
            event_body: dict = {
                "summary": title if title.startswith(_PPAI_PREFIX) else f"{_PPAI_PREFIX} {title}",
                "start": {"dateTime": start, "timeZone": timezone_name},
                "end": {"dateTime": end, "timeZone": timezone_name},
            }
            if description:
                event_body["description"] = description

            result = service.events().insert(calendarId="primary", body=event_body).execute()
            return result.get("id", "")
        except Exception as exc:
            logger.error("Failed to create Google Calendar event", extra={"error": str(exc)})
            return ""

    def update_event(
        self,
        auth: CalendarAuth,
        event_id: str,
        title: str | None = None,
        start: str | None = None,
        end: str | None = None,
        description: str | None = None,
    ) -> bool:
        """Update an existing calendar event."""
        try:
            service = self._build_service(auth)
            body: dict = {}
            if title is not None:
                body["summary"] = title
            if start is not None:
                body["start"] = {"dateTime": start, "timeZone": "UTC"}
            if end is not None:
                body["end"] = {"dateTime": end, "timeZone": "UTC"}
            if description is not None:
                body["description"] = description

            service.events().patch(calendarId="primary", eventId=event_id, body=body).execute()
            return True
        except Exception as exc:
            logger.error("Failed to update Google Calendar event", extra={"event_id": event_id, "error": str(exc)})
            return False

    def delete_event(self, auth: CalendarAuth, event_id: str) -> bool:
        """Delete a calendar event."""
        try:
            service = self._build_service(auth)
            service.events().delete(calendarId="primary", eventId=event_id).execute()
            return True
        except Exception as exc:
            logger.error("Failed to delete Google Calendar event", extra={"event_id": event_id, "error": str(exc)})
            return False

    def _build_service(self, auth: CalendarAuth):
        """Build the Google Calendar API service from auth credentials."""
        credentials = Credentials(
            token=auth.access_token,
            refresh_token=auth.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=_SCOPES,
        )
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)
