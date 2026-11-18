import pytest

from keitaro_wrapper.application.ports.errors import GatewayError
from keitaro_wrapper.application.ports.remote import CreationPlan, PreparedWrite, RemoteOffer
from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.domain.streams.editor import OfferAllocation
from keitaro_wrapper.infrastructure.common.snapshots import freeze, thaw
from keitaro_wrapper.infrastructure.keitaro.gateway import KeitaroGateway


async def test_gateway_exposes_typed_values_and_immutable_snapshots(gateway):
    port = KeitaroGateway(gateway)
    campaign = await port.campaign(7)
    stream = await port.stream(72)
    offers = await port.offers()
    assert campaign.id == 7
    assert offers[0] == RemoteOffer(1, "Autumn collection · France", True, "active")
    assert [(offer.offer_id, offer.weight) for offer in stream.allocations] == [
        (1, 34),
        (2, 33),
        (3, 33),
    ]
    gateway.stream_data[72]["offers"][0]["share"] = 1
    assert stream.allocations[0].weight == 34
    assert thaw(stream.snapshot)["offers"][0]["share"] == 34


async def test_publication_preserves_unrelated_fields_and_compares_semantics(gateway):
    port = KeitaroGateway(gateway)
    stream = await port.stream(72)
    request = port.prepare_publish(72, (OfferAllocation(1, "One", 100),))
    assert thaw(request.body) == {"offers": [{"offer_id": 1, "share": 100, "state": "active"}]}
    assert not port.matches_publish(stream.snapshot, stream.snapshot, request)
    result = await port.write(request)
    assert result.id == 72
    remote = await port.stream(72)
    assert port.matches_publish(remote.snapshot, stream.snapshot, request)
    gateway.stream_data[72]["name"] = "Changed externally"
    changed = await port.stream(72)
    assert not port.matches_publish(changed.snapshot, stream.snapshot, request)


async def test_recovery_refuses_duplicate_and_partial_identity_matches(gateway):
    port = KeitaroGateway(gateway)
    settings = await port.creation_settings()
    plan = CreationPlan(Identity.new(), "test_demo_new", "new", "FR", 1, settings.snapshot)
    request = port.prepare_creation(plan, "campaign")
    created = await port.write(request)
    assert (await port.recover(request, None)).id == created.id
    gateway.campaign_data[created.id + 1] = {
        **gateway.campaign_data[created.id],
        "id": created.id + 1,
    }
    match = await port.recover(request, None)
    assert match.id is None
    assert match.possible_result
    del gateway.campaign_data[created.id + 1]
    gateway.campaign_data[created.id]["notes"] = "changed"
    match = await port.recover(request, None)
    assert match.id is None
    assert match.possible_result


async def test_unknown_recovery_action_fails_closed(gateway):
    with pytest.raises(GatewayError) as caught:
        await KeitaroGateway(gateway).recover(PreparedWrite("typo", freeze({})), None)
    assert caught.value.code == "invalid_checkpoint"
