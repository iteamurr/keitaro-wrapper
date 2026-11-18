from copy import deepcopy

from keitaro_wrapper.application.ports.errors import GatewayError
from keitaro_wrapper.common.types import Document
from keitaro_wrapper.infrastructure.keitaro.client import KeitaroClient


class FakeKeitaro(KeitaroClient):
    def __init__(self) -> None:
        self.campaign_data = {
            7: {
                "id": 7,
                "name": "test_demo_autumn",
                "alias": "autumn",
                "state": "active",
                "type": "position",
                "domain_id": 1,
                "group_id": "2",
                "traffic_source_id": 3,
            }
        }
        self.offer_data = {
            i: {"id": i, "name": name, "state": "active"}
            for i, name in enumerate(
                [
                    "Autumn collection · France",
                    "Essential care · France",
                    "Weekend selection · France",
                    "New arrival · Europe",
                ],
                1,
            )
        }
        self.stream_data = {
            71: {
                "id": 71,
                "campaign_id": 7,
                "name": "Geo · France",
                "position": 1,
                "schema": "redirect",
                "state": "active",
                "type": "regular",
                "action_type": "http",
                "action_payload": "https://google.com",
                "offers": [],
                "filters": [{"name": "country", "mode": "accept", "payload": ["FR"]}],
            },
            72: {
                "id": 72,
                "campaign_id": 7,
                "name": "Основные офферы",
                "position": 2,
                "schema": "landings",
                "state": "active",
                "type": "default",
                "action_type": "http",
                "offers": [
                    {"offer_id": 1, "share": 34, "state": "active"},
                    {"offer_id": 2, "share": 33, "state": "active"},
                    {"offer_id": 3, "share": 33, "state": "active"},
                ],
                "filters": [],
                "landings": [],
            },
        }
        self.writes: list[tuple[str, Document, int | None]] = []
        self.timeout_action: str | None = None
        self.fail_action: str | None = None
        self.fail_read = False

    async def write(self, action: str, data: Document, remote_id: int | None = None) -> Document:
        self.writes.append((action, deepcopy(data), remote_id))
        if self.fail_action == action:
            self.fail_action = None
            raise GatewayError("integration_error", "Synthetic validation rejection")
        if action == "create_campaign":
            key = max(self.campaign_data, default=0) + 1
            self.campaign_data[key] = {**deepcopy(data), "id": key}
            result = self.campaign_data[key]
        elif action == "create_stream":
            key = max(self.stream_data, default=70) + 1
            self.stream_data[key] = {**deepcopy(data), "id": key}
            result = self.stream_data[key]
        elif action == "update_campaign":
            assert remote_id is not None
            self.campaign_data[remote_id].update(deepcopy(data))
            result = self.campaign_data[remote_id]
        else:
            assert remote_id is not None
            self.stream_data[remote_id].update(deepcopy(data))
            result = self.stream_data[remote_id]
        if self.timeout_action == action:
            self.timeout_action = None
            raise GatewayError(
                "integration_unavailable",
                "Synthetic timeout after apply",
                uncertain=True,
            )
        return deepcopy(result)

    async def campaign(self, remote_id: int) -> Document:
        if remote_id not in self.campaign_data:
            raise GatewayError("remote_not_found", "Synthetic missing campaign")
        return deepcopy(self.campaign_data[remote_id])

    async def campaigns(self) -> list[Document]:
        return deepcopy(list(self.campaign_data.values()))

    async def streams(self, campaign_id: int) -> list[Document]:
        return deepcopy([s for s in self.stream_data.values() if s["campaign_id"] == campaign_id])

    async def stream(self, stream_id: int) -> Document:
        if self.fail_read:
            raise GatewayError("integration_unavailable", "Synthetic read failure")
        if stream_id not in self.stream_data:
            raise GatewayError("remote_not_found", "Synthetic missing stream")
        return deepcopy(self.stream_data[stream_id])

    async def offers(self) -> list[Document]:
        return deepcopy(list(self.offer_data.values()))

    async def offer(self, offer_id: int) -> Document:
        if offer_id not in self.offer_data or self.offer_data[offer_id]["state"] != "active":
            raise GatewayError("offer_unavailable", "Synthetic missing offer")
        return deepcopy(self.offer_data[offer_id])

    async def creation_settings(self) -> Document:
        return {
            "prefix": "test_demo_",
            "domain_url": "https://example.invalid",
            "campaign": {"domain_id": 1, "group_id": "2", "traffic_source_id": 3},
            "geo": {
                "schema": "redirect",
                "action_type": "http",
                "action_payload": "https://google.com",
                "filters": [{"name": "country", "mode": "accept", "payload": ["{{country}}"]}],
            },
            "fallback": {
                "schema": "landings",
                "action_type": "http",
                "landings": [],
                "filters": [],
            },
        }
