"""Ingestion IoT + supervision : releves, etat reseau, mesures par salle."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession
from app.models import Calculateur, EtatCalculateurLog, Releve, Salle
from app.schemas.sensors import (
    EtatCalculateurRead,
    MesuresSalle,
    ReleveArduino,
    ReleveCreate,
    ReleveRead,
)

# --------------------------- Ingestion --------------------------
releves = APIRouter(prefix="/api/releves", tags=["ingestion"])


@releves.post("", response_model=ReleveRead, status_code=status.HTTP_201_CREATED)
async def ingest_releve(payload: ReleveCreate, db: DbSession):
    """Recoit une mesure d'un capteur (Arduino reel ou simulateur).

    Pas de role administrateur ici : c'est le capteur/collecteur qui poste.
    (a securiser ulterieurement par cle d'API/mTLS selon l'infra.)
    """
    data = payload.model_dump(exclude_none=True)
    releve = Releve(**data)
    db.add(releve)
    await db.commit()
    await db.refresh(releve)
    return releve


@releves.post("/arduino", response_model=ReleveRead, status_code=status.HTTP_201_CREATED)
async def ingest_releve_arduino(payload: ReleveArduino, db: DbSession):
    """Ingestion au format compact Arduino/VM : {id, t, l, p, f, o}.

    Mappe vers la table releve. Renvoie 404 si le calculateur n'existe pas
    (message clair plutot qu'une violation de cle etrangere).
    """
    if await db.get(Calculateur, payload.id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calculateur introuvable (id={payload.id}).",
        )
    releve = Releve(
        calculateur_id=payload.id,
        temperature=payload.t,
        luminosite=payload.l,
        presence=payload.p,
        fenetre_ouverte=payload.f,
        porte_ouverte=payload.o,
    )
    db.add(releve)
    await db.commit()
    await db.refresh(releve)
    return releve


# -------------------------- Monitoring --------------------------
# Prefixe partage avec le router calculateurs : ce router DOIT etre inclus
# AVANT le CRUD calculateurs pour que /etat ne soit pas capte par /{calc_id}.
monitoring = APIRouter(prefix="/api/calculateurs", tags=["monitoring"])


@monitoring.get("/etat", response_model=list[EtatCalculateurRead])
async def etat_calculateurs(db: DbSession, _: CurrentUser):
    """Etat reseau courant de chaque calculateur (dernier log de ping)."""
    # Dernier change_at par calculateur
    derniers = (
        select(
            EtatCalculateurLog.calculateur_id,
            func.max(EtatCalculateurLog.change_at).label("change_at"),
        )
        .group_by(EtatCalculateurLog.calculateur_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(
                Calculateur.id,
                Calculateur.nom,
                EtatCalculateurLog.en_ligne,
                EtatCalculateurLog.change_at,
            )
            .outerjoin(derniers, derniers.c.calculateur_id == Calculateur.id)
            .outerjoin(
                EtatCalculateurLog,
                (EtatCalculateurLog.calculateur_id == derniers.c.calculateur_id)
                & (EtatCalculateurLog.change_at == derniers.c.change_at),
            )
            .order_by(Calculateur.id)
        )
    ).all()
    return [
        EtatCalculateurRead(
            calculateur_id=r.id, nom=r.nom, en_ligne=r.en_ligne, change_at=r.change_at
        )
        for r in rows
    ]


# ----------------------- Visualisation salle --------------------
salle_mesures = APIRouter(prefix="/api/salles", tags=["visualisation"])


@salle_mesures.get("/{salle_id}/mesures", response_model=MesuresSalle)
async def mesures_salle(salle_id: int, db: DbSession, _: CurrentUser):
    """Derniere mesure connue de la salle + etat reseau des calculateurs + alerte."""
    salle = await db.get(Salle, salle_id)
    if salle is None:
        raise HTTPException(status_code=404, detail=f"Salle introuvable (id={salle_id}).")

    calc_ids = (
        await db.execute(
            select(Calculateur.id).where(Calculateur.salle_id == salle_id)
        )
    ).scalars().all()

    # Derniere mesure (tous calculateurs de la salle confondus)
    derniere = None
    if calc_ids:
        derniere = (
            await db.execute(
                select(Releve)
                .where(Releve.calculateur_id.in_(calc_ids))
                .order_by(Releve.mesure_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    # Etat reseau par calculateur de la salle
    etats: list[EtatCalculateurRead] = []
    for cid in calc_ids:
        row = (
            await db.execute(
                select(Calculateur.nom, EtatCalculateurLog.en_ligne, EtatCalculateurLog.change_at)
                .select_from(Calculateur)
                .outerjoin(EtatCalculateurLog, EtatCalculateurLog.calculateur_id == Calculateur.id)
                .where(Calculateur.id == cid)
                .order_by(EtatCalculateurLog.change_at.desc())
                .limit(1)
            )
        ).first()
        if row is not None:
            etats.append(
                EtatCalculateurRead(
                    calculateur_id=cid, nom=row.nom,
                    en_ligne=row.en_ligne, change_at=row.change_at,
                )
            )

    # Alerte "salle ouverte apres l'heure de fermeture"
    alerte = False
    if (
        salle.heure_fermeture is not None
        and derniere is not None
        and (derniere.porte_ouverte or derniere.fenetre_ouverte)
    ):
        maintenant = datetime.now(timezone.utc).time()
        alerte = maintenant > salle.heure_fermeture

    return MesuresSalle(
        salle_id=salle.id,
        nom=salle.nom,
        heure_fermeture=salle.heure_fermeture.isoformat() if salle.heure_fermeture else None,
        alerte_ouverture=alerte,
        derniere_mesure=ReleveRead.model_validate(derniere) if derniere else None,
        calculateurs=etats,
    )
