from fastapi import APIRouter

from keitaro_wrapper.api.common.schemas.pagination import PageOut
from keitaro_wrapper.api.v1.offers.depends import OfferSearchQueryDep, SearchOffersDep
from keitaro_wrapper.api.v1.offers.schemas import OfferOut

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("", response_model=PageOut[OfferOut])
async def search_offers(use_case: SearchOffersDep, query: OfferSearchQueryDep) -> PageOut[OfferOut]:
    return PageOut[OfferOut].model_validate(await use_case.execute(query))
