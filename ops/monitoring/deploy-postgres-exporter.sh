#!/bin/sh
set -eu

release_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
for secret in postgres_uri postgres_user postgres_password; do
  test -s "/etc/admirra/monitoring/${secret}"
done

docker compose \
  --project-name admirra-observability-postgres \
  -f "$release_dir/compose.postgres-exporter.yml" \
  config --quiet
docker compose \
  --project-name admirra-observability-postgres \
  -f "$release_dir/compose.postgres-exporter.yml" \
  up -d

probe_file=$(mktemp)
trap 'rm -f "$probe_file"' EXIT HUP INT TERM
for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error --max-time 5 \
      --output "$probe_file" http://127.0.0.1:9187/metrics \
      && grep -q '^pg_up 1' "$probe_file"; then
    exit 0
  fi
  sleep 1
done

echo "postgres-exporter did not become ready" >&2
exit 1
