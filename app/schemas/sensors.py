"""Schemas Pydantic : ingestion de releves, mesures, etat reseau."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ReleveCreate(BaseModel):
    """Mesures envoyees par un capteur (Arduino reel ou simulateur)."""

    calculateur_id: int
    temperature: Decimal | None = Field(default=None, ge=-20, le=50)
    luminosite: int | None = Field(default=None, ge=0, le=1023)
    presence: bool | None = None
    fenetre_ouverte: bool | None = None
    porte_ouverte: bool | None = None
    mesure_at: datetime | None = None  # sinon now() cote serveur


class ReleveArduino(BaseModel):
    """Format compact envoye par l'Arduino / la VM (cf. Azure Function).

    id=calculateur, t=temperature, l=luminosite, p=presence, f=fenetre, o=porte.
    """

    id: int
    t: Decimal | None = Field(default=None, ge=-20, le=50)
    l: int | None = Field(default=None, ge=0, le=1023)
    p: bool | None = None
    f: bool | None = None
    o: bool | None = None


class ReleveRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    calculateur_id: int
    temperature: Decimal | None
    luminosite: int | None
    presence: bool | None
    fenetre_ouverte: bool | None
    porte_ouverte: bool | None
    mesure_at: datetime


class EtatCalculateurRead(BaseModel):
    """Etat reseau courant d'un calculateur (issu du dernier log de ping)."""

    calculateur_id: int
    nom: str
    en_ligne: bool | None  # None = jamais pingue
    change_at: datetime | None


class MesuresSalle(BaseModel):
    """Vue de visualisation d'une salle : derniere mesure par calculateur + alerte."""

    salle_id: int
    nom: str
    heure_fermeture: str | None
    alerte_ouverture: bool  # salle ouverte apres l'heure de fermeture
    derniere_mesure: ReleveRead | None
    calculateurs: list[EtatCalculateurRead]
