from abc import ABC, abstractmethod

from keitaro_wrapper.application.ports.remote import RemoteOffer


class IOfferCatalog(ABC):
    @abstractmethod
    async def replace(self, offers: list[RemoteOffer]) -> None:
        """Atomically replace the offer cache."""

    @abstractmethod
    async def get(self) -> tuple[list[RemoteOffer], float]:
        """Return cached offers and age in seconds, infinity for an absent cache."""
