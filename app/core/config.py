"""Configuration applicative — lue depuis l'environnement / le fichier .env."""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Base de donnees : on se connecte avec le role restreint classroom_app (jamais l'admin).
    database_url: str = (
        "postgresql+asyncpg://classroom_app:App_bbBB22##@localhost:5432/classroomobserv"
    )

    # JWT
    jwt_secret: str = "change-me-dev-only-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720

    # CORS — liste d'origines. NoDecode : on parse nous-memes une chaine "a,b,c"
    # (sinon pydantic-settings tente un json.loads sur la valeur d'env et echoue).
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # Supervision : intervalle de ping en secondes (0 = tache de fond desactivee)
    ping_interval_seconds: int = 30

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
