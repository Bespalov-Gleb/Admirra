#!/bin/sh
set -eu

release_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
docker compose \
  --project-name admirra-alerting \
  -f "$release_dir/compose.alertmanager.yml" \
  down
