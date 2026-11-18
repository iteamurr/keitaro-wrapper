from typing import Annotated

from fastapi import Depends, Query

from keitaro_wrapper.api.common.depends.container import ContainerDep
from keitaro_wrapper.api.common.depends.pagination import get_pagination
from keitaro_wrapper.api.v1.offers.schemas import OfferSearchIn
from keitaro_wrapper.application.offers.search import SearchOffersQuery, SearchOffersUseCase


def get_offer_search_use_case(container: ContainerDep) -> SearchOffersUseCase:
    return container.search


SearchOffersDep = Annotated[SearchOffersUseCase, Depends(get_offer_search_use_case)]


def get_offer_search(params: Annotated[OfferSearchIn, Query()]) -> SearchOffersQuery:
    return SearchOffersQuery(query=params.q, pagination=get_pagination(params))


OfferSearchQueryDep = Annotated[SearchOffersQuery, Depends(get_offer_search)]
