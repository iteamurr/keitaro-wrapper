from typing import Annotated

from fastapi import Depends, Query

from keitaro_wrapper.api.common.depends.container import ContainerDep
from keitaro_wrapper.api.common.depends.pagination import get_pagination
from keitaro_wrapper.api.v1.campaigns.schemas import CampaignListIn
from keitaro_wrapper.application.campaigns.create import CreateCampaignUseCase
from keitaro_wrapper.application.campaigns.fetch import FetchCampaignUseCase
from keitaro_wrapper.application.campaigns.get import GetCampaignUseCase
from keitaro_wrapper.application.campaigns.import_campaign import ImportCampaignUseCase
from keitaro_wrapper.application.campaigns.list import ListCampaignsUseCase
from keitaro_wrapper.common.pagination import Pagination


def get_create_campaign(container: ContainerDep) -> CreateCampaignUseCase:
    return container.create


CreateCampaignDep = Annotated[CreateCampaignUseCase, Depends(get_create_campaign)]


def get_import_campaign(container: ContainerDep) -> ImportCampaignUseCase:
    return container.importer


ImportCampaignDep = Annotated[ImportCampaignUseCase, Depends(get_import_campaign)]


def get_fetch_campaign(container: ContainerDep) -> FetchCampaignUseCase:
    return container.fetch


FetchCampaignDep = Annotated[FetchCampaignUseCase, Depends(get_fetch_campaign)]


def get_campaign_reader(container: ContainerDep) -> GetCampaignUseCase:
    return container.get_campaign


GetCampaignDep = Annotated[GetCampaignUseCase, Depends(get_campaign_reader)]


def get_campaign_lister(container: ContainerDep) -> ListCampaignsUseCase:
    return container.list_campaigns


ListCampaignsDep = Annotated[ListCampaignsUseCase, Depends(get_campaign_lister)]


def get_campaign_pagination(params: Annotated[CampaignListIn, Query()]) -> Pagination:
    return get_pagination(params)


CampaignPaginationDep = Annotated[Pagination, Depends(get_campaign_pagination)]
