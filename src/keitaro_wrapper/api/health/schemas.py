from typing import Literal

from keitaro_wrapper.api.common.schemas.base import OutSchema


class HealthOut(OutSchema):
    status: Literal["ok", "not_ready"]
