import pytest

from keitaro_wrapper.application.campaigns.create import CreateCampaignCommand
from keitaro_wrapper.application.operations.manage import ManageOperationCommand
from keitaro_wrapper.application.ports.errors import GatewayError
from keitaro_wrapper.common.identity import Identity

pytestmark = pytest.mark.integration


class TestCreateCampaignUseCase:
    async def test_when_source_parameters_not_preserved_then_no_activation(
        self,
        container,
        monkeypatch,
    ):
        settings = await container.gateway.client.creation_settings()
        settings["campaign"]["parameters"] = {"sub_id_1": {"name": "source"}}

        async def creation_settings():
            return settings

        write = container.gateway.client.write

        async def write_without_parameters(action, data, remote_id=None):
            result = await write(action, data, remote_id)
            if action == "create_campaign":
                container.gateway.client.campaign_data[result["id"]]["parameters"] = {}
            return result

        monkeypatch.setattr(container.gateway.client, "creation_settings", creation_settings)
        monkeypatch.setattr(container.gateway.client, "write", write_without_parameters)
        result = await container.create.execute(
            CreateCampaignCommand(Identity.new(), "parameters", "FR", 1)
        )
        assert result.status == "unknown"
        assert result.error_code == "verification_failed"
        assert all(action != "update_campaign" for action, _, _ in container.gateway.client.writes)

    async def test_when_partial_campaign_changed_then_resume_does_not_write(self, container):
        container.gateway.client.fail_action = "create_stream"
        operation = await container.create.execute(
            CreateCampaignCommand(Identity.new(), "changed", "FR", 1)
        )
        remote_id = operation.context["campaign_remote_id"]
        container.gateway.client.campaign_data[remote_id]["state"] = "active"
        before = len(container.gateway.client.writes)
        got = await container.manage.execute(
            ManageOperationCommand(Identity.new(), operation.id, operation.revision, "resume")
        )
        assert got.status == "unknown"
        assert len(container.gateway.client.writes) == before

    async def test_when_existing_stream_changed_then_resume_does_not_write(
        self,
        container,
        monkeypatch,
    ):
        write = container.gateway.client.write

        async def reject_fallback(action, data, remote_id=None):
            if action == "create_stream" and data["type"] == "default":
                raise GatewayError("integration_error", "Synthetic rejection")
            return await write(action, data, remote_id)

        monkeypatch.setattr(container.gateway.client, "write", reject_fallback)
        operation = await container.create.execute(
            CreateCampaignCommand(Identity.new(), "changed_stream", "FR", 1)
        )
        assert operation.status == "partial"
        container.gateway.client.stream_data[operation.context["geo_remote_id"]][
            "action_payload"
        ] = "https://other.invalid"
        before = len(container.gateway.client.writes)
        monkeypatch.setattr(container.gateway.client, "write", write)
        got = await container.manage.execute(
            ManageOperationCommand(Identity.new(), operation.id, operation.revision, "resume")
        )
        assert got.status == "unknown"
        assert len(container.gateway.client.writes) == before

    async def test_when_valid_then_disabled_until_both_streams_exist(self, container):
        command = CreateCampaignCommand(Identity.new(), "launch", "FR", 1)
        operation = await container.create.execute(command)
        replay = await container.create.execute(command)
        assert operation.status == "succeeded"
        assert replay.id == operation.id
        actions = [call[0] for call in container.gateway.client.writes]
        assert actions == ["create_campaign", "create_stream", "create_stream", "update_campaign"]
        assert container.gateway.client.writes[0][1]["state"] == "disabled"
        assert container.gateway.client.writes[-1][1] == {"state": "active"}
        assert container.gateway.client.writes[1][1]["filters"][0]["payload"] == ["FR"]
        view = await container.get_campaign.execute(operation.campaign_id)
        assert view.name == "test_demo_launch"
        assert view.url.startswith("https://example.invalid/kw")

    async def test_when_stream_creation_fails_then_resume_reuses_campaign(self, container):
        container.gateway.client.fail_action = "create_stream"
        operation = await container.create.execute(
            CreateCampaignCommand(Identity.new(), "partial", "FR", 1)
        )
        assert operation.status == "partial"
        got = await container.manage.execute(
            ManageOperationCommand(Identity.new(), operation.id, operation.revision, "resume")
        )
        assert got.status == "succeeded"
        assert sum(c[0] == "create_campaign" for c in container.gateway.client.writes) == 1

    async def test_when_create_times_out_then_find_existing_without_duplicate(self, container):
        container.gateway.client.timeout_action = "create_campaign"
        operation = await container.create.execute(
            CreateCampaignCommand(Identity.new(), "recover", "FR", 1)
        )
        assert operation.status == "unknown"
        checked = await container.manage.execute(
            ManageOperationCommand(Identity.new(), operation.id, operation.revision, "reconcile")
        )
        assert checked.status == "partial"
        assert len(container.gateway.client.writes) == 1
        done = await container.manage.execute(
            ManageOperationCommand(Identity.new(), checked.id, checked.revision, "resume")
        )
        assert done.status == "succeeded"
        assert sum(c[0] == "create_campaign" for c in container.gateway.client.writes) == 1
