from dataclasses import dataclass, field


@dataclass
class DomainError(Exception):
    code: str
    message: str
    details: dict[str, str | int] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message
