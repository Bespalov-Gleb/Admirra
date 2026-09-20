#!/bin/bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "capture_release_manifest.sh must run as root" >&2
  exit 2
fi

project_dir=${ADMIRRA_PROJECT_DIR:-/root/Admirra}
database_container=${ADMIRRA_DB_CONTAINER:-admirra-db-1}
output_dir=${ADMIRRA_RELEASE_MANIFEST_DIR:-/etc/admirra/release-manifests}
output_file=$output_dir/current.txt

install -d -o root -g root -m 0700 "$output_dir"
temporary=$(mktemp "$output_dir/.current.XXXXXX")
cleanup() {
  rm -f "$temporary"
}
trap cleanup EXIT HUP INT TERM
chmod 0600 "$temporary"

generated_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
git_revision=unavailable
git_dirty=unknown
if git -C "$project_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git_revision=$(git -C "$project_dir" rev-parse HEAD)
  if test -n "$(git -C "$project_dir" status --porcelain --untracked-files=no)"; then
    git_dirty=true
  else
    git_dirty=false
  fi
fi

schema_revision=$(docker exec "$database_container" psql -U postgres -d saas_project -Atc \
  "SELECT version_num FROM alembic_version ORDER BY version_num LIMIT 1")
test -n "$schema_revision"

{
  printf 'format=admirra-release-manifest-v1\n'
  printf 'generated_at=%s\n' "$generated_at"
  printf 'source_host=%s\n' "$(hostname)"
  printf 'git_revision=%s\n' "$git_revision"
  printf 'git_tracked_dirty=%s\n' "$git_dirty"
  printf 'schema_revision=%s\n' "$schema_revision"
  printf '[containers]\n'
  docker container ls --all --format '{{.Names}}' | LC_ALL=C sort | while IFS= read -r container; do
    docker inspect "$container" --format \
      '{{.Name}}|configured_image={{.Config.Image}}|image_id={{.Image}}|restart={{.HostConfig.RestartPolicy.Name}}|state={{.State.Status}}'
  done
  printf '[configuration_hashes]\n'
  for path in \
    "$project_dir/.env" \
    "$project_dir/docker-compose.yml" \
    "$project_dir/nginx.conf" \
    /etc/admirra \
    /etc/nginx \
    /etc/wireguard \
    /etc/letsencrypt; do
    if [ -f "$path" ]; then
      printf '%s|sha256=%s\n' "$path" "$(sha256sum "$path" | cut -d ' ' -f 1)"
    elif [ -d "$path" ]; then
      if [ "$path" = /etc/admirra ]; then
        digest=$(
          find "$path" -xdev -path "$output_dir" -prune -o -type f -print0 \
          | LC_ALL=C sort -z \
          | xargs -0 -r sha256sum \
          | sha256sum \
          | cut -d ' ' -f 1
        )
      else
        digest=$(
          find "$path" -xdev -type f -print0 \
          | LC_ALL=C sort -z \
          | xargs -0 -r sha256sum \
          | sha256sum \
          | cut -d ' ' -f 1
        )
      fi
      printf '%s|tree_sha256=%s\n' "$path" "$digest"
    else
      printf '%s|missing=true\n' "$path"
    fi
  done
} >"$temporary"

mv -f "$temporary" "$output_file"
chmod 0600 "$output_file"
trap - EXIT HUP INT TERM
echo "release manifest captured: $output_file schema=$schema_revision revision=$git_revision"
