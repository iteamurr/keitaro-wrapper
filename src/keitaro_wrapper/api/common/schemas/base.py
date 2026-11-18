from pydantic import BaseModel, ConfigDict


class InSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


def omit_none(value: object) -> bool:
    """Omit absent optional fields without replacing their OpenAPI schemas."""
    return value is None
