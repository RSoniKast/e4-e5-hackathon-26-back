#!/bin/bash
# =====================================================================
# Prepare la REPLICATION en streaming (primaire -> db_replica).
# Joue au 1er demarrage du primaire (volume pgdata vide), AVANT 01_schema.sql.
#   - cree le role de replication "replicator"
#   - autorise les connexions de replication dans pg_hba.conf
# $REPLICATION_PASSWORD vient de docker-compose (.env).
# =====================================================================
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '${REPLICATION_PASSWORD}';
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END
    \$\$;
EOSQL

# Autorise le standby a se connecter en replication (le reseau docker est prive).
# Ces lignes sont lues par le serveur "definitif" qui demarre apres les scripts init.
{
    echo "host replication replicator all scram-sha-256"
    echo "host all         all        all scram-sha-256"
} >> "$PGDATA/pg_hba.conf"

echo "Replication preparee : role 'replicator' cree, pg_hba ouvert."
