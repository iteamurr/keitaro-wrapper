import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from keitaro_wrapper.application.campaigns.import_campaign import ImportCampaignCommand
from keitaro_wrapper.bootstrap.container import Container
from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.config import Settings
from keitaro_wrapper.infrastructure.keitaro.gateway import KeitaroGateway
from keitaro_wrapper.infrastructure.persistence.database import Database
from tests.support.fakes import FakeKeitaro

TEST_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://wrapper:wrapper@127.0.0.1:55432/test_keitaro",
)


@pytest.fixture(scope="session")
def migrated_database():
    url = make_url(TEST_URL)
    if not url.database or not url.database.startswith("test_"):
        raise RuntimeError("Test database must use a test_ prefix")
    env = {**os.environ, "DATABASE_URL": TEST_URL}
    subprocess.run(
        [str(Path(".venv/bin/alembic").resolve()), "upgrade", "head"],
        check=True,
        env=env,
    )
    return TEST_URL


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        database_url=TEST_URL,
        app_secret_key="synthetic-test-session-key-not-production-123",
        keitaro_base_url="https://tracker.example.invalid",
        keitaro_api_key="synthetic-key",
    )


@pytest.fixture
async def database(migrated_database):
    db = Database(migrated_database)
    async with db.engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE operation_attempts, operations, stream_editors, offer_catalog, campaigns, integration_binding CASCADE"
            )
        )
    await db.start("https://tracker.example.invalid")
    yield db
    await db.close()


@pytest.fixture
def gateway():
    return FakeKeitaro()


@pytest.fixture
async def container(settings, database, gateway):
    services = Container(settings, database, KeitaroGateway(gateway))
    yield services
    await services.client.aclose()


@pytest.fixture
async def imported(container):
    return await container.importer.execute(ImportCampaignCommand(Identity.new(), 7))
