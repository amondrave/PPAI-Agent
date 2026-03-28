from typing import Optional, Protocol

from ppai.profile.domain.entities import UserProfile


class ProfileRepository(Protocol):
    def get(self, user_id: str) -> Optional[UserProfile]: ...

    def save(self, profile: UserProfile) -> None: ...

    def exists(self, user_id: str) -> bool: ...


class ProfileTelegramPort(Protocol):
    def send_message(self, chat_id: str, text: str) -> bool: ...
