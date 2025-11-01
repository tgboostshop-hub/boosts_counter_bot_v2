
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, BigInteger, select, func, Text

import os
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./db.sqlite3")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(128))
    username: Mapped[Optional[str]] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CalcLog(Base):
    __tablename__ = "calc_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    subscribers: Mapped[int] = mapped_column(Integer)
    result_json: Mapped[str] = mapped_column(Text)  # таблица уровней в JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def upsert_user(session: AsyncSession, tg_id: int, first_name: str | None, username: str | None) -> User:
    res = await session.execute(select(User).where(User.tg_id == tg_id))
    user = res.scalar_one_or_none()
    now = datetime.utcnow()
    if user is None:
        user = User(tg_id=tg_id, first_name=first_name, username=username, created_at=now, last_active=now)
        session.add(user)
        await session.flush()
    else:
        user.last_active = now
    return user

async def stats_counts(session: AsyncSession):
    total_users = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    total_calcs = (await session.execute(select(func.count()).select_from(CalcLog))).scalar_one()
    return {"total_users": total_users, "total_calcs": total_calcs}

