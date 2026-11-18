from uuid import UUID

from fastapi import APIRouter, Response

from keitaro_wrapper.api.common.depends.commands import CommandExecutorDep, CommandKeyDep
from keitaro_wrapper.api.common.schemas.pagination import PageOut
from keitaro_wrapper.api.v1.campaigns.depends import (
    CampaignPaginationDep,
    CreateCampaignDep,
    FetchCampaignDep,
    GetCampaignDep,
    ImportCampaignDep,
    ListCampaignsDep,
)
from keitaro_wrapper.api.v1.campaigns.schemas import (
    CampaignCreateIn,
    CampaignFetchIn,
    CampaignImportIn,
    CampaignOut,
    CampaignSummaryOut,
)
from keitaro_wrapper.api.v1.operations.responses import COMMAND_RESPONSES, operation_response
from keitaro_wrapper.api.v1.operations.schemas import OperationOut
from keitaro_wrapper.application.campaigns.create import CreateCampaignCommand
from keitaro_wrapper.application.campaigns.fetch import FetchCampaignCommand
from keitaro_wrapper.application.campaigns.import_campaign import ImportCampaignCommand

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=PageOut[CampaignSummaryOut])
async def list_campaigns(
    use_case: ListCampaignsDep,
    pagination: CampaignPaginationDep,
) -> PageOut[CampaignSummaryOut]:
    return PageOut[CampaignSummaryOut].model_validate(await use_case.execute(pagination))


@router.post("", response_model=OperationOut, status_code=201, responses=COMMAND_RESPONSES)
async def create_campaign(
    payload: CampaignCreateIn,
    response: Response,
    use_case: CreateCampaignDep,
    executor: CommandExecutorDep,
    key: CommandKeyDep,
) -> OperationOut:
    command = CreateCampaignCommand(
        key=key,
        name=payload.name,
        country_code=payload.country_code,
        offer_id=payload.offer_id,
    )
    operation = await executor.execute(key, use_case.execute(command))
    return operation_response(operation, response, created=True)


@router.post("/import", response_model=OperationOut, status_code=201, responses=COMMAND_RESPONSES)
async def import_campaign(
    payload: CampaignImportIn,
    response: Response,
    use_case: ImportCampaignDep,
    executor: CommandExecutorDep,
    key: CommandKeyDep,
) -> OperationOut:
    command = ImportCampaignCommand(key=key, remote_id=payload.keitaro_campaign_id)
    operation = await executor.execute(key, use_case.execute(command))
    return operation_response(operation, response, created=True)


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(campaign_id: UUID, use_case: GetCampaignDep) -> CampaignOut:
    return CampaignOut.model_validate(await use_case.execute(campaign_id))


@router.post("/{campaign_id}/fetch", response_model=OperationOut, responses=COMMAND_RESPONSES)
async def fetch_campaign(
    campaign_id: UUID,
    payload: CampaignFetchIn,
    response: Response,
    use_case: FetchCampaignDep,
    executor: CommandExecutorDep,
    key: CommandKeyDep,
) -> OperationOut:
    command = FetchCampaignCommand(
        key=key,
        campaign_id=campaign_id,
        expected_revision=payload.expected_revision,
    )
    operation = await executor.execute(key, use_case.execute(command))
    return operation_response(operation, response)
