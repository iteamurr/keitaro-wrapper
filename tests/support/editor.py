from keitaro_wrapper.application.streams.edit import EditStreamCommand
from keitaro_wrapper.common.identity import Identity


async def editor(container):
    async with container.database.transaction() as store:
        return await store.streams.require(72)


async def add_fourth(container):
    stream = await editor(container)
    return await container.edit.execute(
        EditStreamCommand(Identity.new(), 72, stream.revision, "add", 4)
    )
