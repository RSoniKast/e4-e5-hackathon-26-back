"""Tests de fumee — ne necessitent pas de base Postgres.

Couvrent : montage de l'app, route /health, presence des endpoints clefs,
regles de securite (complexite mot de passe, aller-retour JWT).
"""
from __future__ import annotations

import httpx
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    validate_password_complexity,
)
from app.main import app


@pytest.mark.asyncio
async def test_health():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_routes_montees():
    paths = set(app.openapi()["paths"].keys())
    for expected in (
        "/api/auth/login",
        "/api/auth/me",
        "/api/sites",
        "/api/calculateurs/etat",
        "/api/releves",
        "/api/salles/{salle_id}/mesures",
        "/api/eleves/import",
    ):
        assert expected in paths, f"route manquante : {expected}"


@pytest.mark.parametrize(
    "pwd,ok",
    [
        ("Admin_aaAA11**", True),
        ("aaAA11**", True),
        ("motdepasse", False),   # pas de maj/chiffre/special
        ("Court1*", False),       # < 8
        ("SANSCHIFFRE**aa", False),
    ],
)
def test_complexite_mot_de_passe(pwd, ok):
    assert validate_password_complexity(pwd) is ok


def test_jwt_round_trip():
    token = create_access_token(subject="alice", role="administrateur")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "alice"
    assert payload["role"] == "administrateur"


def test_jwt_invalide():
    assert decode_access_token("pas-un-token") is None
