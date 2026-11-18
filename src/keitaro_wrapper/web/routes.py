from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

WEB_ROOT = Path(__file__).resolve().parent
router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=WEB_ROOT / "templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"campaign_id": ""},
    )


@router.get("/campaigns/{campaign_id}", response_class=HTMLResponse)
async def editor(request: Request, campaign_id: UUID) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"campaign_id": str(campaign_id)},
    )
