import pytest

from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.domain.campaigns.entity import Campaign

pytestmark = pytest.mark.api


async def test_campaigns_report_total_and_empty_page(client, database):
    async with database.transaction() as store:
        for name in ["Alpha", "Beta", "Gamma"]:
            await store.campaigns.save(Campaign(Identity.new(), name))
    response = await client.get("/api/v1/campaigns?limit=1&offset=1")
    assert response.status_code == 200
    page = response.json()
    assert [item["name"] for item in page["items"]] == ["Beta"]
    assert (page["total"], page["limit"], page["offset"], page["has_more"]) == (3, 1, 1, True)
    page = (await client.get("/api/v1/campaigns?limit=2&offset=3")).json()
    assert page == {"items": [], "total": 3, "limit": 2, "offset": 3, "has_more": False}


async def test_offer_search_pages_filtered_results(client):
    page = (await client.get("/api/v1/offers?q=France&limit=1&offset=1")).json()
    assert [item["id"] for item in page["items"]] == [2]
    assert (page["total"], page["limit"], page["offset"], page["has_more"]) == (3, 1, 1, True)
    empty = (await client.get("/api/v1/offers?q=missing&limit=1")).json()
    assert empty == {"items": [], "total": 0, "limit": 1, "offset": 0, "has_more": False}


@pytest.mark.parametrize("path", ["/api/v1/campaigns", "/api/v1/offers"])
@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "offset=text"])
async def test_invalid_pagination_uses_common_error_contract(client, path, query):
    response = await client.get(f"{path}?{query}")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert all(issue["field"].startswith("query.") for issue in error["details"])
