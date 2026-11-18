from typing import Annotated

from fastapi import Depends

from keitaro_wrapper.api.common.depends.container import ContainerDep
from keitaro_wrapper.config import Settings


def get_settings(container: ContainerDep) -> Settings:
    return container.settings


SettingsDep = Annotated[Settings, Depends(get_settings)]
