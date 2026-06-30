"""Router d'authentification : login (JWT) et profil courant."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.core.security import create_access_token, verify_password
from app.deps import CurrentUser, DbSession
from app.models import AppUser
from app.schemas.auth import Token, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> Token:
    user = (
        await db.execute(select(AppUser).where(AppUser.username == form.username))
    ).scalar_one_or_none()
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=user.username, role=user.role)
    return Token(access_token=token)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> AppUser:
    return user
