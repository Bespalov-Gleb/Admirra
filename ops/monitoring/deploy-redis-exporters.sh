#!/bin/sh
set -eu

release_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
for secret in redis_broker_passwords.json redis_cache_passwords.json; do
  test -s "/etc/admirra/monitoring/${secret}"
done

docker compose \
  --project-name admirra-observability-redis \
  -f "$release_dir/compose.redis-exporters.yml" \
  config --quiet
docker compose \
  --project-name admirra-observability-redis \
  -f "$release_dir/compose.redis-exporters.yml" \
  up -d --force-recreate

for port in 9121 9122; do
  probe_file=$(mktemp)
  ready=0
  for attempt in $(seq 1 30); do
    if curl --fail --silent --show-error --max-time 5 \
        --output "$probe_file" "http://10.77.0.2:${port}/metrics" \
        && grep -q '^redis_up 1' "$probe_file"; then
      ready=1
      break
    fi
    sleep 1
  done
  rm -f "$probe_file"
  if [ "$ready" -ne 1 ]; then
    echo "redis_exporter on port ${port} did not become ready" >&2
    exit 1
  fi
done
