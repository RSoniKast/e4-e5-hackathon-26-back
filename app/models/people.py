"""Personnels, classes, eleves et leurs liaisons N-N."""
from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Personnel(Base):
    __tablename__ = "personnel"

    id: Mapped[int] = mapped_column(primary_key=True)
    identifiant: Mapped[str] = mapped_column(String(50), unique=True)
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Classe(Base):
    __tablename__ = "classe"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100))
    niveau: Mapped[str | None] = mapped_column(String(50))
    annee_scolaire: Mapped[str] = mapped_column(String(9))
    professeur_principal_id: Mapped[int | None] = mapped_column(
        ForeignKey("personnel.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("nom", "annee_scolaire", name="uq_classe_nom_annee"),
    )


class Eleve(Base):
    __tablename__ = "eleve"

    id: Mapped[int] = mapped_column(primary_key=True)
    identifiant: Mapped[str] = mapped_column(String(50), unique=True)
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))
    telephone: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PersonnelSalle(Base):
    __tablename__ = "personnel_salle"

    personnel_id: Mapped[int] = mapped_column(
        ForeignKey("personnel.id", ondelete="CASCADE"), primary_key=True
    )
    salle_id: Mapped[int] = mapped_column(
        ForeignKey("salle.id", ondelete="CASCADE"), primary_key=True
    )


class PersonnelClasse(Base):
    __tablename__ = "personnel_classe"

    personnel_id: Mapped[int] = mapped_column(
        ForeignKey("personnel.id", ondelete="CASCADE"), primary_key=True
    )
    classe_id: Mapped[int] = mapped_column(
        ForeignKey("classe.id", ondelete="CASCADE"), primary_key=True
    )
    matiere: Mapped[str] = mapped_column(String(100), primary_key=True, default="")


class PersonnelHoraire(Base):
    __tablename__ = "personnel_horaire"

    id: Mapped[int] = mapped_column(primary_key=True)
    personnel_id: Mapped[int] = mapped_column(
        ForeignKey("personnel.id", ondelete="CASCADE")
    )
    jour: Mapped[int] = mapped_column(SmallInteger)  # 1=lundi ... 7=dimanche
    heure_debut: Mapped[time] = mapped_column(Time)
    heure_fin: Mapped[time] = mapped_column(Time)

    __table_args__ = (
        CheckConstraint("jour BETWEEN 1 AND 7", name="ck_horaire_jour"),
        CheckConstraint("heure_fin > heure_debut", name="ck_horaire_plage"),
    )


class ClasseEleve(Base):
    __tablename__ = "classe_eleve"

    classe_id: Mapped[int] = mapped_column(
        ForeignKey("classe.id", ondelete="CASCADE"), primary_key=True
    )
    eleve_id: Mapped[int] = mapped_column(
        ForeignKey("eleve.id", ondelete="CASCADE"), primary_key=True
    )
    annee_scolaire: Mapped[str] = mapped_column(String(9))

    __table_args__ = (
        # un eleve ne peut etre que dans UNE classe pour une annee donnee
        UniqueConstraint("eleve_id", "annee_scolaire", name="uq_eleve_annee"),
    )
