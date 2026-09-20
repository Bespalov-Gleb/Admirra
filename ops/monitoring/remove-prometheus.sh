#!/bin/sh
set -eu

release_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
docker compose \
  --project-name admirra-observability \
  -f "$release_dir/compose.prometheus.yml" \
  down --remove-orphans
