"""Releves de capteurs et journal d'etat reseau (ping)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Releve(Base):
    __tablename__ = "releve"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    calculateur_id: Mapped[int] = mapped_column(
        ForeignKey("calculateur.id", ondelete="CASCADE")
    )
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    luminosite: Mapped[int | None] = mapped_column(SmallInteger)
    presence: Mapped[bool | None] = mapped_column(Boolean)
    fenetre_ouverte: Mapped[bool | None] = mapped_column(Boolean)
    porte_ouverte: Mapped[bool | None] = mapped_column(Boolean)
    mesure_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "temperature BETWEEN -20 AND 50", name="ck_releve_temperature"
        ),
        CheckConstraint(
            "luminosite BETWEEN 0 AND 1023", name="ck_releve_luminosite"
        ),
        Index("idx_releve_calc_time", "calculateur_id", mesure_at.desc()),
    )


class EtatCalculateurLog(Base):
    __tablename__ = "etat_calculateur_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    calculateur_id: Mapped[int] = mapped_column(
        ForeignKey("calculateur.id", ondelete="CASCADE")
    )
    en_ligne: Mapped[bool] = mapped_column(Boolean)  # true = vert, false = rouge
    change_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_etat_calc_time", "calculateur_id", change_at.desc()),
    )
