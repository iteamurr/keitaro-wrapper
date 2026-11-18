from typing import Annotated

from fastapi import Depends

from keitaro_wrapper.api.common.depends.container import ContainerDep
from keitaro_wrapper.application.streams.edit import EditStreamUseCase
from keitaro_wrapper.application.streams.push import PushStreamUseCase


def get_edit_stream(container: ContainerDep) -> EditStreamUseCase:
    return container.edit


EditStreamDep = Annotated[EditStreamUseCase, Depends(get_edit_stream)]


def get_push_stream(container: ContainerDep) -> PushStreamUseCase:
    return container.push


PushStreamDep = Annotated[PushStreamUseCase, Depends(get_push_stream)]
