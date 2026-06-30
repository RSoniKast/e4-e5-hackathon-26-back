"""Service de supervision reseau : ping des calculateurs cote BACKEND.

Regle d'archi §6.1 : le ping ne se fait JAMAIS depuis le navigateur. Cette tache
de fond ping chaque calculateur ayant une IP, et journalise dans
`etat_calculateur_log` UNIQUEMENT a chaque CHANGEMENT d'etat (en_ligne).
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Calculateur, EtatCalculateurLog

logger = logging.getLogger("classroomobserv.ping")


async def ping_host(ip: str, timeout: float = 1.0) -> bool:
    """Ping ICMP via la commande systeme (1 paquet). True si l'hote repond."""
    proc = await asyncio.create_subprocess_exec(
        "ping", "-c", "1", "-W", str(int(timeout)), ip,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    return await proc.wait() == 0


async def _last_known_state(db, calculateur_id: int) -> bool | None:
    stmt = (
        select(EtatCalculateurLog.en_ligne)
        .where(EtatCalculateurLog.calculateur_id == calculateur_id)
        .order_by(EtatCalculateurLog.change_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def run_ping_cycle() -> None:
    """Une campagne de ping sur tous les calculateurs ayant une IP."""
    async with SessionLocal() as db:
        calcs = (
            await db.execute(select(Calculateur).where(Calculateur.ip_adresse.isnot(None)))
        ).scalars().all()

        for calc in calcs:
            try:
                en_ligne = await ping_host(str(calc.ip_adresse))
            except Exception:  # pragma: no cover - ping indisponible
                logger.exception("Echec du ping de %s", calc.ip_adresse)
                continue
            precedent = await _last_known_state(db, calc.id)
            if precedent != en_ligne:  # on ne journalise que les changements
                db.add(EtatCalculateurLog(calculateur_id=calc.id, en_ligne=en_ligne))
        await db.commit()


async def ping_loop() -> None:
    """Boucle de fond, lancee au demarrage de l'app si PING_INTERVAL_SECONDS > 0."""
    interval = settings.ping_interval_seconds
    logger.info("Boucle de ping demarree (intervalle=%ss)", interval)
    while True:
        try:
            await run_ping_cycle()
        except Exception:  # pragma: no cover
            logger.exception("Erreur dans le cycle de ping")
        await asyncio.sleep(interval)
