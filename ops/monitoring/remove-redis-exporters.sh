#!/bin/sh
set -eu

release_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
docker compose \
  --project-name admirra-observability-redis \
  -f "$release_dir/compose.redis-exporters.yml" \
  down --remove-orphans
