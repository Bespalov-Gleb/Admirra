#!/bin/sh
set -eu

release_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
docker compose \
  --project-name admirra-observability-postgres \
  -f "$release_dir/compose.postgres-exporter.yml" \
  down --remove-orphans
