from fastapi import Request
from fastapi.responses import JSONResponse

from keitaro_wrapper.api.common.schemas.errors import ErrorOut


def error_response(
    code: str,
    message: str,
    request: Request,
    status: int,
    details: object = None,
) -> JSONResponse:
    payload = ErrorOut.model_validate(
        {
            "error": {"code": code, "message": message, "details": details or {}},
            "request_id": getattr(request.state, "request_id", ""),
        }
    )
    return JSONResponse(payload.model_dump(mode="json"), status_code=status)


def domain_error_status(code: str) -> int:
    if code == "not_found":
        return 404
    if code in {"invalid_weights", "last_offer", "invalid_command", "confirmation_required"}:
        return 422
    if code in {
        "integration_unconfigured",
        "creation_not_verified",
        "invalid_configuration",
        "service_unavailable",
        "integration_unavailable",
    }:
        return 503
    if code.startswith("integration_") or code in {"invalid_response", "remote_not_found"}:
        return 502
    return 409
