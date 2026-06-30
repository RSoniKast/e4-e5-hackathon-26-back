# e4-e5-hackathon-26-back

Backend **FastAPI** du projet **ClassroomObserv** : application de supervision de salles
de classe réparties sur plusieurs sites/bâtiments (hackathon de fin d'année ÉSTIAM Metz,
équipe E4/E5). Le frontend (React) est développé séparément par une autre équipe.

Deux casquettes :
1. **Administration** — sites, bâtiments, salles, calculateurs (capteurs), personnels, classes, élèves.
2. **Supervision temps réel** — état réseau des capteurs (ping côté backend) + mesures
   (température, luminosité, présence, porte/fenêtre) avec alertes.

> Contexte complet, stack figée et règles d'architecture : voir [`CLAUDE.md`](./CLAUDE.md).

---

## Stack

| Couche      | Choix |
|-------------|-------|
| Framework   | **FastAPI** (Python 3.12), tout en async |
| ORM         | **SQLAlchemy 2.0 async** + asyncpg |
| Validation  | **Pydantic v2** (+ pydantic-settings) |
| Auth        | **JWT** (python-jose) + **bcrypt** |
| Migrations  | **Alembic** (la base est bootstrappée en SQL, cf. `init/`) |
| Base        | **PostgreSQL 16** |
| Conteneurs  | **Docker** / docker compose |

---

## Structure du dépôt

```
.
├── app/
│   ├── main.py            # app FastAPI + CORS + handler 409 + montage des routers + tâche ping
│   ├── deps.py            # dépendances : get_session, get_current_user, require_admin
│   ├── core/
│   │   ├── config.py      # settings lues depuis .env (DATABASE_URL, JWT, CORS, ping)
│   │   ├── database.py    # engine SQLAlchemy async + fabrique de sessions
│   │   └── security.py    # hash bcrypt, JWT, validation complexité mot de passe
│   ├── models/            # modèles SQLAlchemy — MIROIR de init/01_schema.sql
│   ├── schemas/           # schémas Pydantic (XxxCreate / XxxUpdate / XxxRead)
│   ├── api/               # routers : auth, structure, people, monitoring
│   └── services/          # crud.py (CRUD générique) + ping.py (supervision réseau)
├── alembic/               # migrations (évolutions ultérieures du schéma)
├── scripts/               # gen_hash.py, create_admin.py
├── tests/                 # tests de fumée (sans Postgres)
├── init/                  # bootstrap Postgres (joué au 1er démarrage) :
│   ├── 01_schema.sql      #   schéma complet — SOURCE DE VÉRITÉ
│   ├── 02_roles.sh        #   crée le rôle applicatif restreint classroom_app
│   └── 03_seed.sql        #   données de test
├── docker-compose.yml     # services db + api
├── Dockerfile             # image de l'API
├── pyproject.toml         # dépendances (uv / pip)
└── .env.example           # variables d'environnement à copier en .env
```

---

## Prérequis

- **Docker** (Docker Desktop, ou **Colima** sur macOS).
- La commande de compose est `docker compose` (plugin v2) **ou** `docker-compose`
  (binaire standalone) selon l'installation. Les exemples ci-dessous utilisent
  `docker-compose` — adapter si besoin.
- Pour le dev local de l'API (option B) : **Python 3.12** et [`uv`](https://github.com/astral-sh/uv).

### macOS avec Colima

Si Docker est fourni par Colima, il faut le démarrer une fois :

```bash
colima start          # démarre la VM Docker
docker info           # vérifie que le démon répond
# ... travail ...
colima stop           # arrête la VM quand on a fini
```

---

## 1. Configuration

```bash
cp .env.example .env        # ajuster les secrets pour la prod
```

Variables clés (valeurs de dev par défaut dans `.env.example`) :

| Variable | Rôle |
|----------|------|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | rôle **admin** Postgres — init & migrations uniquement |
| `APP_DB_PASSWORD` | mot de passe du rôle **applicatif restreint** `classroom_app` |
| `DATABASE_URL` | chaîne de connexion de l'API (dev local depuis l'hôte → `localhost:5433`) |
| `JWT_SECRET` | secret de signature des tokens (générer : `openssl rand -hex 32`) |
| `CORS_ORIGINS` | origines front autorisées (séparées par des virgules) |
| `PING_INTERVAL_SECONDS` | intervalle de ping des calculateurs (`0` = désactivé) |

> **Ports** : Postgres est exposé sur **`localhost:5433`** côté hôte (le 5432 est
> souvent déjà occupé par un autre Postgres). En interne (réseau Docker), l'API joint
> toujours la base via `db:5432` — inchangé. L'API écoute sur **`localhost:8000`**.

