import asyncio
import json
from copy import deepcopy
from typing import cast

import httpx

from keitaro_wrapper.application.ports.errors import GatewayError
from keitaro_wrapper.common.fingerprint import Fingerprint
from keitaro_wrapper.common.types import Document
from keitaro_wrapper.config import Settings
from keitaro_wrapper.domain.streams.editor import OfferAllocation


class KeitaroClient:
    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    async def write(self, action: str, data: Document, remote_id: int | None = None) -> Document:
        routes = {
            "create_campaign": ("POST", "/campaigns"),
            "create_stream": ("POST", "/streams"),
            "update_campaign": ("PUT", f"/campaigns/{remote_id}"),
            "update_stream": ("PUT", f"/streams/{remote_id}"),
        }
        if action not in routes or action.startswith("update") and remote_id is None:
            raise GatewayError("invalid_command", "Неверная операция интеграции.")
        method, path = routes[action]
        result = await self._request(method, path, data)
        if (
            not isinstance(result, dict)
            or type(result.get("id")) is not int
            or result["id"] <= 0
            or (method == "PUT" and result["id"] != remote_id)
        ):
            raise GatewayError(
                "invalid_response",
                "Keitaro вернул неподтверждённый результат записи.",
                uncertain=True,
            )
        return result

    async def campaign(self, remote_id: int) -> Document:
        return await self._object(f"/campaigns/{remote_id}", remote_id)

    async def campaigns(self) -> list[Document]:
        result: list[Document] = []
        offset = 0
        while True:
            page = self._list(await self._request("GET", f"/campaigns?limit=100&offset={offset}"))
            result.extend(page)
            if len(page) < 100:
                return result
            offset += 100
            if offset >= 100_000:
                raise GatewayError(
                    "catalog_limit",
                    "Слишком много кампаний для автоматической сверки.",
                )

    async def streams(self, campaign_id: int) -> list[Document]:
        streams = self._list(await self._request("GET", f"/campaigns/{campaign_id}/streams"))
        if any(
            type(stream.get("campaign_id")) is not int or stream["campaign_id"] != campaign_id
            for stream in streams
        ):
            raise GatewayError("invalid_response", "Keitaro вернул потоки другой кампании.")
        return streams

    async def stream(self, stream_id: int) -> Document:
        return await self._object(f"/streams/{stream_id}", stream_id)

    async def offers(self) -> list[Document]:
        offers = self._list(await self._request("GET", "/offers"))
        return [
            {
                "id": o["id"],
                "name": str(o.get("name", f"Оффер #{o['id']}")),
                "state": o.get("state", "unknown"),
            }
            for o in offers
        ]

    async def offer(self, offer_id: int) -> Document:
        offer = await self._object(f"/offers/{offer_id}", offer_id)
        if offer.get("state") != "active":
            raise GatewayError("offer_unavailable", "Оффер отключён или недоступен в Keitaro.")
        return {
            "id": offer_id,
            "name": str(offer.get("name", f"Оффер #{offer_id}")),
            "state": "active",
        }

    async def creation_settings(self) -> Document:
        path = self.settings.keitaro_creation_profile
        if path is None:
            raise GatewayError(
                "creation_not_verified",
                "Создание пока недоступно: нужен проверенный профиль API этого экземпляра (K-02/K-05).",
            )
        try:
            profile = json.loads(await asyncio.to_thread(path.read_text))
            if (
                profile["version"] != 1
                or profile["origin"] != self.settings.keitaro_base_url
                or profile["verified"] is not True
            ):
                raise ValueError("Invalid profile")
            geo, fallback = profile["geo"], profile["fallback"]
            if (
                geo["schema"] != "redirect"
                or fallback["schema"] != "landings"
                or not geo.get("action_type")
                or not fallback.get("action_type")
            ):
                raise ValueError("Invalid schemas")
            if "{{country}}" not in json.dumps(
                geo.get("filters")
            ) or "https://google.com" not in json.dumps(geo):
                raise ValueError("Missing required routing")
        except (OSError, ValueError, KeyError, TypeError):
            raise GatewayError(
                "creation_not_verified",
                "Профиль создания отсутствует, некорректен или относится к другому экземпляру.",
            ) from None
        domains = self._list(await self._request("GET", "/domains"))
        groups = self._list(await self._request("GET", "/groups?type=campaigns"))
        sources = self._list(await self._request("GET", "/traffic_sources"))
        domain = next(
            (
                d
                for d in domains
                if d["id"] == self.settings.keitaro_domain_id and d.get("state") == "active"
            ),
            None,
        )
        group = next((g for g in groups if g["id"] == self.settings.keitaro_group_id), None)
        source = next(
            (
                s
                for s in sources
                if s["id"] == self.settings.keitaro_traffic_source_id
                and s.get("state", "active") == "active"
            ),
            None,
        )
        if (
            not domain
            or not group
            or not source
            or not self.settings.campaign_name_prefix.startswith("test_")
        ):
            raise GatewayError(
                "invalid_configuration",
                "Проверьте домен, группу, источник и тестовый префикс.",
            )
        domain_url = str(domain.get("name", ""))
        if not domain_url.startswith(("https://", "http://")):
            domain_url = ("https://" if domain.get("is_ssl") else "http://") + domain_url
        return {
            "prefix": self.settings.campaign_name_prefix,
            "domain_url": domain_url,
            "geo": geo,
            "fallback": fallback,
            "campaign": {
                "domain_id": domain["id"],
                "group_id": str(group["id"]),
                "traffic_source_id": source["id"],
                "parameters": source.get("parameters", {}),
            },
        }

    def inspect(
        self,
        stream: Document,
        names: dict[int, str],
    ) -> tuple[list[OfferAllocation], str | None]:
        fields = {
            "id",
            "type",
            "name",
            "campaign_id",
            "position",
            "weight",
            "action_options",
            "comments",
            "state",
            "updated_at",
            "created_at",
            "action_type",
            "action_payload",
            "schema",
            "collect_clicks",
            "filter_or",
            "filters",
            "triggers",
            "landings",
            "offers",
            "offer_selection",
        }
        reason = None
        if stream.get("schema") != "landings":
            reason = "Поток без поддерживаемой схемы офферов — только чтение."
        elif (
            set(stream) - fields or stream.get("offer_selection", "before_click") != "before_click"
        ):
            reason = "Настройки потока не поддерживаются редактором."
        elif stream.get("state") != "active":
            reason = "Поток не активен в Keitaro."
        offers = stream.get("offers", [])
        if not isinstance(offers, list):
            raise GatewayError("invalid_response", "Некорректный список офферов в потоке.")
        allocations = []
        seen = set()
        for item in offers:
            if (
                not isinstance(item, dict)
                or type(item.get("offer_id")) is not int
                or type(item.get("share")) is not int
                or item["offer_id"] <= 0
                or item["offer_id"] in seen
            ):
                raise GatewayError(
                    "invalid_response",
                    "Некорректные или повторяющиеся привязки офферов.",
                )
            seen.add(item["offer_id"])
            if (
                set(item)
                - {"id", "stream_id", "offer_id", "share", "state", "created_at", "updated_at"}
                or item.get("state") != "active"
                or not 0 <= item["share"] <= 100
            ):
                reason = "Поток содержит отключённые или неподдерживаемые привязки."
            allocations.append(
                OfferAllocation(
                    item["offer_id"],
                    names.get(item["offer_id"], f"Оффер #{item['offer_id']}"),
                    item["share"],
                    active=item.get("state") == "active",
                    external_state=str(item.get("state", "unknown")),
                )
            )
        return allocations, reason

    def signature(self, stream: Document) -> str:
        clean = deepcopy(stream)
        # Keitaro 11.5 converts null to an empty string after an offers-only PUT.
        # Both mean no action payload for a landings stream; redirects stay strict.
        if clean.get("schema") == "landings" and clean.get("action_payload") in (None, ""):
            clean["action_payload"] = None
        for key in ("created_at", "updated_at"):
            clean.pop(key, None)
        for field in ("offers", "landings", "filters", "triggers"):
            items = clean.get(field, [])
            if not isinstance(items, list):
                raise GatewayError("invalid_response", "Некорректная конфигурация потока.")
            for item in items:
                if not isinstance(item, dict):
                    raise GatewayError("invalid_response", "Некорректная конфигурация потока.")
                for key in ("id", "stream_id", "created_at", "updated_at", "oid"):
                    item.pop(key, None)
            if field == "offers":
                if any(type(item.get("offer_id")) is not int for item in items):
                    raise GatewayError("invalid_response", "Некорректные привязки офферов.")
                items.sort(key=lambda item: item["offer_id"])
            clean[field] = items
        return Fingerprint.of(clean)

    async def _object(self, path: str, expected_id: int) -> Document:
        data = await self._request("GET", path)
        if (
            not isinstance(data, dict)
            or type(data.get("id")) is not int
            or data["id"] != expected_id
        ):
            raise GatewayError("invalid_response", "Keitaro вернул неверный объект.")
        return data

    @classmethod
    def _list(cls, data: object) -> list[Document]:
        if not isinstance(data, list) or any(
            not isinstance(o, dict) or type(o.get("id")) is not int or o["id"] <= 0 for o in data
        ):
            raise GatewayError("invalid_response", "Keitaro вернул неверный список объектов.")
        result = cast(list[Document], data)
        if len({o["id"] for o in result}) != len(result):
            raise GatewayError("invalid_response", "Keitaro вернул дубликаты объектов.")
        return result

    async def _request(self, method: str, path: str, body: Document | None = None) -> object:
        key = self.settings.keitaro_api_key.get_secret_value()
        if not key:
            raise GatewayError(
                "integration_unconfigured",
                "Укажите API-ключ Keitaro в локальном окружении.",
            )
        for attempt in range(2 if method == "GET" else 1):
            try:
                response = await self.client.request(
                    method,
                    f"{self.settings.keitaro_base_url}/admin_api/v1{path}",
                    headers={"Api-Key": key},
                    json=body,
                    follow_redirects=False,
                )
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
                if method == "GET" and attempt == 0:
                    await asyncio.sleep(0.1)
                    continue
                raise GatewayError(
                    "integration_unavailable",
                    "Не удалось подключиться к Keitaro.",
                ) from None
            except httpx.HTTPError:
                raise GatewayError(
                    "integration_unavailable",
                    "Запрос Keitaro прерван. Проверьте состояние операции.",
                    uncertain=method != "GET",
                ) from None
            if response.status_code >= 500 and method == "GET" and attempt == 0:
                await asyncio.sleep(0.1)
                continue
            if response.status_code >= 400 or response.is_redirect:
                code = "integration_error"
                if response.status_code == 404:
                    code = "remote_not_found"
                elif response.status_code in (401, 402, 403):
                    code = "integration_access"
                raise GatewayError(
                    code,
                    "Keitaro отклонил запрос. Проверьте доступность и права интеграции.",
                    {"status": response.status_code},
                    uncertain=method != "GET" and response.status_code >= 500,
                )
            try:
                return cast(object, response.json())
            except ValueError:
                raise GatewayError(
                    "invalid_response",
                    "Keitaro вернул ответ не в формате JSON.",
                    uncertain=method != "GET",
                ) from None
        raise GatewayError("integration_unavailable", "Keitaro недоступен.")
