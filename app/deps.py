"""Dependances FastAPI : session DB, utilisateur courant, controle de role."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import decode_access_token
from app.models import AppUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> AppUser:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou token expire.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_error

    user = (
        await db.execute(select(AppUser).where(AppUser.username == payload["sub"]))
    ).scalar_one_or_none()
    if user is None:
        raise credentials_error
    return user


CurrentUser = Annotated[AppUser, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> AppUser:
    """Reserve l'endpoint au role administrateur."""
    if user.role != "administrateur":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acces reserve aux administrateurs.",
        )
    return user


AdminUser = Annotated[AppUser, Depends(require_admin)]
