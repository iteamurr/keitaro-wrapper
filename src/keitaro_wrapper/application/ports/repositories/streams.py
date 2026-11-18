from abc import ABC, abstractmethod
from uuid import UUID

from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.domain.streams.editor import StreamEditor


class IStreams(ABC):
    @abstractmethod
    async def save(self, entity: StreamEditor) -> None:
        """Persist a whole stream aggregate."""

    @abstractmethod
    async def get(self, key: int) -> StreamEditor | None:
        """Get an editor by Keitaro stream ID."""

    @abstractmethod
    async def list(self, campaign_id: UUID) -> list[StreamEditor]:
        """Get the editors belonging to a campaign."""

    async def require(self, key: int) -> StreamEditor:
        stream = await self.get(key)
        if stream is None:
            raise DomainError("not_found", "Поток не найден.")
        return stream
