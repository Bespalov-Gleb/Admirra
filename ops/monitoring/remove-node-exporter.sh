#!/bin/sh
set -eu

release_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
docker compose \
  --project-name admirra-observability-node \
  -f "$release_dir/compose.node-exporter.yml" \
  down --remove-orphans
