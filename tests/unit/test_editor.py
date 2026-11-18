from dataclasses import replace

import pytest

from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.domain.common.snapshot import Snapshot
from keitaro_wrapper.domain.streams.editor import OfferAllocation, StreamEditor, WeightDistribution


@pytest.fixture
def editor():
    offers = {
        i: OfferAllocation(i, f"Offer {i}", weight) for i, weight in [(1, 34), (2, 33), (3, 33)]
    }
    return StreamEditor(72, Identity.new(), "Offers", 2, Snapshot("opaque"), offers, dict(offers))


class TestDistribution:
    @pytest.mark.parametrize(
        "ids,want",
        [([3, 1, 2], {1: 34, 2: 33, 3: 33}), ([1, 2, 3, 4], {1: 25, 2: 25, 3: 25, 4: 25})],
    )
    def test_when_unpinned_then_exact_deterministic_total(self, ids, want):
        got = WeightDistribution.apply({i: OfferAllocation(i, "Offer", 0) for i in ids})
        assert {i: o.weight for i, o in got.items()} == want

    def test_when_pinned_then_preserves_pin_and_splits_remainder(self):
        got = WeightDistribution.apply(
            {
                1: OfferAllocation(1, "One", 25, pinned=True),
                2: OfferAllocation(2, "Two", 0),
                3: OfferAllocation(3, "Three", 0),
            }
        )
        assert [got[i].weight for i in (1, 2, 3)] == [25, 38, 37]

    @pytest.mark.parametrize(
        "offers",
        [
            {1: OfferAllocation(1, "One", 25, pinned=True)},
            {1: OfferAllocation(1, "One", 100, pinned=True), 2: OfferAllocation(2, "Two", 0)},
            {1: OfferAllocation(1, "One", 101, pinned=True)},
        ],
    )
    def test_when_impossible_then_rejected(self, offers):
        with pytest.raises(DomainError, match="Закреплённый|Невозможно"):
            WeightDistribution.apply(offers)


class TestAdd:
    def test_when_added_then_draft_changes_only(self, editor):
        editor.add(4, "Four")
        assert editor.dirty
        assert [o.weight for o in editor.draft.values()] == [25, 25, 25, 25]
        assert 4 not in editor.baseline


class TestRemove:
    def test_when_last_then_leaves_state_untouched(self):
        offer = OfferAllocation(1, "Only", 100)
        editor = StreamEditor(
            72,
            Identity.new(),
            "Offers",
            2,
            Snapshot("opaque"),
            {1: offer},
            {1: offer},
        )
        with pytest.raises(DomainError, match="хотя бы один"):
            editor.remove(1)
        assert editor.draft == editor.baseline
        assert editor.revision == 0

    def test_when_new_removed_then_no_archive_remains(self, editor):
        editor.add(4, "Four")
        editor.remove(4)
        assert 4 not in editor.draft
        assert not editor.dirty


class TestPin:
    def test_when_impossible_then_draft_is_unchanged(self, editor):
        before = dict(editor.draft)
        with pytest.raises(DomainError):
            editor.pin(1, True, 100)
        assert editor.draft == before


class TestCancel:
    def test_when_removed_pinned_then_restores_weight_and_pin(self, editor):
        editor.baseline[1] = replace(editor.baseline[1], pinned=True)
        editor.draft = dict(editor.baseline)
        editor.remove(1)
        editor.cancel()
        assert editor.draft[1].pinned
        assert editor.draft[1].weight == 34
        assert not editor.dirty


class TestAccept:
    def test_when_external_removal_then_archive_survives_later_fetch(self, editor):
        incoming = [OfferAllocation(1, "One", 70), OfferAllocation(2, "Two", 30)]
        editor.accept(Snapshot("opaque"), incoming, None, name="Offers", position=2)
        editor.accept(Snapshot("opaque"), incoming, None, name="Offers", position=2)
        assert not editor.draft[3].active
        assert editor.draft[3].weight == 0
        assert editor.draft[1].weight == 70
        assert not editor.dirty

    def test_when_archive_returns_then_single_active_binding(self, editor):
        editor.accept(
            Snapshot("opaque"),
            [OfferAllocation(1, "One", 100)],
            None,
            name="Offers",
            position=2,
        )
        editor.accept(
            Snapshot("opaque"),
            [OfferAllocation(1, "One", 50), OfferAllocation(2, "Two", 50)],
            None,
            name="Offers",
            position=2,
        )
        assert editor.draft[2].active
        assert len([o for o in editor.draft.values() if o.offer_id == 2]) == 1
