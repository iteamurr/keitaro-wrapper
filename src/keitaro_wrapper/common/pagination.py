from dataclasses import dataclass


@dataclass(frozen=True)
class Pagination:
    limit: int = 20
    offset: int = 0

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= 100 or self.offset < 0:
            raise ValueError("Pagination requires 1 <= limit <= 100 and offset >= 0")


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total
