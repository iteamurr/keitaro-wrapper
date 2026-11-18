import pytest

from keitaro_wrapper.application.campaigns.fetch import FetchCampaignCommand
from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.domain.campaigns.entity import Campaign
from keitaro_wrapper.domain.common.errors import DomainError
from tests.support.editor import add_fourth, editor

pytestmark = pytest.mark.integration


class TestFetchCampaignUseCase:
    async def test_when_campaign_has_no_remote_id_then_fetch_does_not_reserve(self, container):
        campaign = Campaign(Identity.new(), "Uncreated campaign", state="creating")
        async with container.database.transaction() as store:
            await store.campaigns.save(campaign)

        with pytest.raises(DomainError):
            await container.fetch.execute(
                FetchCampaignCommand(Identity.new(), campaign.id, campaign.revision)
            )

        async with container.database.transaction() as store:
            assert await store.operations.active(campaign.id) is None

    async def test_when_dirty_then_fetch_is_blocked(self, container, imported):
        await add_fourth(container)
        view = await container.get_campaign.execute(imported.campaign_id)
        with pytest.raises(DomainError, match="Сначала"):
            await container.fetch.execute(
                FetchCampaignCommand(Identity.new(), imported.campaign_id, view.revision)
            )
        assert (await editor(container)).dirty

    async def test_when_external_removal_then_archives_without_write(self, container, imported):
        container.gateway.client.stream_data[72]["offers"] = [
            {"offer_id": 1, "share": 100, "state": "active"}
        ]
        view = await container.get_campaign.execute(imported.campaign_id)
        operation = await container.fetch.execute(
            FetchCampaignCommand(Identity.new(), imported.campaign_id, view.revision)
        )
        assert operation.status == "succeeded"
        got = await editor(container)
        assert not got.draft[2].active
        assert got.draft[2].weight == 0
        assert not got.dirty
        assert container.gateway.client.writes == []

    async def test_when_stream_disappears_then_preserves_history_read_only(
        self,
        container,
        imported,
    ):
        del container.gateway.client.stream_data[72]
        view = await container.get_campaign.execute(imported.campaign_id)
        await container.fetch.execute(
            FetchCampaignCommand(Identity.new(), imported.campaign_id, view.revision)
        )
        got = await editor(container)
        assert not got.available
        assert got.draft[1].offer_id == 1
