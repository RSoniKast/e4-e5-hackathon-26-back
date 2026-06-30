#!/bin/bash
# =====================================================================
# Cree le role applicatif RESTREINT classroom_app.
# Exigence sujet (1.S3) : l'application ne se connecte PAS avec le superuser.
# Ce script tourne au 1er demarrage ; $APP_DB_PASSWORD vient de docker-compose.
# =====================================================================
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        CREATE ROLE classroom_app LOGIN PASSWORD '${APP_DB_PASSWORD}'
            NOSUPERUSER NOCREATEDB NOCREATEROLE;
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END
    \$\$;

    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO classroom_app;
    GRANT USAGE  ON SCHEMA public TO classroom_app;

    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES   IN SCHEMA public TO classroom_app;
    -- UPDATE sur les sequences = autorise setval() (recalage apres import d'ids explicites).
    GRANT USAGE, SELECT, UPDATE           ON ALL SEQUENCES IN SCHEMA public TO classroom_app;

    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO classroom_app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO classroom_app;
EOSQL

echo "Role applicatif 'classroom_app' cree (non-superuser)."
