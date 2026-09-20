#!/bin/sh
set -eu

release_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=quay.io/prometheus/prometheus@sha256:332c2f43e7e389d74d3893b55bb02fbbd684208e681eeb604641d5d769c0fe2a

docker run --rm \
  --entrypoint /bin/promtool \
  -v "$release_dir/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  -v "$release_dir/rules.yml:/etc/prometheus/rules.yml:ro" \
  "$image" \
  check config /etc/prometheus/prometheus.yml

docker compose \
  --project-name admirra-observability \
  -f "$release_dir/compose.prometheus.yml" \
  config --quiet
docker compose \
  --project-name admirra-observability \
  -f "$release_dir/compose.prometheus.yml" \
  up -d

for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error --max-time 3 http://127.0.0.1:9090/-/ready >/dev/null 2>&1; then
    curl --fail --silent --show-error --max-time 5 \
      --request POST http://127.0.0.1:9090/-/reload >/dev/null
    exit 0
  fi
  sleep 1
done

echo "Prometheus did not become ready" >&2
exit 1
