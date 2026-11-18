import secrets

import pycountry
from fastapi import APIRouter, Request

from keitaro_wrapper.api.common.depends.settings import SettingsDep
from keitaro_wrapper.api.v1.bootstrap.schemas import BootstrapOut, CountryOut

router = APIRouter(tags=["bootstrap"])


@router.get("/bootstrap", response_model=BootstrapOut)
async def bootstrap(request: Request, settings: SettingsDep) -> BootstrapOut:
    request.session.setdefault("csrf", secrets.token_urlsafe(32))
    return BootstrapOut(
        csrf_token=request.session["csrf"],
        integration_configured=bool(settings.keitaro_api_key.get_secret_value()),
        creation_configured=settings.keitaro_creation_profile is not None,
        prefix=settings.campaign_name_prefix,
        countries=[
            CountryOut(code=country.alpha_2, name=country.name)
            for country in sorted(pycountry.countries, key=lambda country: country.name)
        ],
    )
