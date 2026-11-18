from abc import ABC, abstractmethod
from types import TracebackType

from keitaro_wrapper.application.ports.repositories.campaigns import ICampaigns
from keitaro_wrapper.application.ports.repositories.catalog import IOfferCatalog
from keitaro_wrapper.application.ports.repositories.operations import IOperations
from keitaro_wrapper.application.ports.repositories.streams import IStreams


class IUnitOfWork(ABC):
    """Repositories sharing one transaction; no generic persistence methods."""

    @property
    @abstractmethod
    def campaigns(self) -> ICampaigns: ...

    @property
    @abstractmethod
    def streams(self) -> IStreams: ...

    @property
    @abstractmethod
    def operations(self) -> IOperations: ...

    @property
    @abstractmethod
    def catalog(self) -> IOfferCatalog: ...


class ITransactionContext(ABC):
    """Open an isolated, short transaction and its persistence ports."""

    @abstractmethod
    async def __aenter__(self) -> IUnitOfWork:
        """Start a transaction."""

    @abstractmethod
    async def __aexit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Commit on success and roll back on failure."""


class ITransactions(ABC):
    """Factory for transaction contexts; never shares a session across requests."""

    @abstractmethod
    def transaction(self) -> ITransactionContext:
        """Build a new transaction context."""
