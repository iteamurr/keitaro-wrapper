import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from keitaro_wrapper.api.common.responses.errors import domain_error_status, error_response
from keitaro_wrapper.domain.common.errors import DomainError

logger = logging.getLogger(__name__)


async def domain_error(request: Request, error: DomainError) -> JSONResponse:
    return error_response(
        error.code,
        error.message,
        request,
        domain_error_status(error.code),
        error.details,
    )


async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    fields = [
        {"field": ".".join(map(str, item["loc"])), "type": item["type"]} for item in error.errors()
    ]
    return error_response(
        "validation_error",
        "Проверьте обязательные поля и допустимые значения.",
        request,
        422,
        fields,
    )


async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
    logger.error(
        "request_failed type=%s request_id=%s",
        type(error).__name__,
        getattr(request.state, "request_id", ""),
    )
    return error_response(
        "service_unavailable",
        "Сервис временно недоступен. Проверьте состояние операции перед повтором.",
        request,
        503,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.exception_handler(DomainError)(domain_error)
    app.exception_handler(RequestValidationError)(validation_error)
    app.exception_handler(Exception)(unexpected_error)
