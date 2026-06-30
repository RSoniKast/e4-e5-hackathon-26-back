# Déploiement sur une VM Azure (tout en Docker)

Ce guide déploie **ClassroomObserv** sur une **machine virtuelle Azure**, en lançant
l'intégralité de la stack via `docker compose` : API FastAPI + PostgreSQL **primaire**
+ PostgreSQL **réplica** (redondance des données).

> Approche choisie : « tout en Docker » sur une VM, fidèle à l'environnement local.
> Alternative « managée » (App Service for Containers + Azure Database for PostgreSQL) :
> plus robuste en prod mais la base n'est plus en conteneur. Voir la fin du document.

---

## 1. Architecture déployée

```
                 VM Azure (Ubuntu + Docker)
   Internet ──▶ :443/:80 (Caddy, HTTPS)  ─┐
                                          ├─▶ api (FastAPI)  :8000
                                          │        │
                                          │        ▼ écritures + lectures
                                          │   db (Postgres PRIMAIRE)  :5432
                                          │        │ streaming WAL
                                          │        ▼
                                          └─▶ db_replica (Postgres STANDBY, lecture seule)
```

- **db** : primaire, reçoit toutes les écritures de l'API.
- **db_replica** : se clone du primaire au 1er démarrage puis suit le flux WAL en continu
  (redondance temps réel). En lecture seule ; sert de secours en cas de perte du primaire.
- **api** : se connecte au primaire (`db:5432`).

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
# HTTP/HTTPS pour l'accès web (Caddy fera le HTTPS)
az vm open-port -g $RG -n $VM --port 80  --priority 100
az vm open-port -g $RG -n $VM --port 443 --priority 110
# (optionnel) accès direct à l'API sans reverse proxy
az vm open-port -g $RG -n $VM --port 8000 --priority 120
```

> Le port **22 (SSH)** est déjà ouvert par `az vm create`. **N'ouvre pas** 5432/5434
> (les bases ne doivent pas être exposées sur Internet).

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
# sur la VM
git clone https://github.com/RSoniKast/e4-e5-hackathon-26-back.git
cd e4-e5-hackathon-26-back

cp .env.example .env
nano .env        # ⚠️ changer TOUS les secrets (voir ci-dessous)

docker compose up -d --build
docker compose ps
```

### Secrets à modifier impérativement dans `.env`

| Variable | Action |
|----------|--------|
| `POSTGRES_PASSWORD` | mot de passe admin Postgres — **fort, unique** |
| `APP_DB_PASSWORD` | mot de passe du rôle applicatif `classroom_app` |
| `REPLICATION_PASSWORD` | mot de passe du rôle de réplication |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `CORS_ORIGINS` | URL **déployée** du front (pas localhost) |
| `PING_INTERVAL_SECONDS` | `0` en cloud (voir note supervision plus bas) |

> Le schéma, le rôle restreint, la réplication et le seed sont appliqués
> **automatiquement** au 1er démarrage (scripts `init/`). Pas d'étape SQL manuelle,
> contrairement à une base managée.

### Créer le premier administrateur

```bash
docker compose exec api python -m scripts.create_admin admin '<MotDePasse_aaAA11**>'
```

### Vérifier

```bash
curl http://localhost:8000/health                       # {"status":"ok"}
# état de la réplication (doit afficher state=streaming) :
docker compose exec db psql -U classroom_admin -d classroomobserv \
  -c "SELECT client_addr, state, sync_state FROM pg_stat_replication;"
```

API accessible sur `http://<IP_PUBLIQUE>:8000/docs` (si le port 8000 est ouvert).

---

## 6. HTTPS automatique avec Caddy (recommandé)

Pour servir l'API en HTTPS avec un certificat Let's Encrypt automatique, ajoute un
reverse proxy **Caddy**. Il te faut un **nom de domaine** pointant sur l'IP publique.

`Caddyfile` à la racine :

```
api.mondomaine.fr {
    reverse_proxy api:8000
}
```

Bloc à ajouter dans `docker-compose.yml` (service `caddy`) :

```yaml
  caddy:
    image: caddy:2
    restart: unless-stopped
    depends_on: [api]
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
# ... et dans la section volumes: ajouter  caddy_data:  et  caddy_config:
```

Caddy obtient et renouvelle le certificat tout seul. L'API est alors sur
`https://api.mondomaine.fr` (et tu peux refermer le port 8000 dans le NSG).

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
