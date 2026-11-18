from fastapi import APIRouter, Response

from keitaro_wrapper.api.health.depends import ReadinessDep
from keitaro_wrapper.api.health.schemas import HealthOut

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthOut)
async def live() -> HealthOut:
    return HealthOut(status="ok")


@router.get("/ready", response_model=HealthOut, responses={503: {"model": HealthOut}})
async def ready(response: Response, use_case: ReadinessDep) -> HealthOut:
    available = await use_case.execute()
    response.status_code = 200 if available else 503
    return HealthOut(status="ok" if available else "not_ready")
