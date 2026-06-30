"""Genere un hash bcrypt pour un mot de passe (remplace le placeholder du seed).

Usage :
    python -m scripts.gen_hash 'Admin_aaAA11**'
Puis coller le hash dans init/03_seed.sql a la place de $REMPLACER_PAR_UN_HASH_BCRYPT.
"""
from __future__ import annotations

import sys

from app.core.security import hash_password, validate_password_complexity


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.gen_hash '<mot_de_passe>'", file=sys.stderr)
        return 2
    pwd = sys.argv[1]
    if not validate_password_complexity(pwd):
        print(
            "Attention : ce mot de passe ne respecte pas la regle aaAA11** "
            "(>=8, 1 min, 1 maj, 1 chiffre, 1 special).",
            file=sys.stderr,
        )
    print(hash_password(pwd))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
