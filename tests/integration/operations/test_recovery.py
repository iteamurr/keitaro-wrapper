import pytest

from keitaro_wrapper.application.campaigns.create import CreateCampaignCommand
from keitaro_wrapper.application.operations.manage import ManageOperationCommand
from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.domain.common.errors import DomainError

pytestmark = pytest.mark.integration


class TestOperationRecovery:
    @pytest.mark.parametrize(
        "action,decision",
        [("invalid_action", None), ("resolve", "invalid_decision")],
    )
    async def test_when_invalid_control_then_parent_is_unchanged(self, container, action, decision):
        container.gateway.client.timeout_action = "create_campaign"
        operation = await container.create.execute(
            CreateCampaignCommand(Identity.new(), "recovery", "FR", 1)
        )
        key = Identity.new()
        with pytest.raises(DomainError) as caught:
            await container.manage.execute(
                ManageOperationCommand(
                    key,
                    operation.id,
                    operation.revision,
                    action,
                    decision,
                    True,
                    "Operator check",
                )
            )
        assert caught.value.code == "invalid_command"
        async with container.database.transaction() as store:
            current = await store.operations.require(operation.id)
            assert current.status == operation.status
            assert current.revision == operation.revision
            assert await store.operations.get(key) is None
