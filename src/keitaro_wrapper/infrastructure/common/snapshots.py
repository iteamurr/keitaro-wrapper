import json

from keitaro_wrapper.common.types import Document
from keitaro_wrapper.domain.common.snapshot import Snapshot


def freeze(document: Document) -> Snapshot:
    return Snapshot(json.dumps(document, ensure_ascii=False, sort_keys=True))


def thaw(snapshot: Snapshot) -> Document:
    value: Document = json.loads(snapshot.token)
    if not isinstance(value, dict):
        raise ValueError("Expected an object snapshot")
    return value
