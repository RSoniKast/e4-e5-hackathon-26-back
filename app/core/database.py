"""Moteur SQLAlchemy 2.0 async + fabrique de sessions."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = async_sessionmaker(
    bind=engine, expire_on_commit=False, autoflush=False
)


class Base(DeclarativeBase):
    """Classe de base declarative pour tous les modeles ORM."""


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependance FastAPI : fournit une session DB par requete."""
    async with SessionLocal() as session:
        yield session
