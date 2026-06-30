"""Schemas Pydantic : personnels, classes, eleves, liaisons, horaires."""
from __future__ import annotations

from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --------------------------- Personnel --------------------------
class PersonnelCreate(BaseModel):
    identifiant: str = Field(min_length=1, max_length=50)
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None


class PersonnelUpdate(BaseModel):
    identifiant: str | None = Field(default=None, max_length=50)
    nom: str | None = Field(default=None, max_length=100)
    prenom: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None


class PersonnelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    identifiant: str
    nom: str
    prenom: str
    email: str | None
    created_at: datetime


# ---------------------------- Classe ----------------------------
class ClasseCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    niveau: str | None = Field(default=None, max_length=50)
    annee_scolaire: str = Field(min_length=4, max_length=9)  # ex. "2025-2026"
    professeur_principal_id: int | None = None


class ClasseUpdate(BaseModel):
    nom: str | None = Field(default=None, max_length=100)
    niveau: str | None = Field(default=None, max_length=50)
    annee_scolaire: str | None = Field(default=None, max_length=9)
    professeur_principal_id: int | None = None


class ClasseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nom: str
    niveau: str | None
    annee_scolaire: str
    professeur_principal_id: int | None
    created_at: datetime


# ----------------------------- Eleve ----------------------------
class EleveCreate(BaseModel):
    identifiant: str = Field(min_length=1, max_length=50)
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    telephone: str | None = Field(default=None, max_length=30)


class EleveUpdate(BaseModel):
    identifiant: str | None = Field(default=None, max_length=50)
    nom: str | None = Field(default=None, max_length=100)
    prenom: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    telephone: str | None = Field(default=None, max_length=30)


class EleveRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    identifiant: str
    nom: str
    prenom: str
    email: str | None
    telephone: str | None
    created_at: datetime


class EleveImportResult(BaseModel):
    importes: int
    ignores: int
    erreurs: list[str]


# ------------------------- Affectations -------------------------
class ClasseEleveAffectation(BaseModel):
    eleve_id: int
    annee_scolaire: str = Field(min_length=4, max_length=9)


class PersonnelClasseAffectation(BaseModel):
    personnel_id: int
    matiere: str = Field(default="", max_length=100)


class HoraireCreate(BaseModel):
    jour: int = Field(ge=1, le=7)  # 1 = lundi
    heure_debut: time
    heure_fin: time


class HoraireRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    personnel_id: int
    jour: int
    heure_debut: time
    heure_fin: time
