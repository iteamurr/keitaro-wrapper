from types import TracebackType

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from keitaro_wrapper.application.ports.storage import (
    ITransactionContext,
    ITransactions,
    IUnitOfWork,
)
from keitaro_wrapper.common.clock import Clock
from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.infrastructure.persistence.models.integration import IntegrationRow
from keitaro_wrapper.infrastructure.persistence.models.operations import OperationRow
from keitaro_wrapper.infrastructure.persistence.repositories.operations import ORMOperations
from keitaro_wrapper.infrastructure.persistence.uow import ORMUnitOfWork

SCHEMA_REVISION = "0001_initial"


class Transaction(ITransactionContext):
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self.factory = factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> IUnitOfWork:
        self.session = self.factory()
        await self.session.begin()
        return ORMUnitOfWork(self.session)

    async def __aexit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        assert self.session is not None
        try:
            if kind is None:
                await self.session.commit()
            else:
                if isinstance(error, IntegrityError):
                    raise error
                await self.session.rollback()
        except IntegrityError:
            await self.session.rollback()
            raise DomainError(
                "concurrent_change",
                "Команда конфликтует с уже сохранёнными данными. Обновите страницу.",
            ) from None
        finally:
            await self.session.close()


class Database(ITransactions):
    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(
            url,
            pool_pre_ping=True,
            hide_parameters=True,
        )
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.owner: AsyncConnection | None = None

    def transaction(self) -> Transaction:
        return Transaction(self.factory)

    async def ready(self) -> bool:
        async with self.engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            return bool(revision == SCHEMA_REVISION)

    async def start(self, origin: str) -> None:
        if not await self.ready():
            raise DomainError("schema_not_ready", "Примените миграции перед запуском приложения.")
        self.owner = await self.engine.connect()
        acquired = await self.owner.scalar(text("SELECT pg_try_advisory_lock(731945021)"))
        await self.owner.commit()
        if not acquired:
            raise DomainError("already_running", "Для этой БД уже запущен экземпляр приложения.")
        async with self.factory.begin() as session:
            binding = await session.get(IntegrationRow, 1)
            if binding and binding.origin != origin:
                raise DomainError(
                    "origin_mismatch",
                    "База данных привязана к другому экземпляру Keitaro.",
                )
            if binding is None:
                session.add(IntegrationRow(id=1, origin=origin))
            rows = (
                await session.scalars(select(OperationRow).where(OperationRow.status == "running"))
            ).all()
            operations = ORMOperations(session)
            for row in rows:
                operation = operations._operation(row)
                operation.transition(
                    "unknown" if operation.reserves_campaign else "failed",
                    code="process_interrupted",
                    message="Работа прервана. Требуется сверка состояния.",
                    at=Clock.now(),
                )
                await operations.save(operation)

    async def close(self) -> None:
        if self.owner:
            await self.owner.execute(text("SELECT pg_advisory_unlock(731945021)"))
            await self.owner.close()
            self.owner = None
        await self.engine.dispose()
