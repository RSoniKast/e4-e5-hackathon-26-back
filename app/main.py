"""Point d'entree FastAPI : creation de l'app, CORS, handlers, montage des routers."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api import auth, monitoring, people, structure
from app.core.config import settings
from app.services.ping import ping_loop

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ping_task: asyncio.Task | None = None
    if settings.ping_interval_seconds > 0:
        ping_task = asyncio.create_task(ping_loop())
    try:
        yield
    finally:
        if ping_task is not None:
            ping_task.cancel()


app = FastAPI(
    title="ClassroomObserv API",
    version="0.1.0",
    description="Backend de supervision des salles de classe (hackathon E4/E5).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Violation de contrainte (unicite, FK RESTRICT...) => 409 explicite."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": (
                "Conflit de contrainte en base : doublon ou suppression interdite "
                "(un site/batiment avec des enfants ne peut etre supprime)."
            )
        },
    )


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Ordre IMPORTANT : monitoring (/api/calculateurs/etat) AVANT le CRUD calculateurs
# pour que "etat" ne soit pas interprete comme un {calc_id}.
app.include_router(auth.router)
app.include_router(monitoring.monitoring)        # /api/calculateurs/etat
app.include_router(monitoring.salle_mesures)     # /api/salles/{id}/mesures
app.include_router(monitoring.releves)           # /api/releves
app.include_router(structure.sites)
app.include_router(structure.batiments)
app.include_router(structure.salles)
app.include_router(structure.calculateurs)
app.include_router(people.personnels)
app.include_router(people.classes)
app.include_router(people.eleves)
