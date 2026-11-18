import json

import httpx
import pytest

from keitaro_wrapper.application.ports.errors import GatewayError
from keitaro_wrapper.infrastructure.keitaro.client import KeitaroClient


@pytest.fixture
async def http_gateway(settings):
    async with httpx.AsyncClient() as client:
        yield KeitaroClient(client, settings)


class TestWrite:
    @pytest.mark.parametrize("remote_id", [0, -1, True, 99, "72", None])
    async def test_when_update_returns_invalid_identity_then_result_is_uncertain(
        self,
        http_gateway,
        httpx_mock,
        remote_id,
    ):
        httpx_mock.add_response(json={"id": remote_id})
        with pytest.raises(GatewayError) as caught:
            await http_gateway.write("update_stream", {"offers": []}, 72)
        assert caught.value.code == "invalid_response"
        assert caught.value.uncertain
        assert len(httpx_mock.get_requests()) == 1

    async def test_when_update_then_sends_only_requested_fields(self, http_gateway, httpx_mock):
        httpx_mock.add_response(
            method="PUT",
            url="https://tracker.example.invalid/admin_api/v1/streams/72",
            json={"id": 72},
        )
        body = {"offers": [{"offer_id": 3, "share": 100, "state": "active"}]}
        await http_gateway.write("update_stream", body, 72)
        request = httpx_mock.get_request()
        assert request.headers["Api-Key"] == "synthetic-key"
        assert json.loads(request.content) == body
        assert len(httpx_mock.get_requests()) == 1

    async def test_when_timeout_then_uncertain_and_never_retried(self, http_gateway, httpx_mock):
        httpx_mock.add_exception(httpx.ReadTimeout("synthetic"))
        with pytest.raises(GatewayError) as caught:
            await http_gateway.write("create_campaign", {"name": "Test", "alias": "test"})
        assert caught.value.uncertain
        assert len(httpx_mock.get_requests()) == 1

    async def test_when_bad_json_after_write_then_uncertain(self, http_gateway, httpx_mock):
        httpx_mock.add_response(text="not JSON")
        with pytest.raises(GatewayError) as caught:
            await http_gateway.write("update_stream", {"offers": []}, 72)
        assert caught.value.uncertain


class TestReads:
    async def test_when_boolean_id_then_rejects_object(self, http_gateway, httpx_mock):
        httpx_mock.add_response(json={"id": True})
        with pytest.raises(GatewayError) as caught:
            await http_gateway.campaign(1)
        assert caught.value.code == "invalid_response"

    async def test_when_stream_has_malformed_campaign_id_then_safe_error(
        self,
        http_gateway,
        httpx_mock,
    ):
        httpx_mock.add_response(json=[{"id": 72, "campaign_id": None}])
        with pytest.raises(GatewayError) as caught:
            await http_gateway.streams(7)
        assert caught.value.code == "invalid_response"

    @pytest.mark.parametrize("status", [401, 402, 403, 404, 406, 429])
    async def test_when_upstream_error_then_safe_message(self, http_gateway, httpx_mock, status):
        httpx_mock.add_response(status_code=status, text="synthetic-key private detail")
        with pytest.raises(GatewayError) as caught:
            await http_gateway.campaign(7)
        assert "synthetic-key" not in str(caught.value)
        assert not caught.value.uncertain

    async def test_when_catalog_then_no_invented_search_parameters(self, http_gateway, httpx_mock):
        httpx_mock.add_response(
            url="https://tracker.example.invalid/admin_api/v1/offers",
            json=[{"id": 1, "name": "One", "state": "active", "action_payload": "private"}],
        )
        assert await http_gateway.offers() == [{"id": 1, "name": "One", "state": "active"}]


class TestCreationSettings:
    async def test_when_no_verified_profile_then_no_network_request(self, http_gateway, httpx_mock):
        with pytest.raises(GatewayError, match="проверенный профиль"):
            await http_gateway.creation_settings()
        assert httpx_mock.get_requests() == []


class TestInspect:
    def test_empty_landings_payload_normalization_does_not_create_a_conflict(self, gateway):
        original = {**gateway.stream_data[72], "action_payload": None}
        normalized = {**original, "action_payload": ""}
        assert gateway.signature(original) == gateway.signature(normalized)

    @pytest.mark.parametrize("schema", ["landings", "redirect"])
    def test_nonempty_action_payload_change_is_still_a_conflict(self, gateway, schema):
        original = {**gateway.stream_data[72], "schema": schema, "action_payload": None}
        changed = {**original, "action_payload": "https://example.invalid/changed"}
        assert gateway.signature(original) != gateway.signature(changed)

    def test_redirect_payload_is_not_normalized(self, gateway):
        original = {**gateway.stream_data[71], "action_payload": None}
        changed = {**original, "action_payload": ""}
        assert gateway.signature(original) != gateway.signature(changed)

    def test_when_disabled_then_read_only_not_archived(self, http_gateway):
        offers, reason = http_gateway.inspect(
            {
                "id": 1,
                "schema": "landings",
                "state": "active",
                "offers": [{"offer_id": 2, "share": 100, "state": "disabled"}],
            },
            {2: "Two"},
        )
        assert reason
        assert offers[0].external_state == "disabled"

    def test_when_only_timestamps_change_then_same_fingerprint(self, gateway):
        original = gateway.stream_data[72]
        changed = {**original, "updated_at": "different timestamp"}
        assert gateway.signature(original) == gateway.signature(changed)
