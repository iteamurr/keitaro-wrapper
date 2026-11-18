from typing import Protocol


class IReadiness(Protocol):
    async def ready(self) -> bool: ...
