# Déploiement sur une VM Azure (tout en Docker)

Ce guide déploie **ClassroomObserv** sur une **machine virtuelle Azure**, en lançant
l'intégralité de la stack via `docker compose` : frontend Next.js + API FastAPI +
PostgreSQL **primaire** + PostgreSQL **réplica**, le tout derrière un reverse proxy
**Caddy** (point d'entrée unique sur le port 80).

> Approche choisie : « tout en Docker » sur une VM, fidèle à l'environnement local.
> Alternative « managée » (App Service for Containers + Azure Database for PostgreSQL) :
> plus robuste en prod mais la base n'est plus en conteneur. Voir la fin du document.

---

## 1. Architecture déployée

```
                 VM Azure (Ubuntu + Docker)
   Internet ──▶ :80  caddy ──/api/*──▶ api (FastAPI) ──▶ db (Postgres PRIMAIRE)
                       │                                       │ streaming WAL
                       │                                       ▼
                       └────── /* ─────▶ frontend (Next.js)   db_replica (STANDBY, R/O)
```

- **caddy** : reverse proxy, **seul port exposé (80)**. Route `/api/*` vers l'API et le
  reste vers le frontend → appels **same-origin**, pas de CORS.
- **frontend** : app Next.js (sous-module git `./frontend`).
- **api** : FastAPI, se connecte au primaire (`db:5432`).
- **db** : primaire, reçoit toutes les écritures.
- **db_replica** : se clone du primaire au 1er démarrage puis suit le flux WAL en continu
  (redondance temps réel). En lecture seule ; secours en cas de perte du primaire.

---

## 2. Prérequis & accès Azure

L'accès Azure passe par un **abonnement (Subscription)** et le contrôle de rôle (RBAC) :

1. Le propriétaire de l'abonnement crée un **Resource Group** (ex. `rg-classroomobserv`).
2. Il t'ajoute avec ton e-mail (compte Microsoft/Entra ID) en rôle **Contributor** sur ce
   resource group : *Resource group → Access control (IAM) → Add role assignment*.
3. Tu te connectes sur **https://portal.azure.com** ou via la CLI :

```bash
# Installer la CLI Azure si besoin : https://learn.microsoft.com/cli/azure/install-azure-cli
az login
az account set --subscription "<NOM_OU_ID_DE_LA_SUBSCRIPTION>"
```

---

## 3. Créer la VM

### Variables

```bash
RG=rg-classroomobserv
LOC=francecentral
VM=classroomobserv-vm
ADMIN=azureuser
```

### Création (Ubuntu 22.04, clé SSH générée automatiquement)

```bash
az group create -n $RG -l $LOC

az vm create \
  -g $RG -n $VM \
  --image Ubuntu2204 \
  --size Standard_B2s \
  --admin-username $ADMIN \
  --generate-ssh-keys \
  --public-ip-sku Standard
```

> `Standard_B2s` (2 vCPU / 4 Go) suffit pour une démo. La commande affiche l'**IP publique**
> (`publicIpAddress`) — note-la.

### Ouvrir les ports (NSG)

```bash
# Le proxy Caddy sert le front ET l'API sur le port 80 (un seul port suffit).
az vm open-port -g $RG -n $VM --port 80  --priority 100
az vm open-port -g $RG -n $VM --port 443 --priority 110   # pour le HTTPS (domaine) plus tard
```

> Le port **22 (SSH)** est déjà ouvert par `az vm create`. **N'ouvre PAS** 5432/5434
> (bases) ni 8000/3000 (api/front internes) : tout passe par Caddy sur le 80.

---

## 4. Installer Docker sur la VM

```bash
ssh $ADMIN@<IP_PUBLIQUE>

# sur la VM :
sudo apt-get update
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker            # ou se reconnecter pour appliquer le groupe
docker compose version   # vérifier (plugin v2 fourni par get.docker.com)
```

---

## 5. Déployer la stack

```bash
# sur la VM — --recurse-submodules récupère AUSSI le frontend (sous-module)
git clone --recurse-submodules https://github.com/RSoniKast/e4-e5-hackathon-26-back.git
cd e4-e5-hackathon-26-back

cp .env.example .env
nano .env        # ⚠️ changer TOUS les secrets (voir ci-dessous)

docker compose up -d --build      # build db + replica + api + frontend + caddy
docker compose ps
```

> Déjà cloné sans les sous-modules ? `git submodule update --init --recursive` avant le build.

### Secrets à modifier impérativement dans `.env`

| Variable | Action |
|----------|--------|
| `POSTGRES_PASSWORD` | mot de passe admin Postgres — **fort, unique** |
| `APP_DB_PASSWORD` | mot de passe du rôle applicatif `classroom_app` |
| `REPLICATION_PASSWORD` | mot de passe du rôle de réplication |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `PING_INTERVAL_SECONDS` | `0` en cloud (voir note supervision plus bas) |
| `NEXT_PUBLIC_API_URL` | **laisser vide** : le front appelle `/api` en same-origin via Caddy |
| `CORS_ORIGINS` | inutile en same-origin ; à ne renseigner que si accès cross-origin |

> Le schéma, le rôle restreint, la réplication et le seed sont appliqués
> **automatiquement** au 1er démarrage (scripts `init/`). Pas d'étape SQL manuelle,
> contrairement à une base managée.

### Créer le premier administrateur

```bash
docker compose exec api python -m scripts.create_admin admin '<MotDePasse_aaAA11**>'
```

### Vérifier

```bash
# depuis la VM
curl -s -o /dev/null -w "front: %{http_code}\n" http://localhost/     # 200 (via Caddy)
docker compose exec api curl -s http://localhost:8000/health          # {"status":"ok"}
# état de la réplication (doit afficher state=streaming) :
docker compose exec db psql -U classroom_admin -d classroomobserv \
  -c "SELECT client_addr, state, sync_state FROM pg_stat_replication;"
```

➜ **Application accessible sur `http://<IP_PUBLIQUE>/`** (front + API, port 80).

---

## 6. HTTPS automatique (Caddy est déjà dans la stack)

Le service **caddy** est déjà présent (point d'entrée port 80). Pour activer le HTTPS
avec un certificat Let's Encrypt automatique, il te faut un **nom de domaine** pointant
sur l'IP publique. Remplace alors la 1re ligne du `Caddyfile` :

```diff
- :80 {
+ mondomaine.fr {
      handle /api/* {
          reverse_proxy api:8000
      }
      handle {
          reverse_proxy frontend:3000
      }
  }
```

Puis `docker compose up -d caddy`. Caddy obtient et renouvelle le certificat tout seul ;
l'appli est alors sur `https://mondomaine.fr` (pense à ouvrir le **443** dans le NSG, déjà
fait à l'étape 3).

---

## 7. Exploitation

### Logs & cycle de vie

```bash
docker compose logs -f api
docker compose ps
docker compose pull && docker compose up -d --build   # mise à jour après un git pull
```

### Sauvegardes (à automatiser via cron)

```bash
# dump logique de la base
docker compose exec -T db pg_dump -U classroom_admin -d classroomobserv \
  | gzip > backup_$(date +%F).sql.gz
```

### Bascule en cas de perte du primaire (failover manuel)

Le réplica contient une copie à jour. Pour le promouvoir primaire :

```bash
# promouvoir le standby
docker compose exec db_replica psql -U classroom_admin -d classroomobserv \
  -c "SELECT pg_promote();"
```

Puis faire pointer l'API sur l'ancien réplica (changer l'hôte de `DATABASE_URL` vers
`db_replica` et `docker compose up -d api`). Pour une bascule **automatique**, il faudrait
un orchestrateur type **Patroni** / **repmgr** (hors périmètre hackathon).

---

## 8. Points d'attention spécifiques

- **Supervision réseau (ping) inopérante dans le cloud.** Le service de ping émet de
  l'ICMP sortant vers les **IP privées des capteurs** (LAN de l'école), injoignables
  depuis Azure → mettre `PING_INTERVAL_SECONDS=0`. L'**ingestion `POST /releves`**
  fonctionne (ce sont les capteurs/simulateur qui poussent vers l'API). Pour superviser
  de vrais capteurs : prévoir un **agent collecteur sur site** qui relaie vers le cloud.
- **Ne jamais exposer 5432/5434** sur Internet (NSG fermé par défaut, ne pas ouvrir).
- **Secrets** : ne pas committer `.env` (déjà dans `.gitignore`).
- **Persistance** : les données vivent dans les volumes Docker `pgdata` / `pgreplica`
  sur le disque de la VM. `docker compose down -v` les **supprime** — ne pas l'utiliser
  en prod.

---

## Annexe — Alternative managée (sans base en Docker)

Si vous préférez une base de données **managée** (sauvegardes, patchs, HA gérés par Azure) :

- **API** : Azure **App Service for Containers** (pousse l'image via Azure Container Registry).
- **Base** : Azure **Database for PostgreSQL – Flexible Server** (option *High Availability*
  pour la redondance, à la place du réplica Docker).
- Variables d'env dans *App Service → Configuration* ; `DATABASE_URL` pointe vers le
  Flexible Server avec `?ssl=require` ; `WEBSITES_PORT=8000`.
- ⚠️ Les scripts `init/` ne sont **pas** rejoués automatiquement → appliquer
  `01_schema.sql`, le rôle `classroom_app` et le seed **une fois** via `psql`.
