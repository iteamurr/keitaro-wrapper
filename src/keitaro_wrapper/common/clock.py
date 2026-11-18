from datetime import UTC, datetime


class Clock:
    @classmethod
    def now(cls) -> datetime:
        return datetime.now(UTC)
