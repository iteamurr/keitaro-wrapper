from keitaro_wrapper.api.common.schemas.base import OutSchema


class CountryOut(OutSchema):
    code: str
    name: str


class BootstrapOut(OutSchema):
    csrf_token: str
    integration_configured: bool
    creation_configured: bool
    prefix: str
    countries: list[CountryOut]
