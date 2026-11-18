from dataclasses import asdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from keitaro_wrapper.application.ports.repositories.streams import IStreams
from keitaro_wrapper.common.types import Document
from keitaro_wrapper.domain.streams.editor import OfferAllocation, StreamEditor
from keitaro_wrapper.infrastructure.common.snapshots import freeze, thaw
from keitaro_wrapper.infrastructure.persistence.models.streams import StreamRow


class ORMStreams(IStreams):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, entity: StreamEditor) -> None:
        data = {
            "id": entity.id,
            "campaign_id": entity.campaign_id,
            "name": entity.name,
            "position": entity.position,
            "revision": entity.revision,
            "available": entity.available,
            "read_only_reason": entity.read_only_reason,
            "remote_baseline": thaw(entity.remote_baseline),
            "editor_baseline": self._pack(entity.baseline),
            "editor_draft": self._pack(entity.draft),
        }
        await self.session.merge(StreamRow(**data))
        await self.session.flush()

    async def get(self, key: int) -> StreamEditor | None:
        row = await self.session.get(StreamRow, key, populate_existing=True)
        return self._stream(row) if row else None

    async def list(self, campaign_id: UUID) -> list[StreamEditor]:
        rows = (
            await self.session.scalars(
                select(StreamRow)
                .where(StreamRow.campaign_id == campaign_id)
                .order_by(StreamRow.position, StreamRow.id)
            )
        ).all()
        return [self._stream(row) for row in rows]

    @classmethod
    def _pack(cls, offers: dict[int, OfferAllocation]) -> Document:
        return {
            "version": 1,
            "offers": {str(key): asdict(offer) for key, offer in offers.items()},
        }

    @classmethod
    def _unpack(cls, data: Document) -> dict[int, OfferAllocation]:
        if data.get("version") != 1:
            raise ValueError("Unsupported editor snapshot version")
        return {int(key): OfferAllocation(**value) for key, value in data["offers"].items()}

    @classmethod
    def _stream(cls, row: StreamRow) -> StreamEditor:
        return StreamEditor(
            id=row.id,
            campaign_id=row.campaign_id,
            name=row.name,
            position=row.position,
            revision=row.revision,
            available=row.available,
            read_only_reason=row.read_only_reason,
            remote_baseline=freeze(row.remote_baseline),
            baseline=cls._unpack(row.editor_baseline),
            draft=cls._unpack(row.editor_draft),
        )
