from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from keitaro_wrapper.bootstrap.container import Container


class ApplicationLifespan:
    def __init__(self, container: Container) -> None:
        self.container = container

    @asynccontextmanager
    async def __call__(self, app: FastAPI) -> AsyncIterator[None]:
        owns_database = self.container.database.owner is None
        try:
            if owns_database:
                await self.container.database.start(self.container.settings.keitaro_base_url)
            yield
        finally:
            await self.container.client.aclose()
            if owns_database:
                await self.container.database.close()
