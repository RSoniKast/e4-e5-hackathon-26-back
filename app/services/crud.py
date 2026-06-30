"""CRUD generique async, reutilise par les routers d'administration.

Garde les routers minces (convention §8 du CLAUDE.md : pas de logique dans les
routers). Les violations d'unicite / cles etrangeres remontent en IntegrityError
et sont converties en 409 par le handler global (app/main.py).
"""
from __future__ import annotations

from typing import Any, Generic, Sequence, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class CRUD(Generic[ModelT]):
    def __init__(self, model: type[ModelT]) -> None:
        self.model = model

    async def list(
        self, db: AsyncSession, *, filters: dict[str, Any] | None = None
    ) -> Sequence[ModelT]:
        stmt = select(self.model)
        for field, value in (filters or {}).items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, field) == value)
        stmt = stmt.order_by(self.model.id)
        return (await db.execute(stmt)).scalars().all()

    async def get(self, db: AsyncSession, obj_id: int) -> ModelT:
        obj = await db.get(self.model, obj_id)
        if obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model.__name__} introuvable (id={obj_id}).",
            )
        return obj

    async def create(self, db: AsyncSession, data: dict[str, Any]) -> ModelT:
        obj = self.model(**data)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def update(
        self, db: AsyncSession, obj_id: int, data: dict[str, Any]
    ) -> ModelT:
        obj = await self.get(db, obj_id)
        for field, value in data.items():
            setattr(obj, field, value)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def delete(self, db: AsyncSession, obj_id: int) -> None:
        obj = await self.get(db, obj_id)
        await db.delete(obj)
        await db.commit()
