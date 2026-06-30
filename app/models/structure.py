"""Hierarchie Site -> Batiment -> Salle -> Calculateur (miroir de 01_schema.sql)."""
from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET, MACADDR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Site(Base):
    __tablename__ = "site"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(150))
    adresse: Mapped[str | None] = mapped_column(String(255))
    ville: Mapped[str] = mapped_column(String(100))
    code_postal: Mapped[str | None] = mapped_column(String(10))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    batiments: Mapped[list["Batiment"]] = relationship(back_populates="site")

    __table_args__ = (UniqueConstraint("nom", "ville", name="uq_site_nom_ville"),)


class Batiment(Base):
    __tablename__ = "batiment"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(
        ForeignKey("site.id", ondelete="RESTRICT")
    )
    nom: Mapped[str] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    site: Mapped["Site"] = relationship(back_populates="batiments")
    salles: Mapped[list["Salle"]] = relationship(back_populates="batiment")

    __table_args__ = (
        UniqueConstraint("site_id", "nom", name="uq_batiment_nom_site"),
    )


class Salle(Base):
    __tablename__ = "salle"

    id: Mapped[int] = mapped_column(primary_key=True)
    batiment_id: Mapped[int] = mapped_column(
        ForeignKey("batiment.id", ondelete="RESTRICT")
    )
    nom: Mapped[str] = mapped_column(String(150))
    capacite: Mapped[int | None] = mapped_column(Integer)
    heure_fermeture: Mapped[time | None] = mapped_column(Time)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    batiment: Mapped["Batiment"] = relationship(back_populates="salles")
    calculateurs: Mapped[list["Calculateur"]] = relationship(
        back_populates="salle"
    )

    __table_args__ = (
        UniqueConstraint("batiment_id", "nom", name="uq_salle_nom_batiment"),
        CheckConstraint("capacite >= 0", name="ck_salle_capacite"),
    )


class Calculateur(Base):
    __tablename__ = "calculateur"

    id: Mapped[int] = mapped_column(primary_key=True)
    salle_id: Mapped[int | None] = mapped_column(
        ForeignKey("salle.id", ondelete="SET NULL")
    )
    nom: Mapped[str] = mapped_column(String(150))
    ip_adresse: Mapped[str | None] = mapped_column(INET, unique=True)
    mac_adresse: Mapped[str | None] = mapped_column(MACADDR, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    salle: Mapped["Salle | None"] = relationship(back_populates="calculateurs")
