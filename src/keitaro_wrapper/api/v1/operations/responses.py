from fastapi import Response

from keitaro_wrapper.api.common.schemas.errors import ErrorOut
from keitaro_wrapper.api.v1.operations.schemas import OperationOut
from keitaro_wrapper.application.operations.views import OperationView
from keitaro_wrapper.domain.operations.entity import Operation

COMMAND_RESPONSES: dict[int | str, dict[str, object]] = {
    202: {"model": OperationOut},
    409: {"model": OperationOut | ErrorOut},
    502: {"model": OperationOut | ErrorOut},
}


def operation_response(
    operation: Operation,
    response: Response,
    *,
    created: bool = False,
) -> OperationOut:
    status_codes = {
        "running": 202,
        "unknown": 202,
        "manual_review": 202,
        "partial": 202,
        "conflict": 409,
        "failed": 502,
        "succeeded": 201 if created else 200,
    }
    response.status_code = status_codes[operation.status]
    return OperationOut.model_validate(OperationView.from_entity(operation))
