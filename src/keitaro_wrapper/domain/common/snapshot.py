from dataclasses import dataclass


@dataclass(frozen=True)
class Snapshot:
    """Opaque adapter-owned state, retained for comparison and recovery only."""

    token: str
