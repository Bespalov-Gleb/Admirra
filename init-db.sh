#!/bin/bash
set -e

# This script runs during DB initialization
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    ALTER USER postgres WITH PASSWORD 'postgres_password';
    GRANT ALL PRIVILEGES ON DATABASE saas_project TO postgres;
EOSQL

echo "Database initialization complete. Password set successfully."

