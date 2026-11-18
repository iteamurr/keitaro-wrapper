from fastapi import APIRouter, Response

from keitaro_wrapper.api.common.depends.commands import CommandExecutorDep, CommandKeyDep
from keitaro_wrapper.api.v1.operations.responses import COMMAND_RESPONSES, operation_response
from keitaro_wrapper.api.v1.operations.schemas import OperationOut
from keitaro_wrapper.api.v1.streams.depends import EditStreamDep, PushStreamDep
from keitaro_wrapper.api.v1.streams.schemas import (
    StreamAddOfferIn,
    StreamPinOfferIn,
    StreamRevisionIn,
)
from keitaro_wrapper.application.streams.edit import EditStreamCommand
from keitaro_wrapper.application.streams.push import PushStreamCommand
from keitaro_wrapper.domain.common.errors import DomainError

router = APIRouter(prefix="/streams", tags=["streams"])


@router.post("/{stream_id}/offers", response_model=OperationOut, responses=COMMAND_RESPONSES)
async def add_offer(
    stream_id: int,
    payload: StreamAddOfferIn,
    response: Response,
    use_case: EditStreamDep,
    executor: CommandExecutorDep,
    key: CommandKeyDep,
) -> OperationOut:
    command = EditStreamCommand(
        key=key,
        stream_id=stream_id,
        expected_revision=payload.expected_revision,
        action="add",
        offer_id=payload.offer_id,
    )
    return operation_response(await executor.execute(key, use_case.execute(command)), response)


@router.post(
    "/{stream_id}/offers/{offer_id}/{action}",
    response_model=OperationOut,
    responses=COMMAND_RESPONSES,
)
async def change_offer(
    stream_id: int,
    offer_id: int,
    action: str,
    payload: StreamRevisionIn,
    response: Response,
    use_case: EditStreamDep,
    executor: CommandExecutorDep,
    key: CommandKeyDep,
) -> OperationOut:
    if action not in ("remove", "restore"):
        raise DomainError("not_found", "Действие не найдено.")
    command = EditStreamCommand(
        key=key,
        stream_id=stream_id,
        expected_revision=payload.expected_revision,
        action=action,
        offer_id=offer_id,
    )
    return operation_response(await executor.execute(key, use_case.execute(command)), response)


@router.put(
    "/{stream_id}/offers/{offer_id}/pin",
    response_model=OperationOut,
    responses=COMMAND_RESPONSES,
)
async def pin_offer(
    stream_id: int,
    offer_id: int,
    payload: StreamPinOfferIn,
    response: Response,
    use_case: EditStreamDep,
    executor: CommandExecutorDep,
    key: CommandKeyDep,
) -> OperationOut:
    command = EditStreamCommand(
        key=key,
        stream_id=stream_id,
        expected_revision=payload.expected_revision,
        action="pin",
        offer_id=offer_id,
        pinned=payload.pinned,
        weight=payload.weight,
    )
    return operation_response(await executor.execute(key, use_case.execute(command)), response)


@router.post("/{stream_id}/{action}", response_model=OperationOut, responses=COMMAND_RESPONSES)
async def change_stream(
    stream_id: int,
    action: str,
    payload: StreamRevisionIn,
    response: Response,
    edit: EditStreamDep,
    push: PushStreamDep,
    executor: CommandExecutorDep,
    key: CommandKeyDep,
) -> OperationOut:
    if action == "push":
        operation = await executor.execute(
            key,
            push.execute(
                PushStreamCommand(
                    key=key,
                    stream_id=stream_id,
                    expected_revision=payload.expected_revision,
                )
            ),
        )
    elif action == "cancel":
        operation = await executor.execute(
            key,
            edit.execute(
                EditStreamCommand(
                    key=key,
                    stream_id=stream_id,
                    expected_revision=payload.expected_revision,
                    action="cancel",
                )
            ),
        )
    else:
        raise DomainError("not_found", "Действие не найдено.")
    return operation_response(operation, response)
