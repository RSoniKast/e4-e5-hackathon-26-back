"""Import en masse des données de la base depuis des fichiers CSV.

Charge un CSV par entité (dossier ./data par défaut) dans l'ordre des dépendances,
le tout dans UNE seule transaction (convention §6.3 : écritures multi-lignes
transactionnelles). Réinsère les identifiants explicites du CSV puis recale les
séquences SERIAL.

Usage :
    python -m scripts.import_csv                 # insère (ignore les doublons de PK)
    python -m scripts.import_csv --truncate      # vide d'abord les tables (jeu propre)
    python -m scripts.import_csv --data ./data   # dossier CSV personnalisé

En conteneur :
    docker compose exec api python -m scripts.import_csv --truncate
"""
from __future__ import annotations

import argparse
import asyncio
import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import Base, SessionLocal
from app.models import (
    Batiment,
    Calculateur,
    Classe,
    ClasseEleve,
    Eleve,
    Personnel,
    PersonnelClasse,
    Salle,
    Site,
)

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _to_int(v: str) -> int | None:
    return int(v) if v not in ("", None) else None


def _to_float(v: str) -> float | None:
    return float(v) if v not in ("", None) else None


def _to_time(v: str):
    return datetime.strptime(v, "%H:%M").time() if v not in ("", None) else None


def _to_str(v: str) -> str | None:
    v = (v or "").strip()
    return v or None


# (fichier CSV, modèle, {colonne: convertisseur}) — dans l'ORDRE des dépendances FK.
TABLES: list[tuple[str, type[Base], dict[str, Callable[[str], Any]]]] = [
    ("sites.csv", Site, {
        "id": _to_int, "nom": _to_str, "adresse": _to_str, "ville": _to_str,
        "code_postal": _to_str, "latitude": _to_float, "longitude": _to_float,
    }),
    ("batiments.csv", Batiment, {
        "id": _to_int, "site_id": _to_int, "nom": _to_str,
    }),
    ("salles.csv", Salle, {
        "id": _to_int, "batiment_id": _to_int, "nom": _to_str,
        "capacite": _to_int, "heure_fermeture": _to_time,
    }),
    ("calculateurs.csv", Calculateur, {
        "id": _to_int, "salle_id": _to_int, "nom": _to_str,
        "ip_adresse": _to_str, "mac_adresse": _to_str,
    }),
    ("personnels.csv", Personnel, {
        "id": _to_int, "identifiant": _to_str, "nom": _to_str,
        "prenom": _to_str, "email": _to_str,
    }),
    ("classes.csv", Classe, {
        "id": _to_int, "nom": _to_str, "niveau": _to_str,
        "annee_scolaire": _to_str, "professeur_principal_id": _to_int,
    }),
    ("eleves.csv", Eleve, {
        "id": _to_int, "identifiant": _to_str, "nom": _to_str,
        "prenom": _to_str, "email": _to_str, "telephone": _to_str,
    }),
    ("classe_eleve.csv", ClasseEleve, {
        "classe_id": _to_int, "eleve_id": _to_int, "annee_scolaire": _to_str,
    }),
    ("personnel_classe.csv", PersonnelClasse, {
        "personnel_id": _to_int, "classe_id": _to_int, "matiere": _to_str,
    }),
]

# Tables à séquence SERIAL dont il faut recaler le compteur après insert d'ids explicites.
SERIAL_TABLES = ["site", "batiment", "salle", "calculateur", "personnel", "classe", "eleve"]


def _read_csv(path: Path, converters: dict[str, Callable[[str], Any]]) -> list[dict[str, Any]]:
    if not path.exists():
        print(f"  (ignoré, absent : {path.name})")
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = []
        for raw in reader:
            rows.append({col: conv(raw.get(col, "")) for col, conv in converters.items()})
        return rows


async def run(data_dir: Path, truncate: bool) -> None:
    async with SessionLocal() as db:
        async with db.begin():  # transaction unique
            if truncate:
                # Le rôle applicatif n'a pas TRUNCATE : on DELETE en ordre inverse
                # des dépendances (les liaisons CASCADE/SET NULL se gèrent seules).
                print("Vidage des tables (DELETE en ordre inverse) :")
                for filename, model, _ in reversed(TABLES):
                    await db.execute(text(f"DELETE FROM {model.__tablename__}"))
                    print(f"  - {model.__tablename__}")

            for filename, model, converters in TABLES:
                rows = _read_csv(data_dir / filename, converters)
                if not rows:
                    continue
                stmt = pg_insert(model).on_conflict_do_nothing()
                await db.execute(stmt, rows)
                print(f"  {model.__tablename__:18} {len(rows):3} ligne(s)")

            # Recaler les séquences sur le max(id) inséré.
            for table in SERIAL_TABLES:
                await db.execute(
                    text(
                        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                        f"GREATEST((SELECT COALESCE(MAX(id), 0) FROM {table}), 1))"
                    )
                )
    print("Import terminé.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import CSV -> base ClassroomObserv")
    parser.add_argument("--data", default=str(DEFAULT_DATA_DIR),
                        help="dossier contenant les CSV (défaut : ./data)")
    parser.add_argument("--truncate", action="store_true",
                        help="vide les tables avant import (jeu de données propre)")
    args = parser.parse_args()

    data_dir = Path(args.data)
    if not data_dir.is_dir():
        print(f"Dossier introuvable : {data_dir}")
        return 1
    asyncio.run(run(data_dir, args.truncate))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
