from pydantic import JsonValue

from keitaro_wrapper.api.common.schemas.base import OutSchema


class ErrorDetailOut(OutSchema):
    code: str
    message: str
    details: dict[str, JsonValue] | list[dict[str, JsonValue]]


class ErrorOut(OutSchema):
    error: ErrorDetailOut
    request_id: str
