"""Schemas Pydantic pour l'authentification."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.security import validate_password_complexity


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Literal["utilisateur", "administrateur"]
    created_at: datetime


class UserCreate(BaseModel):
    username: str
    password: str
    role: Literal["utilisateur", "administrateur"] = "utilisateur"

    @field_validator("password")
    @classmethod
    def _check_complexity(cls, v: str) -> str:
        if not validate_password_complexity(v):
            raise ValueError(
                "Mot de passe trop faible : >= 8 caracteres avec au moins "
                "1 minuscule, 1 majuscule, 1 chiffre et 1 caractere special."
            )
        return v
