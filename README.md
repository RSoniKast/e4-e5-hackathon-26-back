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
├── scripts/               # gen_hash.py, create_admin.py, import_csv.py
├── data/                  # jeu de données CSV de démonstration (un fichier par entité)
├── tests/                 # tests de fumée (sans Postgres)
├── init/                  # bootstrap Postgres (joué au 1er démarrage) :
│   ├── 01_schema.sql      #   schéma complet — SOURCE DE VÉRITÉ
│   ├── 02_roles.sh        #   crée le rôle applicatif restreint classroom_app
│   └── 03_seed.sql        #   données de test
├── docker-compose.yml     # db (primaire) + db_replica + api + frontend + caddy (proxy)
├── Dockerfile             # image de l'API
├── Caddyfile              # reverse proxy : /api -> api, le reste -> frontend
├── frontend/              # SOUS-MODULE git (repo Next.js e4-e5-hackathon-26-front)
├── docs/
│   └── DEPLOIEMENT-AZURE.md  # guide de déploiement sur une VM Azure
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

## Architecture (docker compose)

```
Navigateur ──▶ :80  Caddy (reverse proxy)
                     ├─ /api/*  ──▶ api (FastAPI) ──▶ db (Postgres) ──▶ db_replica
                     └─ /*      ──▶ frontend (Next.js)
```

Le front (sous-module `frontend/`) appelle l'API en **same-origin** (`/api/...`) via Caddy :
pas de CORS, pas d'URL d'API figée. **Point d'entrée unique : http://localhost/** (port 80).

## 1. Configuration

> Le frontend est un **sous-module git**. Cloner le dépôt avec `--recurse-submodules` :
> ```bash
> git clone --recurse-submodules https://github.com/RSoniKast/e4-e5-hackathon-26-back.git
> # déjà cloné sans les sous-modules ? :
> git submodule update --init --recursive
> ```

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

> **Ports** : le Postgres **primaire** est exposé sur **`localhost:5433`** côté hôte
> (le 5432 est souvent déjà occupé par un autre Postgres), le **réplica** sur
> **`localhost:5434`**. En interne (réseau Docker), l'API joint toujours le primaire via
> `db:5432`. L'API écoute sur **`localhost:8000`**.

> **Redondance** : la stack lance un **réplica PostgreSQL** (`db_replica`) en réplication
> streaming depuis le primaire — copie des données en temps réel, en lecture seule, prête
> à être promue en cas de panne. Vérifier : `docker-compose exec db psql -U classroom_admin
> -d classroomobserv -c "SELECT state FROM pg_stat_replication;"` → `streaming`.

> **Sécurité** : l'application se connecte **toujours** avec le rôle restreint
> `classroom_app` (jamais l'admin) — exigence du cahier des charges.

---

## 2. Lancer — tout en Docker (recommandé)

```bash
# (Colima : colima start  d'abord)

# Build + démarrage de TOUTE la stack (db + replica + api + frontend + caddy)
docker-compose up --build -d

# Vérifier
curl http://localhost/api/../health 2>/dev/null; curl http://localhost:8000/health  # {"status":"ok"}
curl -s -o /dev/null -w "front: %{http_code}\n" http://localhost/                    # 200

# Créer le premier administrateur
docker-compose exec api python -m scripts.create_admin admin 'Admin_aaAA11**'
```

➜ **Application : http://localhost/** — Swagger de l'API : **http://localhost:8000/docs**

Gestion du cycle de vie :

```bash
docker-compose ps                       # état des conteneurs
docker-compose logs -f api              # logs de l'API
docker-compose logs -f frontend caddy   # logs front + proxy
docker-compose up -d --build frontend   # rebuild le front après un pull du sous-module
docker-compose down                     # arrêter
docker-compose down -v                  # arrêter + RESET complet (rejoue init/ au prochain up)
```

> **Mettre à jour le front** (nouveau commit sur le repo Next.js) :
> ```bash
> git submodule update --remote frontend   # récupère le dernier commit du front
> docker-compose up -d --build frontend
> ```

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

## Remplir la base depuis des CSV

Un jeu de données de démonstration est fourni dans `data/` (un CSV par entité) avec un
script d'import qui charge le tout dans le bon ordre, en une seule transaction.

```bash
# en local (venv) — --truncate vide d'abord les tables pour un jeu propre
python -m scripts.import_csv --truncate

# en Docker
docker-compose exec api python -m scripts.import_csv --truncate

# dossier CSV personnalisé
python -m scripts.import_csv --data ./mon_dossier
```

Fichiers : `sites.csv`, `batiments.csv`, `salles.csv`, `calculateurs.csv`,
`personnels.csv`, `classes.csv`, `eleves.csv`, `classe_eleve.csv`, `personnel_classe.csv`.
Les ids du CSV sont réutilisés tels quels (FK explicites), puis les séquences SERIAL sont
recalées pour que l'API continue à attribuer des ids sans collision.

> Pour importer **uniquement des élèves** via l'API (upload de fichier), utiliser plutôt
> `POST /api/eleves/import` (voir la table des endpoints).

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

## Déploiement

Guide complet de déploiement sur une **VM Azure** (toute la stack en Docker : API +
PostgreSQL primaire + réplica) : **[`docs/DEPLOIEMENT-AZURE.md`](docs/DEPLOIEMENT-AZURE.md)**.
Inclut la création de la VM, l'installation de Docker, l'ouverture des ports, le HTTPS via
Caddy, les sauvegardes et la procédure de bascule (failover).

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
