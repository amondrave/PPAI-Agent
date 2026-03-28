"""Pure domain service for conversational onboarding flow."""

from __future__ import annotations

import re
from datetime import time
from typing import Optional

import structlog

from ppai.profile.domain.entities import UserProfile
from ppai.profile.domain.exceptions import InvalidProfileDataError
from ppai.profile.domain.value_objects import (
    CommunicationStyle,
    OnboardingStep,
)

logger = structlog.get_logger(__name__)

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

_STEP_QUESTIONS: dict[OnboardingStep, str] = {
    OnboardingStep.NAME: (
        "Hola! Soy tu asistente de productividad.\n\n"
        "Vamos a configurar tu perfil. "
        "Para empezar, dime tu nombre:"
    ),
    OnboardingStep.OCCUPATION: (
        "Encantado, {name}! "
        "Ahora dime, a que te dedicas?"
    ),
    OnboardingStep.WORK_START: (
        "Genial! A que hora empiezas a trabajar? "
        "(formato HH:MM, ej. 08:00)"
    ),
    OnboardingStep.WORK_END: (
        "Y a que hora terminas tu jornada? "
        "(formato HH:MM, ej. 17:00)"
    ),
    OnboardingStep.PROTECTED_BLOCKS: (
        "Tienes bloques protegidos? (ej. almuerzo, ejercicio)\n\n"
        "Escribe cada uno asi: HH:MM-HH:MM etiqueta\n"
        "Por ejemplo: 12:00-13:00 Almuerzo\n\n"
        "Si tienes varios, envialos separados por coma.\n"
        "Si no tienes, escribe 'no'."
    ),
    OnboardingStep.COMMUNICATION_STYLE: (
        "Como prefieres que te hable?\n\n"
        "1. gentle - Amable y celebratorio\n"
        "2. direct - Datos concisos, al grano\n"
        "3. confrontational - Desafiante, sin rodeos\n\n"
        "Escribe el numero o el nombre del estilo:"
    ),
    OnboardingStep.CONFIRM: "",  # built dynamically via build_summary
}

_STEP_ORDER = [
    OnboardingStep.NAME,
    OnboardingStep.OCCUPATION,
    OnboardingStep.WORK_START,
    OnboardingStep.WORK_END,
    OnboardingStep.PROTECTED_BLOCKS,
    OnboardingStep.COMMUNICATION_STYLE,
    OnboardingStep.CONFIRM,
]

_BLOCK_RE = re.compile(
    r"^([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d\s+.+$"
)

_STYLE_MAP = {
    "1": CommunicationStyle.GENTLE,
    "2": CommunicationStyle.DIRECT,
    "3": CommunicationStyle.CONFRONTATIONAL,
    "gentle": CommunicationStyle.GENTLE,
    "direct": CommunicationStyle.DIRECT,
    "confrontational": CommunicationStyle.CONFRONTATIONAL,
}


