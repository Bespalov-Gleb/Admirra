#!/bin/sh
set -eu

secret_dir=/etc/admirra/monitoring
password_file=$secret_dir/postgres_password
user_file=$secret_dir/postgres_user
uri_file=$secret_dir/postgres_uri

install -d -m 0700 "$secret_dir"
if [ ! -s "$password_file" ]; then
  umask 077
  openssl rand -base64 36 | tr -d '\n' >"$password_file"
fi
printf '%s\n' admirra_monitor >"$user_file"
printf '%s\n' 'db:5432/saas_project?sslmode=disable' >"$uri_file"

password=$(cat "$password_file")
docker exec -i \
  -e ADMIRRA_MONITOR_PASSWORD="$password" \
  admirra-db-1 \
  psql -v ON_ERROR_STOP=1 -U postgres -d saas_project <<'SQL'
\getenv monitor_password ADMIRRA_MONITOR_PASSWORD
SELECT format(
  'CREATE ROLE admirra_monitor LOGIN PASSWORD %L CONNECTION LIMIT 2',
  :'monitor_password'
) WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'admirra_monitor') \gexec
SELECT format(
  'ALTER ROLE admirra_monitor WITH LOGIN PASSWORD %L CONNECTION LIMIT 2',
  :'monitor_password'
) \gexec
ALTER ROLE admirra_monitor SET statement_timeout = '5s';
ALTER ROLE admirra_monitor SET default_transaction_read_only = on;
GRANT CONNECT ON DATABASE saas_project TO admirra_monitor;
GRANT pg_monitor TO admirra_monitor;
SQL
unset password

chown 65534:65534 "$password_file" "$user_file" "$uri_file"
chmod 0400 "$password_file" "$user_file" "$uri_file"
