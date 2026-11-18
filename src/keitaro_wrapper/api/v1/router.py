from fastapi import APIRouter

from keitaro_wrapper.api.common.schemas.errors import ErrorOut
from keitaro_wrapper.api.v1.bootstrap.handlers import router as bootstrap_router
from keitaro_wrapper.api.v1.campaigns.handlers import router as campaigns_router
from keitaro_wrapper.api.v1.offers.handlers import router as offers_router
from keitaro_wrapper.api.v1.operations.handlers import router as operations_router
from keitaro_wrapper.api.v1.streams.handlers import router as streams_router

router = APIRouter(
    prefix="/api/v1",
    responses={code: {"model": ErrorOut} for code in (403, 404, 409, 415, 422, 502, 503)},
)
for feature_router in (
    bootstrap_router,
    campaigns_router,
    streams_router,
    offers_router,
    operations_router,
):
    router.include_router(feature_router)
