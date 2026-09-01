"""Инициализация движка, сессий и небольших совместимых миграций БД."""
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from database.models import Base

engine = create_async_engine(settings.database_url, echo=False)

async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def init_db() -> None:
    """Создать таблицы и обновить старую схему без удаления данных."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        admin_columns = await conn.run_sync(
            lambda sync_conn: {
                column["name"]
                for column in inspect(sync_conn).get_columns("admins")
            }
        )
        if "is_superadmin" not in admin_columns:
            await conn.execute(
                text(
                    "ALTER TABLE admins ADD COLUMN "
                    "is_superadmin BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
