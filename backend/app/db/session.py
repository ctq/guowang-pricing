from collections.abc import AsyncIterator
import os
from pathlib import Path

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DB_PATH = Path(os.getenv("GUOWANG_DB_PATH", str(Path(__file__).resolve().parents[2] / "guowang.sqlite3")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    from app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for column in ("request_json", "result_json"):
            try:
                await conn.exec_driver_sql(f"ALTER TABLE calculation_logs ADD COLUMN {column} TEXT")
            except OperationalError:
                pass
        try:
            await conn.exec_driver_sql("ALTER TABLE login_qrcodes RENAME COLUMN scene_str TO code")
        except OperationalError:
            pass
        for col in ("openid",):
            for tbl in ("calculation_records", "calculation_logs"):
                try:
                    await conn.exec_driver_sql(f"ALTER TABLE {tbl} ADD COLUMN {col} VARCHAR(128)")
                except OperationalError:
                    pass
