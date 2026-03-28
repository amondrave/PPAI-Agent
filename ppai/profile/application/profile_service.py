"""Profile management service — CRUD, holidays, days off."""

from __future__ import annotations

import re
from datetime import date, time, datetime, timezone
from typing import Optional

import structlog

from ppai.profile.application.ports import ProfileRepository
from ppai.profile.domain.entities import UserProfile
from ppai.profile.domain.exceptions import InvalidProfileDataError
from ppai.profile.domain.value_objects import CommunicationStyle, WeekendMode

logger = structlog.get_logger(__name__)

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ProfileService:
    """Application service for profile management and holiday/day-off logic."""

    def __init__(self, profile_repo: ProfileRepository) -> None:
        self._repo = profile_repo

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        return self._repo.get(user_id)

    def save_profile(self, profile: UserProfile) -> None:
        profile.updated_at = datetime.now(timezone.utc)
        self._repo.save(profile)
        logger.info("profile.saved", user_id=profile.user_id)

    def profile_exists(self, user_id: str) -> bool:
        return self._repo.exists(user_id)

    def update_field(self, user_id: str, field: str, value: str) -> UserProfile:
        """Validate and update a single profile field. Returns updated profile."""
        profile = self._repo.get(user_id)
        if profile is None:
            raise InvalidProfileDataError(
                "No tienes un perfil configurado. Usa /setup para crearlo."
            )

        if field == "nombre":
            if len(value) < 2 or len(value) > 50:
                raise InvalidProfileDataError(
                    "El nombre debe tener entre 2 y 50 caracteres."
                )
            profile.name = value

        elif field == "estilo":
            try:
                profile.communication_style = CommunicationStyle(value.lower())
            except ValueError:
                raise InvalidProfileDataError(
                    "Estilo no valido. Opciones: gentle, direct, confrontational."
                )

        elif field == "horario":
            parts = value.split("-")
            if len(parts) != 2:
                raise InvalidProfileDataError(
                    "Formato invalido. Usa: HH:MM-HH:MM (ej. 08:00-17:00)."
                )
            start_str, end_str = parts[0].strip(), parts[1].strip()
            if not _TIME_RE.match(start_str) or not _TIME_RE.match(end_str):
                raise InvalidProfileDataError(
                    "Formato de hora invalido. Usa HH:MM-HH:MM."
                )
            sp = start_str.split(":")
            ep = end_str.split(":")
            profile.work_start = time(int(sp[0]), int(sp[1]))
            profile.work_end = time(int(ep[0]), int(ep[1]))

        elif field == "pais":
            profile.holidays_country = value.upper() if value.lower() != "none" else None

        elif field == "finde":
            try:
                profile.weekend_mode = WeekendMode(value.lower())
            except ValueError:
                raise InvalidProfileDataError(
                    "Modo no valido. Opciones: descanso, personal, mixto."
                )

        else:
            raise InvalidProfileDataError(
                f"Campo '{field}' no reconocido. "
                "Campos disponibles: nombre, estilo, horario, pais, finde."
            )

        profile.updated_at = datetime.now(timezone.utc)
        self._repo.save(profile)
        logger.info("profile.field_updated", user_id=user_id, field=field)
        return profile

    def get_holidays(self, country: str, year: int) -> list[date]:
        """Return list of holiday dates for a country and year using holidays library."""
        try:
            import holidays as holidays_lib
        except ImportError:
            logger.warning("holidays_lib.not_installed")
            return []

        try:
            country_holidays = holidays_lib.country_holidays(country.upper(), years=year)
        except Exception:
            logger.warning("holidays_lib.unsupported_country", country=country)
            return []

        return sorted(country_holidays.keys())

    def is_day_off(self, user_id: str, target_date: date) -> bool:
        """Check if a date is a day off for the user (holidays + personal days + weekend)."""
        profile = self._repo.get(user_id)
        if profile is None:
            return False

        date_str = target_date.isoformat()

        # Check personal days off
        if date_str in profile.days_off:
            return True

        # Check country holidays
        if profile.holidays_country:
            country_holidays = self.get_holidays(
                profile.holidays_country, target_date.year
            )
            if target_date in country_holidays:
                return True

        # Check weekend mode
        weekday = target_date.weekday()  # 0=Monday, 5=Saturday, 6=Sunday
        if weekday >= 5:  # Saturday or Sunday
            if profile.weekend_mode == WeekendMode.DESCANSO:
                return True
            # PERSONAL and MIXTO: not a full day off

        return False

    def add_day_off(self, user_id: str, date_str: str) -> UserProfile:
        """Add a personal day off."""
        if not _DATE_RE.match(date_str):
            raise InvalidProfileDataError(
                "Formato de fecha invalido. Usa YYYY-MM-DD (ej. 2026-04-15)."
            )

        # Validate the date is parseable
        try:
            date.fromisoformat(date_str)
        except ValueError:
            raise InvalidProfileDataError(
                "Fecha invalida. Verifica que sea una fecha real."
            )

        profile = self._repo.get(user_id)
        if profile is None:
            raise InvalidProfileDataError(
                "No tienes un perfil configurado. Usa /setup para crearlo."
            )

        if date_str in profile.days_off:
            raise InvalidProfileDataError(
                f"La fecha {date_str} ya esta en tu lista de dias libres."
            )

        profile.days_off.append(date_str)
        profile.updated_at = datetime.now(timezone.utc)
        self._repo.save(profile)
        logger.info("profile.day_off_added", user_id=user_id, date=date_str)
        return profile

    def list_days_off(self, user_id: str) -> str:
        """Return formatted list of personal days off."""
        profile = self._repo.get(user_id)
        if profile is None:
            return "No tienes un perfil configurado. Usa /setup para crearlo."

        if not profile.days_off:
            return "No tienes dias libres configurados."

        lines = ["Tus dias libres:"]
        for d in sorted(profile.days_off):
            lines.append(f"  - {d}")
        return "\n".join(lines)
