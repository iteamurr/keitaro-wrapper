from abc import ABC, abstractmethod
from uuid import UUID

from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.domain.common.snapshot import Snapshot
from keitaro_wrapper.domain.operations.entity import Operation


class IOperations(ABC):
    @abstractmethod
    async def save(self, entity: Operation) -> None:
        """Persist the command receipt and recovery checkpoint."""

    @abstractmethod
    async def record_attempt(self, operation: Operation, stage: str, expected: Snapshot) -> int:
        """Record an uncertain write before it is sent."""

    @abstractmethod
    async def confirm_attempt(self, operation_id: UUID, number: int) -> None:
        """Record a confirmed remote response."""

    @abstractmethod
    async def get(self, key: UUID) -> Operation | None:
        """Get a command receipt."""

    @abstractmethod
    async def active(self, campaign_id: UUID) -> Operation | None:
        """Get the operation reserving the campaign."""

    @abstractmethod
    async def list(self, campaign_id: UUID) -> list[Operation]:
        """Get recent external operations for a campaign."""

    async def require(self, key: UUID) -> Operation:
        operation = await self.get(key)
        if operation is None:
            raise DomainError("not_found", "Операция не найдена.")
        return operation
