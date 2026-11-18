import httpx

from keitaro_wrapper.application.campaigns.create import CreateCampaignUseCase
from keitaro_wrapper.application.campaigns.fetch import FetchCampaignUseCase
from keitaro_wrapper.application.campaigns.get import GetCampaignUseCase
from keitaro_wrapper.application.campaigns.import_campaign import (
    ImportCampaignUseCase,
)
from keitaro_wrapper.application.campaigns.list import ListCampaignsUseCase
from keitaro_wrapper.application.common.execution import CommandExecutor
from keitaro_wrapper.application.common.synchronization import Synchronization
from keitaro_wrapper.application.health.check import CheckReadinessUseCase
from keitaro_wrapper.application.offers.search import SearchOffersUseCase
from keitaro_wrapper.application.operations.get import GetOperationUseCase
from keitaro_wrapper.application.operations.manage import ManageOperationUseCase
from keitaro_wrapper.application.ports.clock import IClock
from keitaro_wrapper.application.ports.keitaro import IKeitaroGateway
from keitaro_wrapper.application.streams.edit import EditStreamUseCase
from keitaro_wrapper.application.streams.push import PushStreamUseCase
from keitaro_wrapper.common.clock import Clock
from keitaro_wrapper.config import Settings
from keitaro_wrapper.infrastructure.keitaro.client import KeitaroClient
from keitaro_wrapper.infrastructure.keitaro.gateway import KeitaroGateway
from keitaro_wrapper.infrastructure.persistence.database import Database


class Container:
    def __init__(
        self,
        settings: Settings,
        database: Database | None = None,
        gateway: IKeitaroGateway | None = None,
        clock: IClock | None = None,
    ) -> None:
        self.clock = clock or Clock()
        self.settings = settings
        self.database = database or Database(settings.database_url.get_secret_value())
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                settings.http_read_timeout,
                connect=settings.http_connect_timeout,
                pool=5,
                write=10,
            )
        )
        self.gateway = gateway or KeitaroGateway(KeitaroClient(self.client, settings))
        self.sync = Synchronization(self.database, self.gateway, self.clock)
        self.edit = EditStreamUseCase(self.database, self.gateway, self.clock)
        self.fetch = FetchCampaignUseCase(self.database, self.sync, self.clock)
        self.push = PushStreamUseCase(self.database, self.sync, self.clock)
        self.create = CreateCampaignUseCase(self.database, self.sync, self.clock)
        self.importer = ImportCampaignUseCase(self.database, self.fetch, self.clock)
        self.get_campaign = GetCampaignUseCase(self.database)
        self.search = SearchOffersUseCase(self.database, self.gateway)
        self.manage = ManageOperationUseCase(
            self.database,
            self.sync,
            self.fetch,
            self.push,
            self.create,
            self.clock,
        )

        self.executor = CommandExecutor(
            self.database,
            self.sync,
            settings.http_operation_timeout,
            self.clock,
        )
        self.list_campaigns = ListCampaignsUseCase(self.database)
        self.get_operation = GetOperationUseCase(self.database)
        self.readiness = CheckReadinessUseCase(self.database)
