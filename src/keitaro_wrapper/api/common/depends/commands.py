from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header

from keitaro_wrapper.api.common.depends.container import ContainerDep
from keitaro_wrapper.application.common.execution import CommandExecutor


def get_command_key(idempotency_key: Annotated[UUID, Header()]) -> UUID:
    return idempotency_key


def get_command_executor(container: ContainerDep) -> CommandExecutor:
    return container.executor


CommandKeyDep = Annotated[UUID, Depends(get_command_key)]
CommandExecutorDep = Annotated[CommandExecutor, Depends(get_command_executor)]
