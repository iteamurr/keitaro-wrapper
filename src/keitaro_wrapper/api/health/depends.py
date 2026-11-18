from typing import Annotated

from fastapi import Depends

from keitaro_wrapper.api.common.depends.container import ContainerDep
from keitaro_wrapper.application.health.check import CheckReadinessUseCase


def get_readiness(container: ContainerDep) -> CheckReadinessUseCase:
    return container.readiness


ReadinessDep = Annotated[CheckReadinessUseCase, Depends(get_readiness)]
