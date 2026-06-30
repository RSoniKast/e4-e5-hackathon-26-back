"""Cree (ou met a jour) un utilisateur administrateur dans la base.

Usage :
    python -m scripts.create_admin <username> <mot_de_passe>
Le mot de passe doit respecter la regle de complexite aaAA11**.
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password, validate_password_complexity
from app.models import AppUser


async def _run(username: str, password: str) -> int:
    if not validate_password_complexity(password):
        print("Mot de passe trop faible (regle aaAA11**).", file=sys.stderr)
        return 1
    async with SessionLocal() as db:
        user = (
            await db.execute(select(AppUser).where(AppUser.username == username))
        ).scalar_one_or_none()
        if user is None:
            user = AppUser(username=username, password_hash=hash_password(password),
                           role="administrateur")
            db.add(user)
            action = "cree"
        else:
            user.password_hash = hash_password(password)
            user.role = "administrateur"
            action = "mis a jour"
        await db.commit()
    print(f"Administrateur '{username}' {action}.")
    return 0


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python -m scripts.create_admin <username> <mot_de_passe>",
              file=sys.stderr)
        return 2
    return asyncio.run(_run(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    raise SystemExit(main())
