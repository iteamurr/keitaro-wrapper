from abc import ABC, abstractmethod
from uuid import UUID

from keitaro_wrapper.domain.campaigns.entity import Campaign
from keitaro_wrapper.domain.common.errors import DomainError


class ICampaigns(ABC):
    @abstractmethod
    async def save(self, entity: Campaign) -> None:
        """Persist a campaign."""

    @abstractmethod
    async def get(self, key: UUID, lock: bool = False) -> Campaign | None:
        """Get a campaign, optionally locking it for update."""

    @abstractmethod
    async def by_remote(self, remote_id: int) -> Campaign | None:
        """Find an imported campaign by its remote identity."""

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> list[Campaign]:
        """List local campaigns."""

    @abstractmethod
    async def count(self) -> int:
        """Count campaigns before pagination."""

    async def require(self, key: UUID, lock: bool = False) -> Campaign:
        campaign = await self.get(key, lock)
        if campaign is None:
            raise DomainError("not_found", "Кампания не найдена.")
        return campaign
