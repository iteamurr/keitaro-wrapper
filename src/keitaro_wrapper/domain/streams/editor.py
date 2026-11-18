from __future__ import annotations

from dataclasses import dataclass, field, replace
from uuid import UUID

from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.domain.common.snapshot import Snapshot


@dataclass(frozen=True)
class OfferAllocation:
    offer_id: int
    name: str
    weight: int
    active: bool = True
    pinned: bool = False
    external_state: str = "active"


class WeightDistribution:
    @classmethod
    def apply(cls, offers: dict[int, OfferAllocation]) -> dict[int, OfferAllocation]:
        active = [o for o in offers.values() if o.active]
        if not active:
            raise DomainError("last_offer", "В потоке должен остаться хотя бы один оффер.")
        pinned = [o for o in active if o.pinned]
        free = sorted((o for o in active if not o.pinned), key=lambda o: o.offer_id)
        if any(type(o.weight) is not int or not 1 <= o.weight <= 100 for o in pinned):
            raise DomainError("invalid_weights", "Закреплённый вес должен быть от 1 до 100%.")
        remainder = 100 - sum(o.weight for o in pinned)
        if remainder < len(free) or (not free and remainder != 0):
            raise DomainError(
                "invalid_weights",
                "Невозможно распределить 100%. Измените закрепления; каждому офферу нужен хотя бы 1%.",
            )
        result = {
            key: replace(o, weight=0, pinned=False) if not o.active else o
            for key, o in offers.items()
        }
        if free:
            share, extra = divmod(remainder, len(free))
            for index, offer in enumerate(free):
                result[offer.offer_id] = replace(offer, weight=share + (index < extra))
        return result


@dataclass
class StreamEditor:
    id: int
    campaign_id: UUID
    name: str
    position: int
    remote_baseline: Snapshot
    baseline: dict[int, OfferAllocation] = field(default_factory=dict)
    draft: dict[int, OfferAllocation] = field(default_factory=dict)
    revision: int = 0
    available: bool = True
    read_only_reason: str | None = None

    @property
    def dirty(self) -> bool:
        return self.baseline != self.draft

    @property
    def total(self) -> int:
        return sum(o.weight for o in self.draft.values() if o.active)

    def assert_editable(self) -> None:
        if not self.available or self.read_only_reason:
            raise DomainError("read_only", self.read_only_reason or "Поток больше недоступен.")

    def add(self, offer_id: int, name: str) -> None:
        self.assert_editable()
        current = self.draft.get(offer_id)
        if current and current.active:
            raise DomainError("duplicate_offer", "Оффер уже активен в этом потоке.")
        desired = {**self.draft, offer_id: OfferAllocation(offer_id, name, 0)}
        self._apply(WeightDistribution.apply(desired))

    def restore(self, offer_id: int, name: str) -> None:
        if offer_id not in self.draft:
            raise DomainError("not_found", "Архивная привязка не найдена.")
        self.add(offer_id, name)

    def remove(self, offer_id: int) -> None:
        self.assert_editable()
        offer = self._active(offer_id)
        desired = dict(self.draft)
        if offer_id not in self.baseline:
            del desired[offer_id]
        else:
            desired[offer_id] = replace(offer, active=False, weight=0, pinned=False)
        self._apply(WeightDistribution.apply(desired))

    def pin(self, offer_id: int, pinned: bool, weight: int | None = None) -> None:
        self.assert_editable()
        offer = self._active(offer_id)
        if pinned and weight is None:
            raise DomainError("invalid_weights", "Укажите закреплённый вес.")
        desired = {
            **self.draft,
            offer_id: replace(
                offer,
                pinned=pinned,
                weight=weight if pinned and weight is not None else offer.weight,
            ),
        }
        self._apply(WeightDistribution.apply(desired))

    def cancel(self) -> None:
        self._apply(dict(self.baseline))

    def _active(self, offer_id: int) -> OfferAllocation:
        offer = self.draft.get(offer_id)
        if not offer or not offer.active:
            raise DomainError("offer_not_active", "Оффер не активен в этом потоке.")
        return offer

    def _apply(self, offers: dict[int, OfferAllocation]) -> None:
        if self.draft != offers:
            self.draft = offers
            self.revision += 1

    def mark_missing(self) -> None:
        self.available = False
        self.read_only_reason = "Поток удалён или недоступен в Keitaro."
        self.revision += 1

    def accept(
        self,
        snapshot: Snapshot,
        offers: list[OfferAllocation],
        reason: str | None,
        *,
        name: str,
        position: int,
    ) -> None:
        incoming = {o.offer_id: o for o in offers}
        baseline = {
            key: replace(old, active=False, weight=0, pinned=False, external_state="active")
            for key, old in self.baseline.items()
            if key not in incoming
        }
        for key, offer in incoming.items():
            old = self.draft.get(key)
            pinned = bool(
                old and old.active and old.pinned and 1 <= offer.weight <= 100 and offer.active
            )
            baseline[key] = replace(offer, pinned=pinned)
        self.remote_baseline = snapshot
        self.baseline = baseline
        self.draft = dict(baseline)
        self.name = name
        self.position = position
        self.read_only_reason = reason
        self.available = True
        self.revision += 1

    def publication(self) -> tuple[OfferAllocation, ...]:
        self.assert_editable()
        if not self.dirty:
            raise DomainError("no_changes", "В потоке нет изменений для публикации.")
        target = tuple(
            offer
            for offer in sorted(self.draft.values(), key=lambda offer: offer.offer_id)
            if offer.active
        )
        if (
            not target
            or any(type(o.weight) is not int or not 1 <= o.weight <= 100 for o in target)
            or sum(o.weight for o in target) != 100
        ):
            raise DomainError("invalid_weights", "Сумма активных весов должна быть равна 100%.")
        return target
