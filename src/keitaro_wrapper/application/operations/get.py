from dataclasses import dataclass
from uuid import UUID

from keitaro_wrapper.application.operations.views import OperationView
from keitaro_wrapper.application.ports.storage import ITransactions


@dataclass
class GetOperationUseCase:
    transactions: ITransactions

    async def execute(self, operation_id: UUID) -> OperationView:
        async with self.transactions.transaction() as store:
            operation = await store.operations.require(operation_id)
        return OperationView.from_entity(operation)
