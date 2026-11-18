from dataclasses import dataclass

from keitaro_wrapper.application.ports.health import IReadiness


@dataclass
class CheckReadinessUseCase:
    probe: IReadiness

    async def execute(self) -> bool:
        try:
            return await self.probe.ready()
        except Exception:
            return False
