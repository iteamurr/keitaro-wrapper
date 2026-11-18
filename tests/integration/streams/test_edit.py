import pytest

from keitaro_wrapper.application.streams.edit import EditStreamCommand
from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.domain.common.errors import DomainError
from tests.support.editor import add_fourth, editor

pytestmark = pytest.mark.integration


class TestEditStreamUseCase:
    async def test_when_same_command_replayed_then_one_edit(self, container, imported):
        before = await editor(container)
        command = EditStreamCommand(Identity.new(), 72, before.revision, "add", 4)
        await container.edit.execute(command)
        await container.edit.execute(command)
        got = await editor(container)
        assert got.revision == before.revision + 1
        assert got.total == 100
        assert len(got.draft) == len(before.draft) + 1
        assert container.gateway.client.writes == []

    async def test_when_stale_then_no_edit(self, container, imported):
        await add_fourth(container)
        with pytest.raises(DomainError, match="изменились"):
            await container.edit.execute(EditStreamCommand(Identity.new(), 72, 0, "remove", 1))
        assert (await editor(container)).draft[1].active

    async def test_when_cancel_then_restores_entire_snapshot(self, container, imported):
        before = await editor(container)
        await add_fourth(container)
        changed = await editor(container)
        await container.edit.execute(
            EditStreamCommand(Identity.new(), 72, changed.revision, "cancel")
        )
        got = await editor(container)
        assert got.draft == before.draft
        assert not got.dirty
