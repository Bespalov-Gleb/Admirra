#!/bin/sh
set -eu

listen_address=${1:-}
case "$listen_address" in
  10.77.0.1:9100|10.77.0.2:9100) ;;
  *) echo "usage: $0 10.77.0.1:9100|10.77.0.2:9100" >&2; exit 64 ;;
esac

release_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export NODE_EXPORTER_LISTEN_ADDRESS=$listen_address

docker compose \
  --project-name admirra-observability-node \
  -f "$release_dir/compose.node-exporter.yml" \
  config --quiet
docker compose \
  --project-name admirra-observability-node \
  -f "$release_dir/compose.node-exporter.yml" \
  up -d

probe_file=$(mktemp)
trap 'rm -f "$probe_file"' EXIT HUP INT TERM
for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error --max-time 5 \
      --output "$probe_file" "http://${listen_address}/metrics" \
      && grep -q '^node_exporter_build_info' "$probe_file"; then
    exit 0
  fi
  sleep 1
done

echo "node-exporter did not become ready on ${listen_address}" >&2
exit 1
