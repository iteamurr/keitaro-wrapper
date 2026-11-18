import pytest

from keitaro_wrapper.application.campaigns.create import CreateCampaignCommand
from keitaro_wrapper.application.ports.errors import GatewayError
from keitaro_wrapper.common.identity import Identity

pytestmark = pytest.mark.api


class TestHTTPContracts:
    async def test_when_preflight_rejected_then_reports_command_not_started(
        self,
        client,
        container,
        monkeypatch,
    ):
        async def invalid_settings():
            raise GatewayError("invalid_configuration", "Synthetic preflight rejection")

        monkeypatch.setattr(container.gateway.client, "creation_settings", invalid_settings)
        key = str(Identity.new())
        response = await client.post(
            "/api/v1/campaigns",
            json={"name": "Summer", "country_code": "FR", "offer_id": 1},
            headers={"Idempotency-Key": key},
        )
        assert response.status_code == 503
        assert response.json()["error"]["details"]["command_state"] == "not_started"
        assert (await client.get(f"/api/v1/operations/{key}")).status_code == 404
        assert container.gateway.client.writes == []

    async def test_when_control_receipt_read_then_links_to_parent(self, client, container):
        container.gateway.client.timeout_action = "create_campaign"
        operation = await container.create.execute(
            CreateCampaignCommand(Identity.new(), "recover", "FR", 1)
        )
        key = str(Identity.new())
        response = await client.post(
            f"/api/v1/operations/{operation.id}/reconcile",
            json={"expected_operation_revision": operation.revision},
            headers={"Idempotency-Key": key},
        )
        assert response.status_code == 202
        receipt = (await client.get(f"/api/v1/operations/{key}")).json()
        assert receipt["parent_operation_id"] == str(operation.id)
        assert not receipt["can_resume"]
        parent = (await client.get(f"/api/v1/operations/{receipt['parent_operation_id']}")).json()
        assert parent["status"] == "partial"

    async def test_when_confirmation_is_string_then_rejected(self, client):
        response = await client.post(
            f"/api/v1/operations/{Identity.new()}/resolve",
            json={"expected_operation_revision": 0, "confirmation": "true"},
            headers={"Idempotency-Key": str(Identity.new())},
        )
        assert response.status_code == 422

    async def test_when_non_ascii_csrf_then_rejected_without_server_error(self, client):
        response = await client.post(
            "/api/v1/campaigns/import",
            json={"keitaro_campaign_id": 7},
            headers=[
                (b"X-CSRF-Token", b"\xff"),
                (b"Idempotency-Key", str(Identity.new()).encode()),
            ],
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "csrf_failed"

    async def test_when_import_edit_publish_then_returns_editor_and_receipt(
        self,
        client,
        container,
    ):
        response = await client.post(
            "/api/v1/campaigns/import",
            json={"keitaro_campaign_id": 7},
            headers={"Idempotency-Key": str(Identity.new())},
        )
        assert response.status_code == 201
        campaign_id = response.json()["campaign_id"]
        view = (await client.get(f"/api/v1/campaigns/{campaign_id}")).json()
        stream = next(s for s in view["streams"] if s["id"] == 72)
        key = str(Identity.new())
        payload = {"expected_revision": stream["revision"], "offer_id": 4}
        added = await client.post(
            "/api/v1/streams/72/offers",
            json=payload,
            headers={"Idempotency-Key": key},
        )
        replay = await client.post(
            "/api/v1/streams/72/offers",
            json=payload,
            headers={"Idempotency-Key": key},
        )
        assert added.status_code == replay.status_code == 200
        assert added.json()["id"] == replay.json()["id"]
        view = (await client.get(f"/api/v1/campaigns/{campaign_id}")).json()
        stream = next(s for s in view["streams"] if s["id"] == 72)
        pushed = await client.post(
            "/api/v1/streams/72/push",
            json={"expected_revision": stream["revision"]},
            headers={"Idempotency-Key": str(Identity.new())},
        )
        assert pushed.json()["status"] == "succeeded"
        assert len(container.gateway.client.writes) == 1

    async def test_when_csrf_missing_then_rejected(self, client):
        response = await client.post(
            "/api/v1/campaigns/import",
            json={"keitaro_campaign_id": 7},
            headers={"X-CSRF-Token": "", "Idempotency-Key": str(Identity.new())},
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "csrf_failed"

    async def test_when_cross_origin_then_rejected_even_with_token(self, client):
        response = await client.post(
            "/api/v1/campaigns/import",
            json={"keitaro_campaign_id": 7},
            headers={"Origin": "https://untrusted.invalid", "Idempotency-Key": str(Identity.new())},
        )
        assert response.status_code == 403

    @pytest.mark.parametrize(
        "payload",
        [{"keitaro_campaign_id": -1}, {"keitaro_campaign_id": "7"}, {"keitaro_campaign_id": True}],
    )
    async def test_when_invalid_input_then_safe_validation_error(self, client, payload):
        response = await client.post(
            "/api/v1/campaigns/import",
            json=payload,
            headers={"Idempotency-Key": str(Identity.new())},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"

    async def test_when_create_then_country_normalized_and_url_returned(self, client):
        response = await client.post(
            "/api/v1/campaigns",
            json={"name": "Summer", "country_code": "fr", "offer_id": 1},
            headers={"Idempotency-Key": str(Identity.new())},
        )
        assert response.status_code == 201
        assert response.json()["result"]["url"].startswith("https://example.invalid/")

    async def test_when_unknown_write_then_accepted_operation_and_readable_status(
        self,
        client,
        imported,
        container,
    ):
        view = (await client.get(f"/api/v1/campaigns/{imported.campaign_id}")).json()
        stream = next(s for s in view["streams"] if s["id"] == 72)
        await client.post(
            "/api/v1/streams/72/offers",
            json={"offer_id": 4, "expected_revision": stream["revision"]},
            headers={"Idempotency-Key": str(Identity.new())},
        )
        container.gateway.client.timeout_action = "update_stream"
        key = str(Identity.new())
        response = await client.post(
            "/api/v1/streams/72/push",
            json={"expected_revision": stream["revision"] + 1},
            headers={"Idempotency-Key": key},
        )
        assert response.status_code == 202
        got = (await client.get(f"/api/v1/operations/{key}")).json()
        assert got["status"] == "unknown"
        assert got["can_reconcile"]

    async def test_when_get_page_then_csp_static_resources_and_no_secret(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        assert "script-src 'self'" in response.headers["Content-Security-Policy"]
        assert "synthetic-key" not in response.text
        assert (await client.get("/static/app.js")).status_code == 200
        assert (await client.get("/health/ready")).json() == {"status": "ok"}
