from typing import Annotated

from fastapi import Depends

from keitaro_wrapper.api.common.depends.container import ContainerDep
from keitaro_wrapper.application.operations.get import GetOperationUseCase
from keitaro_wrapper.application.operations.manage import ManageOperationUseCase


def get_operation_manager(container: ContainerDep) -> ManageOperationUseCase:
    return container.manage


ManageOperationDep = Annotated[ManageOperationUseCase, Depends(get_operation_manager)]


def get_operation_reader(container: ContainerDep) -> GetOperationUseCase:
    return container.get_operation


GetOperationDep = Annotated[GetOperationUseCase, Depends(get_operation_reader)]
