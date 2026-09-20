#!/bin/bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ] || { [ "$#" -ne 1 ] && [ "$#" -ne 3 ]; }; then
  echo "usage: restore_logical_backup.sh BACKUP_ID [MIGRATION_IMAGE EXPECTED_HEAD] (as root on repository host)" >&2
  exit 2
fi
backup_id=$1
migration_image=${2:-}
expected_head=${3:-}
case "$backup_id" in
  [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]T[0-9][0-9][0-9][0-9][0-9][0-9]Z-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;;
  *) echo "invalid backup id" >&2; exit 2 ;;
esac

repository=${ADMIRRA_BACKUP_REPOSITORY:-/var/lib/admirra-backup/postgres}
identity=${ADMIRRA_BACKUP_IDENTITY:-/etc/admirra/backup/age.key}
database_file=$repository/$backup_id.database.age
globals_file=$repository/$backup_id.globals.age
runtime_file=$repository/$backup_id.runtime.age
manifest_file=$repository/$backup_id.manifest.age
for file in "$identity" "$database_file" "$globals_file" "$manifest_file"; do
  test -s "$file"
done

manifest=$(age --decrypt --identity "$identity" "$manifest_file")
test "$(printf '%s\n' "$manifest" | sed -n 's/^backup_id=//p')" = "$backup_id"
schema_revision=$(printf '%s\n' "$manifest" | sed -n 's/^schema_revision=//p')
test -n "$schema_revision"

expected_database_sha=$(printf '%s\n' "$manifest" | sed -n 's/^stored database bytes=[0-9][0-9]* sha256=//p')
expected_globals_sha=$(printf '%s\n' "$manifest" | sed -n 's/^stored globals bytes=[0-9][0-9]* sha256=//p')
test "$(sha256sum "$database_file" | cut -d ' ' -f 1)" = "$expected_database_sha"
test "$(sha256sum "$globals_file" | cut -d ' ' -f 1)" = "$expected_globals_sha"
if [ -s "$runtime_file" ]; then
  expected_runtime_sha=$(printf '%s\n' "$manifest" | sed -n 's/^stored runtime bytes=[0-9][0-9]* sha256=//p')
  test "$(sha256sum "$runtime_file" | cut -d ' ' -f 1)" = "$expected_runtime_sha"
  runtime_members=$(age --decrypt --identity "$identity" "$runtime_file" | tar --list --file=-)
  printf '%s\n' "$runtime_members" | grep -qx 'root/Admirra/.env'
  printf '%s\n' "$runtime_members" | grep -qx 'root/Admirra/docker-compose.yml'
  printf '%s\n' "$runtime_members" | grep -qx 'etc/wireguard/admirra0.conf'
  if printf '%s\n' "$runtime_members" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
    echo "unsafe runtime backup member" >&2
    exit 1
  fi
fi

suffix=$(printf '%s' "$backup_id" | tr '[:upper:]' '[:lower:]')
container=admirra-restore-$suffix
volume=admirra-restore-$suffix
image=postgres:15.18-alpine@sha256:3d0f7584ed7d04e27fa050d6683a74746608faf21f202be78460d679cc56461f
started_at=$(date +%s)
application_container=
runtime_directory=

cleanup() {
  if [ -n "$application_container" ]; then
    docker stop --time 10 "$application_container" >/dev/null 2>&1 || true
    docker container rm "$application_container" >/dev/null 2>&1 || true
  fi
  docker stop --time 10 "$container" >/dev/null 2>&1 || true
  docker container rm "$container" >/dev/null 2>&1 || true
  docker volume rm "$volume" >/dev/null 2>&1 || true
  if [ -n "$runtime_directory" ] && [ -d "$runtime_directory" ]; then
    python3 -c 'import shutil,sys; shutil.rmtree(sys.argv[1])' "$runtime_directory"
  fi
}
trap cleanup EXIT HUP INT TERM
if docker container inspect "$container" >/dev/null 2>&1 || docker volume inspect "$volume" >/dev/null 2>&1; then
  echo "restore drill resources already exist" >&2
  exit 1
fi

docker volume create "$volume" >/dev/null
docker run -d \
  --name "$container" \
  --network none \
  --memory 2g \
  --cpus 2 \
  --pids-limit 256 \
  --shm-size 256m \
  -e POSTGRES_PASSWORD=isolated-restore-only \
  -e POSTGRES_DB=restore \
  -v "$volume:/var/lib/postgresql/data" \
  "$image" >/dev/null

ready=0
for attempt in $(seq 1 60); do
  if docker exec "$container" pg_isready -U postgres -d restore >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "isolated PostgreSQL did not become ready" >&2
  exit 1
fi

test "$(docker inspect "$container" --format '{{.HostConfig.NetworkMode}}')" = none
age --decrypt --identity "$identity" "$database_file" \
| docker exec -i "$container" pg_restore -U postgres -d restore \
    --exit-on-error --no-owner --no-privileges

restored_revision=$(docker exec "$container" psql -U postgres -d restore -Atc \
  "SELECT version_num FROM alembic_version ORDER BY version_num LIMIT 1")
test "$restored_revision" = "$schema_revision"

