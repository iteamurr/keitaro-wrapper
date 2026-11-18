from copy import deepcopy

import pytest

from keitaro_wrapper.application.operations.manage import ManageOperationCommand
from keitaro_wrapper.application.streams.edit import EditStreamCommand
from keitaro_wrapper.application.streams.push import PushStreamCommand
from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.domain.common.errors import DomainError
from tests.support.editor import add_fourth, editor

pytestmark = pytest.mark.integration


class TestPushStreamUseCase:
    async def test_when_deleted_remotely_then_conflict_without_write(self, container, imported):
        await add_fourth(container)
        del container.gateway.client.stream_data[72]
        operation = await container.push.execute(
            PushStreamCommand(Identity.new(), 72, (await editor(container)).revision)
        )
        assert operation.status == "conflict"
        assert (await editor(container)).dirty
        assert container.gateway.client.writes == []

    async def test_when_verification_read_fails_then_reserves_until_reconciled(
        self,
        container,
        imported,
        monkeypatch,
    ):
        await add_fourth(container)
        write = container.gateway.client.write

        async def write_then_read_failure(*args, **kwargs):
            result = await write(*args, **kwargs)
            container.gateway.client.fail_read = True
            return result

        monkeypatch.setattr(container.gateway.client, "write", write_then_read_failure)
        operation = await container.push.execute(
            PushStreamCommand(Identity.new(), 72, (await editor(container)).revision)
        )
        assert operation.status == "unknown"
        assert (await container.get_campaign.execute(imported.campaign_id)).busy
        container.gateway.client.fail_read = False
        got = await container.manage.execute(
            ManageOperationCommand(Identity.new(), operation.id, operation.revision, "reconcile")
        )
        assert got.status == "succeeded"
        assert len(container.gateway.client.writes) == 1

    async def test_when_manual_confirmation_missing_then_preserves_reservation(
        self,
        container,
        imported,
    ):
        await add_fourth(container)
        container.gateway.client.timeout_action = "update_stream"
        operation = await container.push.execute(
            PushStreamCommand(Identity.new(), 72, (await editor(container)).revision)
        )
        with pytest.raises(DomainError) as caught:
            await container.manage.execute(
                ManageOperationCommand(
                    Identity.new(),
                    operation.id,
                    operation.revision,
                    "resolve",
                    "adopt_current",
                )
            )
        assert caught.value.code == "confirmation_required"
        assert (await container.get_campaign.execute(imported.campaign_id)).busy
        result = await container.manage.execute(
            ManageOperationCommand(
                Identity.new(),
                operation.id,
                operation.revision,
                "resolve",
                "adopt_current",
                True,
                "Synthetic operator check",
            )
        )
        assert result.status == "succeeded"
        assert not (await editor(container)).dirty
        assert len(container.gateway.client.writes) == 1

    async def test_when_publish_then_updates_only_offers_and_confirms(self, container, imported):
        await add_fourth(container)
        stream = await editor(container)
        before = deepcopy(container.gateway.client.stream_data[72])
        operation = await container.push.execute(
            PushStreamCommand(Identity.new(), 72, stream.revision)
        )
        assert operation.status == "succeeded"
        assert container.gateway.client.writes == [
            (
                "update_stream",
                {"offers": [{"offer_id": i, "share": 25, "state": "active"} for i in range(1, 5)]},
                72,
            )
        ]
        assert container.gateway.client.stream_data[72]["filters"] == before["filters"]
        assert not (await editor(container)).dirty

    async def test_when_external_conflict_then_never_writes(self, container, imported):
        await add_fourth(container)
        container.gateway.client.stream_data[72]["name"] = "External change"
        operation = await container.push.execute(
            PushStreamCommand(Identity.new(), 72, (await editor(container)).revision)
        )
        assert operation.status == "conflict"
        assert (await editor(container)).dirty
        assert container.gateway.client.writes == []

    async def test_when_timeout_after_apply_then_reconcile_without_second_write(
        self,
        container,
        imported,
    ):
        await add_fourth(container)
        container.gateway.client.timeout_action = "update_stream"
        operation = await container.push.execute(
            PushStreamCommand(Identity.new(), 72, (await editor(container)).revision)
        )
        assert operation.status == "unknown"
        with pytest.raises(DomainError, match="занята"):
            await container.edit.execute(
                EditStreamCommand(Identity.new(), 72, (await editor(container)).revision, "cancel")
            )
        got = await container.manage.execute(
            ManageOperationCommand(Identity.new(), operation.id, operation.revision, "reconcile")
        )
        assert got.status == "succeeded"
        assert len(container.gateway.client.writes) == 1
        assert not (await editor(container)).dirty

    async def test_when_still_old_after_uncertainty_then_no_automatic_retry(
        self,
        container,
        imported,
    ):
        await add_fourth(container)
        old_remote = deepcopy(container.gateway.client.stream_data[72])
        container.gateway.client.timeout_action = "update_stream"
        operation = await container.push.execute(
            PushStreamCommand(Identity.new(), 72, (await editor(container)).revision)
        )
        container.gateway.client.stream_data[72] = old_remote
        got = await container.manage.execute(
            ManageOperationCommand(Identity.new(), operation.id, operation.revision, "reconcile")
        )
        assert got.status in ("unknown", "manual_review")
        assert len(container.gateway.client.writes) == 1
        assert (await container.get_campaign.execute(imported.campaign_id)).busy

    async def test_when_removed_then_archive_survives_publish(self, container, imported):
        stream = await editor(container)
        await container.edit.execute(
            EditStreamCommand(Identity.new(), 72, stream.revision, "remove", 3)
        )
        operation = await container.push.execute(
            PushStreamCommand(Identity.new(), 72, (await editor(container)).revision)
        )
        assert operation.status == "succeeded"
        assert not (await editor(container)).draft[3].active
        assert all(o["offer_id"] != 3 for o in container.gateway.client.stream_data[72]["offers"])
