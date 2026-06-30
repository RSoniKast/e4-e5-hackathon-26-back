"""CRUD personnels / classes / eleves + affectations N-N + import CSV eleves."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import delete, select

from app.deps import CurrentUser, DbSession, require_admin
from app.models import (
    Classe,
    ClasseEleve,
    Eleve,
    Personnel,
    PersonnelClasse,
    PersonnelHoraire,
)
from app.schemas.people import (
    ClasseCreate,
    ClasseEleveAffectation,
    ClasseRead,
    ClasseUpdate,
    EleveCreate,
    EleveImportResult,
    EleveRead,
    EleveUpdate,
    HoraireCreate,
    HoraireRead,
    PersonnelClasseAffectation,
    PersonnelCreate,
    PersonnelRead,
    PersonnelUpdate,
)
from app.services.crud import CRUD

write_admin = Depends(require_admin)

personnel_crud = CRUD(Personnel)
classe_crud = CRUD(Classe)
eleve_crud = CRUD(Eleve)


# =========================== PERSONNELS ==========================
personnels = APIRouter(prefix="/api/personnels", tags=["personnels"])


@personnels.get("", response_model=list[PersonnelRead])
async def list_personnels(db: DbSession, _: CurrentUser):
    return await personnel_crud.list(db)


@personnels.get("/{pid}", response_model=PersonnelRead)
async def get_personnel(pid: int, db: DbSession, _: CurrentUser):
    return await personnel_crud.get(db, pid)


@personnels.post("", response_model=PersonnelRead, status_code=status.HTTP_201_CREATED,
                 dependencies=[write_admin])
async def create_personnel(payload: PersonnelCreate, db: DbSession):
    return await personnel_crud.create(db, payload.model_dump())


@personnels.put("/{pid}", response_model=PersonnelRead, dependencies=[write_admin])
async def update_personnel(pid: int, payload: PersonnelUpdate, db: DbSession):
    return await personnel_crud.update(db, pid, payload.model_dump(exclude_unset=True))


@personnels.delete("/{pid}", status_code=status.HTTP_204_NO_CONTENT,
                   dependencies=[write_admin])
async def delete_personnel(pid: int, db: DbSession):
    await personnel_crud.delete(db, pid)


@personnels.get("/{pid}/horaires", response_model=list[HoraireRead])
async def list_horaires(pid: int, db: DbSession, _: CurrentUser):
    await personnel_crud.get(db, pid)  # 404 si introuvable
    rows = (
        await db.execute(
            select(PersonnelHoraire).where(PersonnelHoraire.personnel_id == pid)
        )
    ).scalars().all()
    return rows


@personnels.post("/{pid}/horaires", response_model=HoraireRead,
                 status_code=status.HTTP_201_CREATED, dependencies=[write_admin])
async def add_horaire(pid: int, payload: HoraireCreate, db: DbSession):
    await personnel_crud.get(db, pid)
    horaire = PersonnelHoraire(personnel_id=pid, **payload.model_dump())
    db.add(horaire)
    await db.commit()
    await db.refresh(horaire)
    return horaire


# ============================ CLASSES ============================
classes = APIRouter(prefix="/api/classes", tags=["classes"])


@classes.get("", response_model=list[ClasseRead])
async def list_classes(db: DbSession, _: CurrentUser, annee_scolaire: str | None = None):
    return await classe_crud.list(db, filters={"annee_scolaire": annee_scolaire})


@classes.get("/{cid}", response_model=ClasseRead)
async def get_classe(cid: int, db: DbSession, _: CurrentUser):
    return await classe_crud.get(db, cid)


@classes.post("", response_model=ClasseRead, status_code=status.HTTP_201_CREATED,
              dependencies=[write_admin])
async def create_classe(payload: ClasseCreate, db: DbSession):
    return await classe_crud.create(db, payload.model_dump())


@classes.put("/{cid}", response_model=ClasseRead, dependencies=[write_admin])
async def update_classe(cid: int, payload: ClasseUpdate, db: DbSession):
    return await classe_crud.update(db, cid, payload.model_dump(exclude_unset=True))


@classes.delete("/{cid}", status_code=status.HTTP_204_NO_CONTENT,
                dependencies=[write_admin])
async def delete_classe(cid: int, db: DbSession):
    await classe_crud.delete(db, cid)


@classes.get("/{cid}/eleves", response_model=list[EleveRead])
async def list_classe_eleves(cid: int, db: DbSession, _: CurrentUser):
    await classe_crud.get(db, cid)
    stmt = (
        select(Eleve)
        .join(ClasseEleve, ClasseEleve.eleve_id == Eleve.id)
        .where(ClasseEleve.classe_id == cid)
        .order_by(Eleve.nom, Eleve.prenom)
    )
    return (await db.execute(stmt)).scalars().all()


@classes.post("/{cid}/eleves", status_code=status.HTTP_201_CREATED,
              dependencies=[write_admin])
async def affecter_eleve(cid: int, payload: ClasseEleveAffectation, db: DbSession):
    await classe_crud.get(db, cid)
    await eleve_crud.get(db, payload.eleve_id)
    db.add(
        ClasseEleve(
            classe_id=cid,
            eleve_id=payload.eleve_id,
            annee_scolaire=payload.annee_scolaire,
        )
    )
    await db.commit()
    return {"detail": "Eleve affecte a la classe."}


@classes.delete("/{cid}/eleves/{eleve_id}", status_code=status.HTTP_204_NO_CONTENT,
                dependencies=[write_admin])
async def retirer_eleve(cid: int, eleve_id: int, db: DbSession):
    await db.execute(
        delete(ClasseEleve).where(
            ClasseEleve.classe_id == cid, ClasseEleve.eleve_id == eleve_id
        )
    )
    await db.commit()


@classes.post("/{cid}/personnels", status_code=status.HTTP_201_CREATED,
              dependencies=[write_admin])
async def affecter_personnel(cid: int, payload: PersonnelClasseAffectation, db: DbSession):
    await classe_crud.get(db, cid)
    await personnel_crud.get(db, payload.personnel_id)
    db.add(
        PersonnelClasse(
            classe_id=cid, personnel_id=payload.personnel_id, matiere=payload.matiere
        )
    )
    await db.commit()
    return {"detail": "Personnel affecte a la classe."}


# ============================= ELEVES ============================
eleves = APIRouter(prefix="/api/eleves", tags=["eleves"])


@eleves.get("", response_model=list[EleveRead])
async def list_eleves(db: DbSession, _: CurrentUser):
    return await eleve_crud.list(db)


@eleves.get("/{eid}", response_model=EleveRead)
async def get_eleve(eid: int, db: DbSession, _: CurrentUser):
    return await eleve_crud.get(db, eid)


@eleves.post("", response_model=EleveRead, status_code=status.HTTP_201_CREATED,
             dependencies=[write_admin])
async def create_eleve(payload: EleveCreate, db: DbSession):
    return await eleve_crud.create(db, payload.model_dump())


@eleves.put("/{eid}", response_model=EleveRead, dependencies=[write_admin])
async def update_eleve(eid: int, payload: EleveUpdate, db: DbSession):
    return await eleve_crud.update(db, eid, payload.model_dump(exclude_unset=True))


@eleves.delete("/{eid}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[write_admin])
async def delete_eleve(eid: int, db: DbSession):
    await eleve_crud.delete(db, eid)


@eleves.post("/import", response_model=EleveImportResult, dependencies=[write_admin])
async def import_eleves(db: DbSession, file: UploadFile):
    """Import CSV transactionnel. Colonnes attendues :
    identifiant, nom, prenom, email, telephone (en-tete obligatoire).
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Fichier .csv attendu.",
        )
    raw = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))

    existants = set(
        (await db.execute(select(Eleve.identifiant))).scalars().all()
    )
    importes = 0
    ignores = 0
    erreurs: list[str] = []
    a_inserer: list[Eleve] = []

    for i, row in enumerate(reader, start=2):  # ligne 1 = en-tete
        ident = (row.get("identifiant") or "").strip()
        nom = (row.get("nom") or "").strip()
        prenom = (row.get("prenom") or "").strip()
        if not ident or not nom or not prenom:
            erreurs.append(f"Ligne {i} : identifiant, nom et prenom obligatoires.")
            continue
        if ident in existants:
            ignores += 1
            continue
        existants.add(ident)
        a_inserer.append(
            Eleve(
                identifiant=ident,
                nom=nom,
                prenom=prenom,
                email=(row.get("email") or "").strip() or None,
                telephone=(row.get("telephone") or "").strip() or None,
            )
        )
        importes += 1

    # Ecriture multi-lignes => une seule transaction (convention §6.3).
    if a_inserer:
        db.add_all(a_inserer)
        await db.commit()

    return EleveImportResult(importes=importes, ignores=ignores, erreurs=erreurs)
