import pytest

from keitaro_wrapper.application.common.commands import Commands
from keitaro_wrapper.common.clock import Clock
from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.domain.campaigns.entity import Campaign
from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.infrastructure.persistence.database import Database

pytestmark = pytest.mark.integration


class TestStorage:
    async def test_when_transaction_fails_then_rolls_back(self, database):
        campaign = Campaign(Identity.new(), "rollback")
        with pytest.raises(ValueError):
            async with database.transaction() as store:
                await store.campaigns.save(campaign)
                raise ValueError("abort")
        async with database.transaction() as store:
            assert await store.campaigns.get(campaign.id) is None

    async def test_when_two_reservations_then_database_rejects(self, database, imported):
        with pytest.raises(DomainError) as caught:
            async with database.transaction() as store:
                for _ in range(2):
                    await store.operations.save(
                        Commands.build(
                            Identity.new(),
                            "fetch",
                            imported.campaign_id,
                            {},
                            now=Clock.now(),
                        )
                    )
        assert caught.value.code == "concurrent_change"
        async with database.transaction() as store:
            assert await store.operations.active(imported.campaign_id) is None

    async def test_when_origin_changes_then_rejected(self, database, migrated_database):
        await database.close()
        other = Database(migrated_database)
        try:
            with pytest.raises(DomainError) as caught:
                await other.start("https://other.example.invalid")
            assert caught.value.code == "origin_mismatch"
        finally:
            await other.close()

    async def test_when_second_process_starts_then_rejected(self, database, migrated_database):
        other = Database(migrated_database)
        try:
            with pytest.raises(DomainError) as caught:
                await other.start("https://tracker.example.invalid")
            assert caught.value.code == "already_running"
        finally:
            await other.close()

    async def test_when_restart_then_interrupted_write_requires_reconciliation(
        self,
        database,
        imported,
    ):
        operation = Commands.build(
            Identity.new(),
            "push",
            imported.campaign_id,
            {},
            72,
            now=Clock.now(),
        )
        async with database.transaction() as store:
            await store.operations.save(operation)
        await database.close()
        await database.start("https://tracker.example.invalid")
        async with database.transaction() as store:
            recovered = await store.operations.require(operation.id)
            active = await store.operations.active(imported.campaign_id)
        assert recovered.status == "unknown"
        assert recovered.error_code == "process_interrupted"
        assert active.id == operation.id
