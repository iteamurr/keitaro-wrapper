from dataclasses import asdict, dataclass
from uuid import UUID

from keitaro_wrapper.application.common.commands import Commands
from keitaro_wrapper.application.ports.clock import IClock
from keitaro_wrapper.application.ports.keitaro import IKeitaroGateway
from keitaro_wrapper.application.ports.storage import ITransactions
from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.domain.operations.entity import Operation


@dataclass
class EditStreamCommand:
    key: UUID
    stream_id: int
    expected_revision: int
    action: str
    offer_id: int | None = None
    pinned: bool = False
    weight: int | None = None


@dataclass
class EditStreamUseCase:
    """Apply an atomic local edit; no remote write occurs."""

    transactions: ITransactions
    gateway: IKeitaroGateway
    clock: IClock

    async def execute(self, command: EditStreamCommand) -> Operation:
        payload = asdict(command)
        payload.pop("key")
        async with self.transactions.transaction() as store:
            previous = await Commands.replay(store.operations, command.key, "edit", payload)
            if previous:
                return previous
        # Validate an external dependency outside the database transaction.
        offer = None
        if command.action in ("add", "restore") and command.offer_id is not None:
            offer = await self.gateway.offer(command.offer_id)
        async with self.transactions.transaction() as store:
            stream = await store.streams.require(command.stream_id)
            campaign = await store.campaigns.require(stream.campaign_id, lock=True)
            previous = await Commands.replay(store.operations, command.key, "edit", payload)
            if previous:
                return previous
            await Commands.unlocked(store.operations, campaign.id)
            stream = await store.streams.require(command.stream_id)
            Commands.revision(stream.revision, command.expected_revision)
            if command.action == "cancel":
                stream.cancel()
            elif command.action in ("add", "restore") and offer and command.offer_id:
                if command.action == "restore":
                    stream.restore(command.offer_id, offer.name)
                else:
                    stream.add(command.offer_id, offer.name)
            elif command.action == "remove" and command.offer_id:
                stream.remove(command.offer_id)
            elif command.action == "pin" and command.offer_id:
                stream.pin(command.offer_id, command.pinned, command.weight)
            else:
                raise DomainError("invalid_command", "Неизвестная команда редактора.")
            campaign.touch()
            operation = Commands.build(
                command.key,
                "edit",
                campaign.id,
                payload,
                stream.id,
                False,
                now=self.clock.now(),
            )
            operation.transition(
                "succeeded",
                {"campaign_id": str(campaign.id), "stream_id": stream.id},
                at=self.clock.now(),
            )
            await store.streams.save(stream)
            await store.campaigns.save(campaign)
            await store.operations.save(operation)
            return operation
