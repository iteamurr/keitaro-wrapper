from uuid import UUID

from fastapi import APIRouter, Response

from keitaro_wrapper.api.common.depends.commands import CommandExecutorDep, CommandKeyDep
from keitaro_wrapper.api.v1.operations.depends import GetOperationDep, ManageOperationDep
from keitaro_wrapper.api.v1.operations.responses import COMMAND_RESPONSES, operation_response
from keitaro_wrapper.api.v1.operations.schemas import OperationControlIn, OperationOut
from keitaro_wrapper.application.operations.manage import ManageOperationCommand
from keitaro_wrapper.domain.common.errors import DomainError

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/{operation_id}", response_model=OperationOut)
async def get_operation(operation_id: UUID, use_case: GetOperationDep) -> OperationOut:
    return OperationOut.model_validate(await use_case.execute(operation_id))


@router.post("/{operation_id}/{action}", response_model=OperationOut, responses=COMMAND_RESPONSES)
async def control_operation(
    operation_id: UUID,
    action: str,
    payload: OperationControlIn,
    response: Response,
    use_case: ManageOperationDep,
    executor: CommandExecutorDep,
    key: CommandKeyDep,
) -> OperationOut:
    if action not in ("reconcile", "resume", "resolve"):
        raise DomainError("not_found", "Действие не найдено.")
    command = ManageOperationCommand(
        key=key,
        operation_id=operation_id,
        expected_operation_revision=payload.expected_operation_revision,
        action=action,
        decision=payload.decision,
        confirmation=payload.confirmation,
        note=payload.note,
    )
    return operation_response(await executor.execute(key, use_case.execute(command)), response)
