# CLAUDE.md — ClassroomObserv

> Fichier de contexte pour Claude Code. À placer à la **racine du dépôt**.
> Il décrit le projet, la stack figée, les conventions et les règles à **ne jamais
> enfreindre**. Lis-le entièrement avant toute tâche de dev.

---

## 1. Le projet

**ClassroomObserv** est une application de **supervision des salles de classe**
réparties sur plusieurs sites et bâtiments (hackathon de fin d'année ÉSTIAM Metz,
équipe E4/E5). Elle a deux casquettes :

1. **Administration** — gérer sites, bâtiments, salles, calculateurs (capteurs),
   personnels, classes, élèves.
2. **Supervision temps réel** — état réseau des capteurs (ping) + mesures des salles
   (température, luminosité, présence, porte/fenêtre) avec alertes (ex. salle restée
   ouverte après une heure définie).

La maquette d'origine était une appli WinForms ; **on la réécrit en application web**.

---

## 2. Stack (figée)

| Couche       | Choix                                                            |
|--------------|------------------------------------------------------------------|
| Front        | **React + Vite + TypeScript**, TanStack Query (data fetching), React Router |
| Back         | **FastAPI** (Python 3.12), **SQLAlchemy 2.0 async** + asyncpg, Pydantic v2 |
| Migrations   | **Alembic** (la BDD bootstrap reste en SQL, cf. §5)              |
| Auth         | JWT (python-jose) + hash mot de passe **bcrypt** (passlib)       |
| Base         | **PostgreSQL 16** (déjà conteneurisée, cf. §5)                   |
| Conteneurs   | **Docker / docker compose**                                      |