class OnboardingService:
    """Tracks onboarding state per user and processes each step."""

    def __init__(self) -> None:
        # In-memory tracking: user_id -> partially built profile
        self._profiles: dict[str, UserProfile] = {}

    def get_current_step(self, user_id: str) -> OnboardingStep:
        """Determine the current onboarding step based on partial profile data."""
        profile = self._profiles.get(user_id)
        if profile is None:
            return OnboardingStep.NAME
        if not profile.name:
            return OnboardingStep.NAME
        if not profile.occupation:
            return OnboardingStep.OCCUPATION
        if profile.work_start is None:
            return OnboardingStep.WORK_START
        if profile.work_end is None:
            return OnboardingStep.WORK_END
        # protected_blocks can be empty (user said "no"), mark with sentinel
        if not hasattr(profile, "_blocks_asked") or not profile._blocks_asked:
            return OnboardingStep.PROTECTED_BLOCKS
        if profile.communication_style is None:
            return OnboardingStep.COMMUNICATION_STYLE
        return OnboardingStep.CONFIRM

    def get_question(self, step: OnboardingStep, profile: Optional[UserProfile] = None) -> str:
        """Return the question text for a given step."""
        template = _STEP_QUESTIONS[step]
        if step == OnboardingStep.OCCUPATION and profile:
            return template.format(name=profile.name)
        if step == OnboardingStep.CONFIRM and profile:
            return self.build_summary(profile)
        return template

    def start(self, user_id: str) -> str:
        """Start or restart onboarding. Returns the first question."""
        profile = UserProfile(user_id=user_id)
        profile._blocks_asked = False  # type: ignore[attr-defined]
        self._profiles[user_id] = profile
        return self.get_question(OnboardingStep.NAME)

    def process_step(
        self,
        user_id: str,
        text: str,
        current_step: OnboardingStep,
    ) -> tuple[Optional[OnboardingStep], str]:
        """
        Process user input for the current step.
        Returns (next_step, response_text).
        next_step is None when onboarding is complete (user confirmed).
        """
        profile = self._profiles.get(user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)
            profile._blocks_asked = False  # type: ignore[attr-defined]
            self._profiles[user_id] = profile

        try:
            self.validate_input(current_step, text)
        except InvalidProfileDataError as exc:
            # Return same step with error message
            return current_step, str(exc)

        # Apply input to profile
        self._apply_input(profile, current_step, text)

        # Determine next step
        next_step = self._next_step(current_step)
        if next_step is None:
            # CONFIRM step — check user response
            return self._handle_confirm(user_id, profile, text)

        response = self.get_question(next_step, profile)
        return next_step, response

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get the in-progress profile for a user."""
        return self._profiles.get(user_id)

    def complete(self, user_id: str) -> Optional[UserProfile]:
        """Mark onboarding complete and return the final profile."""
        profile = self._profiles.get(user_id)
        if profile:
            profile.onboarding_completed = True
            del self._profiles[user_id]
        return profile

    def validate_input(self, step: OnboardingStep, text: str) -> None:
        """Validate input for a given step. Raises InvalidProfileDataError."""
        text = text.strip()
        if not text:
            raise InvalidProfileDataError("El campo no puede estar vacio.")

        if step == OnboardingStep.NAME:
            if len(text) < 2 or len(text) > 50:
                raise InvalidProfileDataError(
                    "El nombre debe tener entre 2 y 50 caracteres."
                )

        elif step == OnboardingStep.OCCUPATION:
            if len(text) < 2 or len(text) > 100:
                raise InvalidProfileDataError(
                    "La ocupacion debe tener entre 2 y 100 caracteres."
                )

        elif step in (OnboardingStep.WORK_START, OnboardingStep.WORK_END):
            if not _TIME_RE.match(text):
                raise InvalidProfileDataError(
                    "Formato de hora invalido. Usa HH:MM (ej. 08:00)."
                )

        elif step == OnboardingStep.PROTECTED_BLOCKS:
            if text.lower() != "no":
                for block_str in text.split(","):
                    block_str = block_str.strip()
                    if not _BLOCK_RE.match(block_str):
                        raise InvalidProfileDataError(
                            "Formato invalido. Usa: HH:MM-HH:MM etiqueta\n"
                            "Ejemplo: 12:00-13:00 Almuerzo\n"
                            "Si no tienes bloques, escribe 'no'."
                        )

        elif step == OnboardingStep.COMMUNICATION_STYLE:
            key = text.lower().strip()
            if key not in _STYLE_MAP:
                raise InvalidProfileDataError(
                    "Opcion no valida. Escribe 1, 2, 3 o el nombre del estilo "
                    "(gentle, direct, confrontational)."
                )

        elif step == OnboardingStep.CONFIRM:
            if text.lower().strip() not in ("si", "sí", "no"):
                raise InvalidProfileDataError(
                    "Responde 'Si' para confirmar o 'No' para empezar de nuevo."
                )

    def build_summary(self, profile: UserProfile) -> str:
        """Build a formatted summary of the profile for confirmation."""
        work_start_str = profile.work_start.strftime("%H:%M") if profile.work_start else "N/A"
        work_end_str = profile.work_end.strftime("%H:%M") if profile.work_end else "N/A"

        blocks_str = "Ninguno"
        if profile.protected_blocks:
            blocks_lines = []
            for b in profile.protected_blocks:
                blocks_lines.append(f"  {b['start']}-{b['end']} {b['label']}")
            blocks_str = "\n".join(blocks_lines)

        style_labels = {
            CommunicationStyle.GENTLE: "Amable",
            CommunicationStyle.DIRECT: "Directo",
            CommunicationStyle.CONFRONTATIONAL: "Desafiante",
        }
        style_label = style_labels.get(profile.communication_style, str(profile.communication_style))

        return (
            "Este es tu perfil:\n\n"
            f"Nombre: {profile.name}\n"
            f"Ocupacion: {profile.occupation}\n"
            f"Horario: {work_start_str} - {work_end_str}\n"
            f"Bloques protegidos:\n{blocks_str}\n"
            f"Estilo de comunicacion: {style_label}\n\n"
            "Esta todo correcto? (Si/No)"
        )

    def _apply_input(self, profile: UserProfile, step: OnboardingStep, text: str) -> None:
        """Apply validated input to the profile."""
        text = text.strip()

        if step == OnboardingStep.NAME:
            profile.name = text

        elif step == OnboardingStep.OCCUPATION:
            profile.occupation = text

        elif step == OnboardingStep.WORK_START:
            parts = text.split(":")
            profile.work_start = time(int(parts[0]), int(parts[1]))

        elif step == OnboardingStep.WORK_END:
            parts = text.split(":")
            profile.work_end = time(int(parts[0]), int(parts[1]))

        elif step == OnboardingStep.PROTECTED_BLOCKS:
            if text.lower() == "no":
                profile.protected_blocks = []
            else:
                blocks = []
                for block_str in text.split(","):
                    block_str = block_str.strip()
                    time_range, label = block_str.split(" ", 1)
                    start_t, end_t = time_range.split("-")
                    blocks.append({
                        "start": start_t,
                        "end": end_t,
                        "label": label.strip(),
                    })
                profile.protected_blocks = blocks
            profile._blocks_asked = True  # type: ignore[attr-defined]

        elif step == OnboardingStep.COMMUNICATION_STYLE:
            key = text.lower().strip()
            profile.communication_style = _STYLE_MAP[key]

    def _next_step(self, current: OnboardingStep) -> Optional[OnboardingStep]:
        """Return the next step, or None if current is last before CONFIRM."""
        idx = _STEP_ORDER.index(current)
        if idx + 1 >= len(_STEP_ORDER):
            return None
        return _STEP_ORDER[idx + 1]

    def _handle_confirm(
        self,
        user_id: str,
        profile: UserProfile,
        text: str,
    ) -> tuple[Optional[OnboardingStep], str]:
        """Handle the confirm step response."""
        answer = text.strip().lower()
        if answer in ("si", "sí"):
            # Onboarding complete
            logger.info("onboarding.completed", user_id=user_id, name=profile.name)
            return None, "Perfil guardado! Ya estamos listos para trabajar juntos."
        else:
            # Restart onboarding
            logger.info("onboarding.restarted", user_id=user_id)
            return OnboardingStep.NAME, self.start(user_id)
