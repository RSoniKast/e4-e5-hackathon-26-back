"""Schemas Pydantic : sites, batiments, salles, calculateurs."""
from __future__ import annotations

from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, field_validator

MAC_RE = r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$"


# ----------------------------- Site -----------------------------
class SiteBase(BaseModel):
    nom: str = Field(min_length=1, max_length=150)
    adresse: str | None = Field(default=None, max_length=255)
    ville: str = Field(min_length=1, max_length=100)
    code_postal: str | None = Field(default=None, max_length=10)
    latitude: float | None = None
    longitude: float | None = None


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    nom: str | None = Field(default=None, max_length=150)
    adresse: str | None = None
    ville: str | None = Field(default=None, max_length=100)
    code_postal: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class SiteRead(SiteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# --------------------------- Batiment ---------------------------
class BatimentCreate(BaseModel):
    site_id: int
    nom: str = Field(min_length=1, max_length=150)


class BatimentUpdate(BaseModel):
    site_id: int | None = None
    nom: str | None = Field(default=None, max_length=150)


class BatimentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    nom: str
    created_at: datetime


# ----------------------------- Salle ----------------------------
class SalleCreate(BaseModel):
    batiment_id: int
    nom: str = Field(min_length=1, max_length=150)
    capacite: int | None = Field(default=None, ge=0)
    heure_fermeture: time | None = None


class SalleUpdate(BaseModel):
    batiment_id: int | None = None
    nom: str | None = Field(default=None, max_length=150)
    capacite: int | None = Field(default=None, ge=0)
    heure_fermeture: time | None = None


class SalleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    batiment_id: int
    nom: str
    capacite: int | None
    heure_fermeture: time | None
    created_at: datetime


# -------------------------- Calculateur -------------------------
class CalculateurCreate(BaseModel):
    salle_id: int | None = None
    nom: str = Field(min_length=1, max_length=150)
    ip_adresse: IPvAnyAddress | None = None
    mac_adresse: str | None = Field(default=None, pattern=MAC_RE)

    @field_validator("ip_adresse")
    @classmethod
    def _ip_to_str(cls, v: IPvAnyAddress | None) -> str | None:
        return str(v) if v is not None else None


class CalculateurUpdate(BaseModel):
    salle_id: int | None = None
    nom: str | None = Field(default=None, max_length=150)
    ip_adresse: IPvAnyAddress | None = None
    mac_adresse: str | None = Field(default=None, pattern=MAC_RE)

    @field_validator("ip_adresse")
    @classmethod
    def _ip_to_str(cls, v: IPvAnyAddress | None) -> str | None:
        return str(v) if v is not None else None


class CalculateurRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    salle_id: int | None
    nom: str
    ip_adresse: str | None
    mac_adresse: str | None
    created_at: datetime

    @field_validator("ip_adresse", "mac_adresse", mode="before")
    @classmethod
    def _coerce_str(cls, v: object) -> str | None:
        # asyncpg renvoie INET/MACADDR comme objets (IPv4Address...) -> on serialise en str.
        return str(v) if v is not None else None
