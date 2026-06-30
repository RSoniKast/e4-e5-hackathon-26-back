"""Modeles ORM — miroir exact de db/init/01_schema.sql.

L'import de ce module enregistre toutes les tables sur Base.metadata
(utile pour Alembic et les tests).
"""
from app.models.auth import AppUser
from app.models.people import (
    Classe,
    ClasseEleve,
    Eleve,
    Personnel,
    PersonnelClasse,
    PersonnelHoraire,
    PersonnelSalle,
)
from app.models.sensors import EtatCalculateurLog, Releve
from app.models.structure import Batiment, Calculateur, Salle, Site

__all__ = [
    "AppUser",
    "Site",
    "Batiment",
    "Salle",
    "Calculateur",
    "Personnel",
    "Classe",
    "Eleve",
    "PersonnelSalle",
    "PersonnelClasse",
    "PersonnelHoraire",
    "ClasseEleve",
    "Releve",
    "EtatCalculateurLog",
]
