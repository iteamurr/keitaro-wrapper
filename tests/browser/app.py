"""Isolated synthetic application used only by the browser smoke test."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.engine import make_url

from keitaro_wrapper.application.campaigns.import_campaign import ImportCampaignCommand
from keitaro_wrapper.bootstrap.container import Container
from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.config import Settings
from keitaro_wrapper.infrastructure.keitaro.gateway import KeitaroGateway
from keitaro_wrapper.main import create_app
from tests.support.fakes import FakeKeitaro


def browser_app() -> FastAPI:
    database_url = os.environ["TEST_DATABASE_URL"]
    if not (make_url(database_url).database or "").startswith("test_"):
        raise RuntimeError("Browser tests require an isolated test_ database")
    settings = Settings(
        _env_file=None,
        database_url=database_url,
        app_secret_key="synthetic-browser-session-key-1234567890",
        keitaro_api_key="synthetic-key",
        keitaro_creation_profile=Path("synthetic-profile"),
    )
    services = Container(settings, gateway=KeitaroGateway(FakeKeitaro()))
    app = create_app(settings, services)
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with services.database.engine.begin() as connection:
            await connection.execute(
                text(
                    "TRUNCATE operation_attempts, operations, stream_editors, offer_catalog, campaigns, integration_binding CASCADE"
                )
            )
        async with original(app):
            await services.importer.execute(ImportCampaignCommand(Identity.new(), 7))
            yield

    app.router.lifespan_context = lifespan
    return app
