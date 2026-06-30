"""CRUD de la hierarchie : sites, batiments, salles, calculateurs.

Lecture ouverte a tout utilisateur authentifie ; ecriture reservee aux
administrateurs (dependance require_admin au niveau du router).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.deps import CurrentUser, DbSession, require_admin
from app.models import Batiment, Calculateur, Salle, Site
from app.schemas.structure import (
    BatimentCreate,
    BatimentRead,
    BatimentUpdate,
    CalculateurCreate,
    CalculateurRead,
    CalculateurUpdate,
    SalleCreate,
    SalleRead,
    SalleUpdate,
    SiteCreate,
    SiteRead,
    SiteUpdate,
)
from app.services.crud import CRUD

# Tout endpoint d'ecriture exige le role administrateur.
write_admin = Depends(require_admin)

site_crud = CRUD(Site)
batiment_crud = CRUD(Batiment)
salle_crud = CRUD(Salle)
calculateur_crud = CRUD(Calculateur)


# ============================= SITES =============================
sites = APIRouter(prefix="/api/sites", tags=["sites"])


@sites.get("", response_model=list[SiteRead])
async def list_sites(db: DbSession, _: CurrentUser):
    return await site_crud.list(db)


@sites.get("/{site_id}", response_model=SiteRead)
async def get_site(site_id: int, db: DbSession, _: CurrentUser):
    return await site_crud.get(db, site_id)


@sites.post("", response_model=SiteRead, status_code=status.HTTP_201_CREATED,
            dependencies=[write_admin])
async def create_site(payload: SiteCreate, db: DbSession):
    return await site_crud.create(db, payload.model_dump())


@sites.put("/{site_id}", response_model=SiteRead, dependencies=[write_admin])
async def update_site(site_id: int, payload: SiteUpdate, db: DbSession):
    return await site_crud.update(db, site_id, payload.model_dump(exclude_unset=True))


@sites.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT,
              dependencies=[write_admin])
async def delete_site(site_id: int, db: DbSession):
    await site_crud.delete(db, site_id)


# =========================== BATIMENTS ===========================
batiments = APIRouter(prefix="/api/batiments", tags=["batiments"])


@batiments.get("", response_model=list[BatimentRead])
async def list_batiments(db: DbSession, _: CurrentUser, site_id: int | None = None):
    return await batiment_crud.list(db, filters={"site_id": site_id})


@batiments.get("/{batiment_id}", response_model=BatimentRead)
async def get_batiment(batiment_id: int, db: DbSession, _: CurrentUser):
    return await batiment_crud.get(db, batiment_id)


@batiments.post("", response_model=BatimentRead, status_code=status.HTTP_201_CREATED,
                dependencies=[write_admin])
async def create_batiment(payload: BatimentCreate, db: DbSession):
    return await batiment_crud.create(db, payload.model_dump())


@batiments.put("/{batiment_id}", response_model=BatimentRead, dependencies=[write_admin])
async def update_batiment(batiment_id: int, payload: BatimentUpdate, db: DbSession):
    return await batiment_crud.update(
        db, batiment_id, payload.model_dump(exclude_unset=True)
    )


@batiments.delete("/{batiment_id}", status_code=status.HTTP_204_NO_CONTENT,
                  dependencies=[write_admin])
async def delete_batiment(batiment_id: int, db: DbSession):
    await batiment_crud.delete(db, batiment_id)


# ============================= SALLES ============================
salles = APIRouter(prefix="/api/salles", tags=["salles"])


@salles.get("", response_model=list[SalleRead])
async def list_salles(db: DbSession, _: CurrentUser, batiment_id: int | None = None):
    return await salle_crud.list(db, filters={"batiment_id": batiment_id})


@salles.get("/{salle_id}", response_model=SalleRead)
async def get_salle(salle_id: int, db: DbSession, _: CurrentUser):
    return await salle_crud.get(db, salle_id)


@salles.post("", response_model=SalleRead, status_code=status.HTTP_201_CREATED,
             dependencies=[write_admin])
async def create_salle(payload: SalleCreate, db: DbSession):
    return await salle_crud.create(db, payload.model_dump())


@salles.put("/{salle_id}", response_model=SalleRead, dependencies=[write_admin])
async def update_salle(salle_id: int, payload: SalleUpdate, db: DbSession):
    return await salle_crud.update(db, salle_id, payload.model_dump(exclude_unset=True))


@salles.delete("/{salle_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[write_admin])
async def delete_salle(salle_id: int, db: DbSession):
    await salle_crud.delete(db, salle_id)


# ========================== CALCULATEURS =========================
calculateurs = APIRouter(prefix="/api/calculateurs", tags=["calculateurs"])


@calculateurs.get("", response_model=list[CalculateurRead])
async def list_calculateurs(db: DbSession, _: CurrentUser, salle_id: int | None = None):
    return await calculateur_crud.list(db, filters={"salle_id": salle_id})


@calculateurs.get("/{calc_id}", response_model=CalculateurRead)
async def get_calculateur(calc_id: int, db: DbSession, _: CurrentUser):
    return await calculateur_crud.get(db, calc_id)


@calculateurs.post("", response_model=CalculateurRead, status_code=status.HTTP_201_CREATED,
                   dependencies=[write_admin])
async def create_calculateur(payload: CalculateurCreate, db: DbSession):
    return await calculateur_crud.create(db, payload.model_dump())


@calculateurs.put("/{calc_id}", response_model=CalculateurRead, dependencies=[write_admin])
async def update_calculateur(calc_id: int, payload: CalculateurUpdate, db: DbSession):
    return await calculateur_crud.update(
        db, calc_id, payload.model_dump(exclude_unset=True)
    )


@calculateurs.delete("/{calc_id}", status_code=status.HTTP_204_NO_CONTENT,
                     dependencies=[write_admin])
async def delete_calculateur(calc_id: int, db: DbSession):
    await calculateur_crud.delete(db, calc_id)
