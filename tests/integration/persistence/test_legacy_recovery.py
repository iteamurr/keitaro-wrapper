from datetime import UTC, datetime

import pytest

from keitaro_wrapper.application.campaigns.create import CreateCampaignCommand
from keitaro_wrapper.application.operations.manage import ManageOperationCommand
from keitaro_wrapper.application.streams.push import PushStreamCommand
from keitaro_wrapper.bootstrap.container import Container
from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.domain.common.snapshot import Snapshot
from keitaro_wrapper.infrastructure.keitaro.gateway import KeitaroGateway
from keitaro_wrapper.infrastructure.persistence.models.operations import OperationRow
from tests.support.editor import add_fourth, editor

pytestmark = pytest.mark.integration


async def test_pre_refactor_push_checkpoint_survives_restart(container, imported):
    await add_fourth(container)
    view = await editor(container)
    container.gateway.client.timeout_action = "update_stream"
    operation = await container.push.execute(PushStreamCommand(Identity.new(), 72, view.revision))
    assert operation.status == "unknown"
    async with container.database.factory.begin() as session:
        row = await session.get(OperationRow, operation.id)
        context = dict(row.context)
        context["offers"] = context.pop("publication")["offers"]
        del context["offer_ids"]
        row.context = context
    await container.database.close()
    await container.database.start("https://tracker.example.invalid")
    async with container.database.transaction() as store:
        restored = await store.operations.require(operation.id)
        assert isinstance(restored.snapshot("base"), Snapshot)
        assert isinstance(restored.snapshot("publication"), Snapshot)
    before = len(container.gateway.client.writes)
    result = await container.manage.execute(
        ManageOperationCommand(Identity.new(), restored.id, restored.revision, "reconcile")
    )
    assert result.status == "succeeded"
    assert len(container.gateway.client.writes) == before
    assert not (await editor(container)).dirty


async def test_json_creation_checkpoint_survives_restart_without_duplicate(container):
    container.gateway.client.timeout_action = "create_campaign"
    operation = await container.create.execute(
        CreateCampaignCommand(Identity.new(), "restart", "FR", 1)
    )
    assert operation.status == "unknown"
    # Existing JSONB remains plain JSON, not serialized dataclass implementation details.
    async with container.database.factory() as session:
        row = await session.get(OperationRow, operation.id)
        assert isinstance(row.context["settings"]["campaign"], dict)
        assert row.context["pending_body"]["state"] == "disabled"
        assert "token" not in row.context["settings"]
    await container.database.close()
    await container.database.start("https://tracker.example.invalid")
    checked = await container.manage.execute(
        ManageOperationCommand(Identity.new(), operation.id, operation.revision, "reconcile")
    )
    assert checked.status == "partial"
    result = await container.manage.execute(
        ManageOperationCommand(Identity.new(), checked.id, checked.revision, "resume")
    )
    assert result.status == "succeeded"
    assert sum(action == "create_campaign" for action, _, _ in container.gateway.client.writes) == 1


async def test_application_clock_controls_persisted_operation_times(settings, database, gateway):
    instant = datetime(2020, 1, 2, tzinfo=UTC)

    class FixedClock:
        def now(self):
            return instant

    services = Container(settings, database, KeitaroGateway(gateway), FixedClock())
    try:
        result = await services.create.execute(
            CreateCampaignCommand(Identity.new(), "clock", "FR", 1)
        )
        assert result.status == "succeeded"
        async with database.transaction() as store:
            saved = await store.operations.require(result.id)
            campaign = await store.campaigns.require(result.campaign_id)
        assert saved.created_at == saved.updated_at == instant
        assert campaign.last_fetched_at == instant
    finally:
        await services.client.aclose()
