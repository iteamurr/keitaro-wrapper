from copy import deepcopy

from keitaro_wrapper.application.ports.errors import GatewayError
from keitaro_wrapper.application.ports.remote import CreationPlan
from keitaro_wrapper.common.types import Document
from keitaro_wrapper.infrastructure.common.snapshots import thaw


class CreationCodec:
    @classmethod
    def stream_body(cls, plan: CreationPlan, stage: str) -> Document:
        template = deepcopy(thaw(plan.settings)[stage])
        country = str(plan.country_code)
        template = cls.substitute(template, country)
        template.update(
            {
                "campaign_id": plan.campaign_id,
                "name": f"Geo {country}" if stage == "geo" else "Offers",
                "comments": f"wrapper:{plan.operation_id}:{stage}",
                "state": "active",
                "position": 1 if stage == "geo" else 2,
                "type": "regular" if stage == "geo" else "default",
            }
        )
        if stage == "fallback":
            template["offers"] = [{"offer_id": int(plan.offer_id), "share": 100, "state": "active"}]
        return template

    @classmethod
    def substitute(cls, template: Document, country: str) -> Document:
        return {key: cls._substitute_value(value, country) for key, value in template.items()}

    @classmethod
    def _substitute_value(cls, value: object, country: str) -> object:
        if isinstance(value, dict):
            return cls.substitute(value, country)
        if isinstance(value, list):
            return [cls._substitute_value(item, country) for item in value]
        return country if value == "{{country}}" else value

    @classmethod
    def verify(
        cls,
        plan: CreationPlan,
        remote: Document,
        streams: list[Document],
        partial: bool = False,
    ) -> None:
        expected_campaign = thaw(plan.settings)["campaign"]
        for key in ("domain_id", "group_id", "traffic_source_id"):
            if str(remote.get(key)) != str(expected_campaign.get(key)):
                raise GatewayError(
                    "verification_failed",
                    "Настройки созданной кампании не подтверждены.",
                    uncertain=True,
                )
        expected_parameters = expected_campaign.get("parameters")
        if expected_parameters is not None and not cls.contains(
            remote.get("parameters"),
            expected_parameters,
        ):
            raise GatewayError(
                "verification_failed",
                "Параметры источника созданной кампании не подтверждены.",
                uncertain=True,
            )
        stages = [stage for stage in ("geo", "fallback") if getattr(plan, f"{stage}_id")]
        if (
            remote.get("alias") != plan.alias
            or remote.get("type") != "position"
            or remote.get("name") != plan.name
            or remote.get("notes") != f"wrapper:{plan.operation_id}:campaign"
            or remote.get("state") not in ("active", "disabled")
            or len(streams) != (len(stages) if partial else 2)
            or (partial and len(stages) < 2 and remote.get("state") != "disabled")
        ):
            raise GatewayError(
                "verification_failed",
                "Состав созданной кампании изменён или не подтверждён.",
                uncertain=True,
            )
        for stage in stages:
            expected = cls.stream_body(plan, stage)
            found = next(
                (s for s in streams if int(s["id"]) == getattr(plan, f"{stage}_id")),
                None,
            )
            if found is None or not cls.contains(found, expected):
                raise GatewayError(
                    "verification_failed",
                    "Настройки созданного потока не подтверждены.",
                    uncertain=True,
                )

    @classmethod
    def contains(cls, actual: object, expected: object) -> bool:
        if isinstance(expected, dict):
            return isinstance(actual, dict) and all(
                key in actual and cls.contains(actual[key], value)
                for key, value in expected.items()
            )
        if isinstance(expected, list):
            return (
                isinstance(actual, list)
                and len(actual) == len(expected)
                and all(cls.contains(a, e) for a, e in zip(actual, expected, strict=True))
            )
        return actual == expected
