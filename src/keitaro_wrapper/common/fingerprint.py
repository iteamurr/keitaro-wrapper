import hashlib
import json


class Fingerprint:
    @classmethod
    def of(cls, value: object) -> str:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(encoded.encode()).hexdigest()