> Choix raisonnés mais modifiables : si on préfère Next.js (connu de l'équipe) au
> couple Vite+React, le reste du doc reste valable. Ne change pas de stack sans le
> signaler explicitement.

---

## 3. Structure cible du dépôt (monorepo)

```
classroomobserv/
├── CLAUDE.md                  # ce fichier
├── docker-compose.yml         # db (fait) → à étendre avec api + web
├── .env / .env.example        # secrets (jamais commiter .env)
├── db/
│   └── init/                  # scripts joués au 1er démarrage Postgres
│       ├── 01_schema.sql      # FAIT — source de vérité du schéma
│       ├── 02_roles.sh        # FAIT — crée le rôle applicatif restreint
│       └── 03_seed.sql        # FAIT — données de test
├── backend/                   # FastAPI
│   ├── app/
│   │   ├── main.py            # création de l'app + montage des routers
│   │   ├── core/              # config (settings env), sécurité (JWT/hash), session DB
│   │   ├── models/            # SQLAlchemy (miroir du schéma SQL)
│   │   ├── schemas/           # Pydantic (request/response)
│   │   ├── api/               # un router par module métier
│   │   ├── services/          # logique non triviale (ping, ingestion IoT, import/export .cro)
│   │   └── deps.py            # dépendances FastAPI (get_db, get_current_user…)
│   ├── alembic/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
└── frontend/                  # React + Vite + TS
    ├── src/
    │   ├── api/               # client HTTP + hooks par ressource
    │   ├── components/        # UI réutilisable
    │   ├── features/          # un dossier par module (sites, salles, supervision…)
    │   ├── hooks/
    │   ├── routes.tsx
    │   └── main.tsx
    ├── package.json
    └── Dockerfile
```

> **État actuel :** seul `db/` existe (Postgres + schéma + rôles + seed). Les dossiers
> `backend/` et `frontend/` sont **à scaffolder**. Les fichiers db sont actuellement
> dans un dossier `classroomobserv-db/` — les déplacer sous `db/` lors du scaffolding.

---

## 4. Commandes

```bash
# --- Base de données (déjà opérationnelle) ---
docker compose up -d db
docker compose logs -f db
docker compose down -v          # reset complet (rejoue les scripts init/)

# Connexion en tant que rôle APPLICATIF (jamais l'admin) :
docker exec -it classroomobserv-db psql -U classroom_app -d classroomobserv

# --- Backend (une fois scaffoldé) ---
cd backend
uv sync                          # ou pip install -e .
uvicorn app.main:app --reload    # API sur http://localhost:8000 , docs sur /docs
alembic revision --autogenerate -m "..."   # nouvelle migration
alembic upgrade head
pytest

# --- Frontend (une fois scaffoldé) ---
cd frontend
npm install
npm run dev                      # http://localhost:5173
npm run build
npm run lint
```

---

## 5. Base de données

### Connexion
L'application **se connecte avec le rôle restreint** `classroom_app`, **jamais** avec
`classroom_admin` (superuser). C'est une exigence de sécurité du cahier des charges
(id 1.S3 : « ne pas utiliser l'identifiant root »).

```
DATABASE_URL=postgresql+asyncpg://classroom_app:<APP_DB_PASSWORD>@localhost:5432/classroomobserv
```

`classroom_app` a uniquement SELECT/INSERT/UPDATE/DELETE. Toute opération DDL
(création de table, migration) passe par `classroom_admin` / Alembic.

### Schéma — source de vérité : `db/init/01_schema.sql`
Ne pas dupliquer le DDL ailleurs ; les modèles SQLAlchemy doivent **refléter** ce
fichier. Résumé des entités et des relations :

- `site` 1—N `batiment` 1—N `salle` 1—N `calculateur`
- `calculateur` 1—N `releve` (snapshot mesures) et 1—N `etat_calculateur_log` (ping)
- `personnel` N—N `salle` / `classe` (avec `matiere`) ; `personnel` 1—N `personnel_horaire`
- `classe` N—N `eleve` via `classe_eleve` ; `classe` → `personnel` (prof principal)
- `app_user` : authentification (rôles `utilisateur` / `administrateur`)

### Contraintes métier déjà posées en base (à re-valider aussi côté API)
- Unicité site `(nom, ville)` ; bâtiment `(site_id, nom)` ; salle `(batiment_id, nom)`.
- **Suppression d'un site/bâtiment interdite s'il a des enfants** (`ON DELETE RESTRICT`).
- `calculateur.ip_adresse` (type `INET`) et `mac_adresse` (type `MACADDR`) **uniques**.
- Élève : identifiant unique ; **un seul élève par classe et par année**
  (`UNIQUE(eleve_id, annee_scolaire)` sur `classe_eleve`).
- `releve` : `temperature` ∈ [-20, 50], `luminosite` ∈ [0, 1023] (specs capteurs Grove).
- Extension `pgcrypto` disponible pour chiffrer en AES les colonnes sensibles (RGPD).

---

## 6. Règles d'architecture — IMPORTANT

1. **Le ping et la collecte IoT se font côté BACKEND, jamais côté navigateur.**
   Le front ne peut ni pinger une IP ni parler à un Arduino. FastAPI ping les
   calculateurs en tâche de fond, écrit dans `etat_calculateur_log` à chaque
   **changement** d'état, et expose l'état courant. Le front fait du **polling**
   (TanStack Query `refetchInterval`) ou écoute un WebSocket.

2. **Ingestion des mesures** : un endpoint `POST /api/releves` reçoit les mesures des
   capteurs (Arduino réel ou simulateur) et les écrit dans `releve`. La visualisation
   lit la **dernière** mesure par calculateur (l'index `(calculateur_id, mesure_at DESC)`
   est là pour ça).

3. **Toute écriture multi-lignes est transactionnelle** (import CSV élèves, import
   `.cro`, affectations N—N). Utiliser `async with session.begin()`.

4. **Auth & droits** : tout endpoint d'administration exige le rôle `administrateur`.
   La visualisation/consultation est ouverte au rôle `utilisateur`. Dépendance
   FastAPI `get_current_user` + check de rôle.

---

## 7. Modules & surface API cible

Un router FastAPI par module, préfixe `/api`. Statuts HTTP corrects (201 création,
404 introuvable, 409 conflit d'unicité, 422 validation).

| Module             | Endpoints clés                                              | Statut |
|--------------------|-------------------------------------------------------------|--------|
| Auth               | `POST /api/auth/login`, `GET /api/auth/me`                  | à faire |
| Sites              | CRUD `/api/sites`                                           | à faire |
| Bâtiments          | CRUD `/api/batiments` (filtre `?site_id=`)                  | à faire |
| Salles             | CRUD `/api/salles` (+ liaison calculateurs)                 | à faire |
| Calculateurs       | CRUD `/api/calculateurs`                                    | à faire |
| Monitoring (ping)  | `GET /api/calculateurs/etat` (état courant + historique)    | à faire |
| Personnels         | CRUD `/api/personnels` (+ liaisons salles/classes/horaires) | à faire |
| Classes            | CRUD `/api/classes` (+ affectation élèves/personnels)       | à faire |
| Élèves             | CRUD `/api/eleves` + `POST /api/eleves/import` (CSV)         | à faire |
| Visualisation      | `GET /api/salles/{id}/mesures` (dernières mesures + état)   | à faire |
| Ingestion IoT      | `POST /api/releves`                                         | à faire |
| Export/Import .cro | `GET /api/config/export`, `POST /api/config/import`         | à faire |

Le format `.cro` est un **JSON versionné** (champ `schema_version` + horodatage).
L'import valide le schéma (Pydantic) puis écrase en **une transaction**, avec
sauvegarde préalable proposée.

---

## 8. Conventions de code

**Backend**
- Tout async (handlers, session DB, requêtes). Pas de SQLAlchemy synchrone.
- Modèles SQLAlchemy en `snake_case`, miroir exact des tables (mêmes noms).
- Schémas Pydantic v2 séparés : `XxxCreate`, `XxxUpdate`, `XxxRead`.
- Pas de logique métier dans les routers : extraire dans `services/`.
- Jamais de SQL concaténé à la main → ORM ou requêtes paramétrées (anti-injection).
- Validation : email, complexité mot de passe `aaAA11**` (≥1 min, 1 maj, 1 chiffre,
  1 spécial), formats IP/MAC (déléguer aux types Postgres + valider en entrée).

**Frontend**
- TypeScript strict. Types des réponses API dérivés du contrat (idéalement générés
  depuis l'OpenAPI de FastAPI).
- Données serveur via TanStack Query (cache + `refetchInterval` pour la supervision) ;
  pas de `useEffect`+`fetch` manuel pour le data fetching.
- Un dossier par module sous `features/`.

**Général**
- Pas de secret en dur : tout via `.env` (jamais commité ; `.env.example` à jour).
- Messages d'erreur clairs et explicites (le cahier des charges insiste là-dessus à
  chaque module : doublons, conflits, contraintes).
- Commits clairs ; branches par module/feature.

---

## 9. Sécurité & RGPD (exigences du cahier des charges)

À garder en tête et à matérialiser au fil du dev (utile aussi pour la soutenance) :

- Mots de passe : règle de complexité `aaAA11**` (validée à l'inscription).
- BDD : pas de superuser pour l'app (fait, cf. §5) ; chiffrement at-rest (volume
  chiffré en cloud / `pgcrypto` sur colonnes sensibles côté app).
- Échanges chiffrés (HTTPS/TLS en déploiement ; AES 128 bits min pour les données).
- RGPD : minimiser les données élèves, prévoir une charte ; chiffrer les contacts.
- En infra (hors dev pur, mais à documenter) : VLAN séparés, NSG, fail2ban, logs
  d'audit, CI/CD, environnement de test distinct de la prod.

---

## 10. État d'avancement

**Fait**
- [x] PostgreSQL conteneurisé (docker compose) avec healthcheck.
- [x] Schéma complet (`01_schema.sql`) couvrant toutes les entités + contraintes métier.
- [x] Rôle applicatif restreint `classroom_app` (non-superuser).
- [x] Données de seed pour tests.

**À faire (ordre conseillé)**
1. [ ] Scaffolder `backend/` (FastAPI + SQLAlchemy async + config + session DB).
2. [ ] Auth (login JWT, hash bcrypt, dépendance de rôle).
3. [ ] CRUD Administration dans l'ordre des dépendances : Sites → Bâtiments → Salles
       → Calculateurs → Personnels → Classes → Élèves (+ import CSV).
4. [ ] Scaffolder `frontend/` + écrans d'administration correspondants.
5. [ ] Supervision : service de ping backend + endpoint d'état + écran monitoring.
6. [ ] Ingestion IoT (endpoint + simulateur de mesures) + écran Visualisation salles.
7. [ ] Export/Import `.cro`.
8. [ ] Sécurité/RGPD, conteneurisation api+web, doc d'architecture, finitions.

---

## 11. Pièges à éviter

- ❌ Pinger ou interroger un capteur **depuis React** → toujours via le backend.
- ❌ Connecter l'app avec `classroom_admin` → utiliser `classroom_app`.
- ❌ Dupliquer le DDL : `01_schema.sql` est la source de vérité, les modèles le reflètent.
- ❌ Supprimer en cascade un site/bâtiment qui a des enfants (la base l'interdit déjà :
  gérer le 409 proprement côté API plutôt que de contourner la contrainte).
- ❌ Oublier les transactions sur les imports/affectations multi-lignes.
- ❌ Hash admin du seed laissé en placeholder (`$REMPLACER_PAR_UN_HASH_BCRYPT`) :
  générer un vrai hash avant toute démo.

---

## 12. Question ouverte à trancher avec le client/formateur

Un calculateur appartient-il à **une seule** salle (hypothèse actuelle, `salle_id` sur
`calculateur`) ou peut-il être partagé entre salles ? Si partagé, passer en table de
liaison N—N `salle_calculateur`. Ça ne change qu'une partie du schéma et des modèles.
