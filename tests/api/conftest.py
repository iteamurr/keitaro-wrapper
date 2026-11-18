import httpx
import pytest
from asgi_lifespan import LifespanManager

from keitaro_wrapper.main import create_app


@pytest.fixture
def app(container, settings):
    return create_app(settings, container)


@pytest.fixture
async def client(app):
    async with LifespanManager(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app, raise_app_exceptions=False),
            base_url="http://testserver",
        ) as client:
            bootstrap = (await client.get("/api/v1/bootstrap")).json()
            client.headers["X-CSRF-Token"] = bootstrap["csrf_token"]
            yield client
