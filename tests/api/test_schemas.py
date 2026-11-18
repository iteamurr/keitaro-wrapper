from uuid import UUID

import pytest

from keitaro_wrapper.api.v1.campaigns.depends import get_campaign_lister
from keitaro_wrapper.application.campaigns.list import CampaignSummary
from keitaro_wrapper.common.pagination import Page

pytestmark = pytest.mark.api


async def test_openapi_describes_nested_outputs_and_query_parameters(client):
    schema = (await client.get("/openapi.json")).json()
    components = schema["components"]["schemas"]
    result = components["OperationResultOut"]
    assert {"campaign_id", "operation_id", "url", "stream_id"} <= result["properties"].keys()
    assert result.get("additionalProperties") is False
    assert {"campaign_remote_id", "geo_remote_id", "fallback_remote_id"} <= components[
        "RemoteIDsOut"
    ]["properties"].keys()
    assert {"streams", "operations", "last_fetched_at"} <= components["CampaignOut"][
        "properties"
    ].keys()
    assert components["CampaignCreateIn"]["additionalProperties"] is False
    for path in ["/api/v1/campaigns", "/api/v1/offers"]:
        endpoint = schema["paths"][path]["get"]
        assert "requestBody" not in endpoint
        parameters = {parameter["name"]: parameter for parameter in endpoint["parameters"]}
        assert parameters["limit"]["in"] == parameters["offset"]["in"] == "query"
        response_ref = endpoint["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        page = components[response_ref.rsplit("/", 1)[-1]]
        assert set(page["required"]) == {"items", "total", "limit", "offset", "has_more"}
    operation_response = schema["paths"]["/api/v1/campaigns"]["post"]["responses"]
    assert operation_response["201"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/OperationOut"
    )
    assert operation_response["202"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/OperationOut"
    )


async def test_handler_dependencies_can_replace_one_use_case(app, client):
    class CampaignQuery:
        async def execute(self, pagination):
            return Page(
                [CampaignSummary(UUID(int=1), 7, "Injected campaign", "active", 0)],
                total=42,
                limit=pagination.limit,
                offset=pagination.offset,
            )

    app.dependency_overrides[get_campaign_lister] = CampaignQuery
    response = await client.get("/api/v1/campaigns?limit=3&offset=6")
    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": str(UUID(int=1)),
                "keitaro_id": 7,
                "name": "Injected campaign",
                "state": "active",
                "revision": 0,
            }
        ],
        "total": 42,
        "limit": 3,
        "offset": 6,
        "has_more": True,
    }


async def test_invalid_application_output_is_not_exposed(app, client):
    class InvalidQuery:
        async def execute(self, pagination):
            return {"items": [{"private": "must-not-leak"}]}

    app.dependency_overrides[get_campaign_lister] = InvalidQuery
    response = await client.get("/api/v1/campaigns")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
    assert "must-not-leak" not in response.text