check=$(docker exec "$container" psql -U postgres -d restore -Atc \
  "SELECT (SELECT count(*) FROM users) >= 0
       AND (SELECT count(*) FROM clients) >= 0
       AND (SELECT count(*) FROM integrations) >= 0
       AND NOT EXISTS (SELECT 1 FROM alembic_version WHERE version_num IS NULL)")
test "$check" = t

if [ -n "$migration_image" ]; then
  case "$expected_head" in
    [0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z]) ;;
    *) echo "invalid expected migration head" >&2; exit 2 ;;
  esac
  docker image inspect "$migration_image" >/dev/null
  docker run --rm \
    --network "container:$container" \
    --read-only \
    --tmpfs /tmp:size=64m \
    --user 10001:10001 \
    --pids-limit 128 \
    --cap-drop ALL \
    --security-opt no-new-privileges:true \
    -e DATABASE_URL=postgresql://postgres:isolated-restore-only@127.0.0.1:5432/restore \
    --entrypoint alembic \
    "$migration_image" upgrade head
  restored_revision=$(docker exec "$container" psql -U postgres -d restore -Atc \
    "SELECT version_num FROM alembic_version ORDER BY version_num LIMIT 1")
  test "$restored_revision" = "$expected_head"
  migrated_tables=$(docker exec "$container" psql -U postgres -d restore -Atc \
    "SELECT count(*) FROM information_schema.tables
       WHERE table_schema = 'public'
         AND table_name IN ('background_jobs','background_outbox','background_schedule_cursor',
           'report_route_attempts','history_backfill_runs','public_report_links',
           'stored_artifacts','report_artifact_refs','artifact_public_links')")
  test "$migrated_tables" = 9
fi

application_smoke=skipped
if [ "${ADMIRRA_APPLICATION_SMOKE:-0}" = 1 ]; then
  if [ -z "$migration_image" ] || [ ! -s "$runtime_file" ]; then
    echo "application smoke requires migration image and runtime object" >&2
    exit 2
  fi
  runtime_directory=$(mktemp -d /dev/shm/admirra-runtime-restore.XXXXXX)
  chmod 0700 "$runtime_directory"
  age --decrypt --identity "$identity" "$runtime_file" \
  | tar --extract --file=- --directory="$runtime_directory" --no-same-owner --no-same-permissions
  test -s "$runtime_directory/root/Admirra/.env"
  test -d "$runtime_directory/root/Admirra/uploads"
  test -d "$runtime_directory/root/Admirra/secrets"
  chown -R 10001:10001 "$runtime_directory/root/Admirra"

  application_container=admirra-app-restore-$suffix
  if docker container inspect "$application_container" >/dev/null 2>&1; then
    echo "application restore drill container already exists" >&2
    exit 1
  fi
  docker run -d \
    --name "$application_container" \
    --network "container:$container" \
    --read-only \
    --tmpfs /tmp:size=128m \
    --user 10001:10001 \
    --memory 1g \
    --cpus 1 \
    --pids-limit 256 \
    --cap-drop ALL \
    --security-opt no-new-privileges:true \
    -e DATABASE_URL=postgresql://postgres:isolated-restore-only@127.0.0.1:5432/restore \
    -e APP_PROCESS_ROLE=api \
    -e DB_AUTO_BOOTSTRAP=false \
    -e RUN_SYNC_WORKER=false \
    -e RUN_API_SCHEDULER=false \
    -e DURABLE_TASKS=false \
    -e REDIS_ENABLED=false \
    -e SHARED_READ_CACHE=false \
    -e SMTP_ENABLED=false \
    -e LOG_TO_STDOUT=true \
    -e OPENAI_API_KEY= \
    -e WORDSTAT_API_KEY= \
    -v "$runtime_directory/root/Admirra/.env:/app/.env:ro" \
    -v "$runtime_directory/root/Admirra/uploads:/app/uploads:ro" \
    -v "$runtime_directory/root/Admirra/secrets:/app/secrets:ro" \
    "$migration_image" >/dev/null

  ready=0
  for attempt in $(seq 1 60); do
    if docker exec "$application_container" python -c \
      'import json,urllib.request; data=json.load(urllib.request.urlopen("http://127.0.0.1:8001/api/health/ready", timeout=2)); assert data["status"] == "ready" and data["database"] == "ok"' \
      >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 1
  done
  if [ "$ready" -ne 1 ]; then
    echo "restored application did not become ready" >&2
    docker logs --tail 30 "$application_container" >&2 || true
    exit 1
  fi
  docker exec "$application_container" python -c \
    'import urllib.error,urllib.request
try:
    urllib.request.urlopen("http://127.0.0.1:8001/api/auth/me", timeout=2)
except urllib.error.HTTPError as error:
    assert error.code in (401, 403)
else:
    raise AssertionError("protected route was not protected")'
  application_smoke=passed
fi

duration=$(( $(date +%s) - started_at ))
echo "restore drill passed: backup=$backup_id schema=$restored_revision duration_seconds=$duration network=none migration=$([ -n "$migration_image" ] && echo applied || echo skipped) application=$application_smoke"
