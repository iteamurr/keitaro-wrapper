from sqlalchemy.ext.asyncio import AsyncSession

from keitaro_wrapper.application.ports.storage import IUnitOfWork
from keitaro_wrapper.infrastructure.persistence.repositories.campaigns import ORMCampaigns
from keitaro_wrapper.infrastructure.persistence.repositories.catalog import ORMOfferCatalog
from keitaro_wrapper.infrastructure.persistence.repositories.operations import ORMOperations
from keitaro_wrapper.infrastructure.persistence.repositories.streams import ORMStreams


class ORMUnitOfWork(IUnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self._campaigns = ORMCampaigns(session)
        self._streams = ORMStreams(session)
        self._operations = ORMOperations(session)
        self._catalog = ORMOfferCatalog(session)

    @property
    def campaigns(self) -> ORMCampaigns:
        return self._campaigns

    @property
    def streams(self) -> ORMStreams:
        return self._streams

    @property
    def operations(self) -> ORMOperations:
        return self._operations

    @property
    def catalog(self) -> ORMOfferCatalog:
        return self._catalog
