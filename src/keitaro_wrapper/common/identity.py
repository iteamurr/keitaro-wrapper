from uuid import UUID, uuid4


class Identity:
    @classmethod
    def new(cls) -> UUID:
        return uuid4()