> **Sécurité** : l'application se connecte **toujours** avec le rôle restreint
> `classroom_app` (jamais l'admin) — exigence du cahier des charges.

---

## 2. Lancer — tout en Docker (recommandé)

```bash
# (Colima : colima start  d'abord)

# Build + démarrage de la base ET de l'API
docker-compose up --build -d

# Vérifier que l'API répond
curl http://localhost:8000/health        # -> {"status":"ok"}

# Créer le premier administrateur
docker-compose exec api python -m scripts.create_admin admin 'Admin_aaAA11**'
```

➜ Documentation interactive (Swagger) : **http://localhost:8000/docs**

Gestion du cycle de vie :

```bash
docker-compose ps                  # état des conteneurs
docker-compose logs -f api         # logs de l'API
docker-compose logs -f db          # logs Postgres
docker-compose up -d --build api   # rebuild + relancer l'API après une modif de code
docker-compose restart api         # redémarrer l'API
docker-compose down                # arrêter
docker-compose down -v             # arrêter + RESET complet (rejoue init/ au prochain up)
```

---

## 3. Lancer — dev local (base en Docker, API en local avec reload)

```bash
docker-compose up -d db                       # PostgreSQL seul (exposé sur localhost:5433)

uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"

uvicorn app.main:app --reload                 # http://localhost:8000/docs

# (autre terminal) créer un admin
source .venv/bin/activate
python -m scripts.create_admin admin 'Admin_aaAA11**'
```

---

## Premier administrateur

Le seed `init/03_seed.sql` contient un **hash placeholder** à remplacer. Deux options :

```bash
# A) créer / mettre à jour un admin directement en base (le plus simple)
python -m scripts.create_admin admin 'Admin_aaAA11**'
#    en Docker :
docker-compose exec api python -m scripts.create_admin admin 'Admin_aaAA11**'

# B) générer un hash bcrypt à coller dans init/03_seed.sql (à la place du placeholder)
python -m scripts.gen_hash 'Admin_aaAA11**'
```

> Règle de complexité imposée (`aaAA11**`) : ≥ 8 caractères, au moins 1 minuscule,
> 1 majuscule, 1 chiffre et 1 caractère spécial.

---

## Authentification

```bash
# login (formulaire OAuth2) → renvoie un access_token JWT
curl -X POST http://localhost:8000/api/auth/login \
  -d 'username=admin&password=Admin_aaAA11**'

# appel d'un endpoint protégé
curl http://localhost:8000/api/auth/me -H "Authorization: Bearer <token>"
```

**Droits** : la lecture (GET) est ouverte à tout utilisateur authentifié ;
l'**écriture (POST/PUT/DELETE) est réservée au rôle `administrateur`**.

---

## Surface API (`/api`)

| Module        | Endpoints | Statuts |
|---------------|-----------|---------|
| Auth          | `POST /auth/login`, `GET /auth/me` | 200 / 401 |
| Sites         | CRUD `/sites` | 201 / 404 / 409 |
| Bâtiments     | CRUD `/batiments` (`?site_id=`) | 201 / 404 / 409 |
| Salles        | CRUD `/salles` (`?batiment_id=`) | 201 / 404 / 409 |
| Calculateurs  | CRUD `/calculateurs` (`?salle_id=`) | 201 / 404 / 409 |
| Monitoring    | `GET /calculateurs/etat` (état réseau courant) | 200 |
| Personnels    | CRUD `/personnels` + `/personnels/{id}/horaires` | 201 / 404 |
| Classes       | CRUD `/classes` + `/classes/{id}/eleves`, `/classes/{id}/personnels` | 201 / 404 |
| Élèves        | CRUD `/eleves` + `POST /eleves/import` (CSV) | 201 / 404 |
| Visualisation | `GET /salles/{id}/mesures` (dernière mesure + état + alerte) | 200 / 404 |
| Ingestion IoT | `POST /releves` (mesures capteurs) | 201 |

Conventions HTTP : **201** création, **404** introuvable, **409** conflit d'unicité ou
suppression interdite (site/bâtiment avec enfants), **422** validation.

---

## Migrations Alembic

La base est bootstrappée en SQL (`init/`). Alembic sert aux **évolutions ultérieures**
du schéma. **Lancer les migrations avec le rôle admin** (pas `classroom_app`) :

```bash
DATABASE_URL=postgresql+asyncpg://classroom_admin:<PWD>@localhost:5433/classroomobserv \
  alembic revision --autogenerate -m "description"
DATABASE_URL=postgresql+asyncpg://classroom_admin:<PWD>@localhost:5433/classroomobserv \
  alembic upgrade head
```

---

## Tests

```bash
source .venv/bin/activate
pytest        # tests de fumée : /health, présence des routes, complexité mdp, aller-retour JWT
```

Les tests de fumée ne nécessitent pas de base de données.

---

## Dépannage

- **`Bind for 0.0.0.0:5432 failed: port is already allocated`** — un autre Postgres
  occupe le 5432. La base est déjà mappée sur **5433** côté hôte ; vérifier qu'aucun
  autre service ne prend ce port (`lsof -iTCP:5433 -sTCP:LISTEN`).
- **`docker: unknown command: docker compose`** — utiliser `docker-compose` (binaire
  standalone) au lieu du plugin v2.
- **`Cannot connect to the Docker daemon`** — sur macOS avec Colima : `colima start`.
- **401 sur un endpoint d'écriture** — token absent/expiré, ou l'utilisateur n'a pas le
  rôle `administrateur`.

---

## Points encore ouverts

- Simulateur de mesures (alimente `POST /releves`) — à ajouter pour les démos.
- Export / import `.cro` (JSON versionné) — non implémenté.
- Sécurisation de `POST /releves` (clé d'API / mTLS) selon l'infra de déploiement.
- Question schéma : un calculateur appartient-il à **une seule** salle ou peut-il être
  partagé entre salles ? (cf. §12 de `CLAUDE.md`)
