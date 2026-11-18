from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Campaign:
    id: UUID
    name: str
    remote_id: int | None = None
    alias: str = ""
    state: str = "importing"
    revision: int = 0
    url: str | None = None
    last_fetched_at: datetime | None = None

    def touch(self) -> None:
        self.revision += 1

    def set_tracking_url(self, domain_url: str) -> None:
        self.url = f"{domain_url.rstrip('/')}/{self.alias}"

    def accept(self, remote_id: int, name: str, alias: str, state: str, when: datetime) -> None:
        self.remote_id = remote_id
        self.name = name
        self.alias = alias
        self.state = state
        self.last_fetched_at = when
        self.touch()
