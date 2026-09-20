#!/bin/bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ] || { [ "$#" -ne 1 ] && [ "$#" -ne 3 ]; }; then
  echo "usage: restore_logical_backup.sh BACKUP_ID [MIGRATION_IMAGE EXPECTED_HEAD] (as root on repository host)" >&2
  exit 2
fi
backup_id=$1
migration_image=${2:-}
expected_head=${3:-}
release_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
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
release_manifest_sha=$(printf '%s\n' "$manifest" | sed -n 's/^release_manifest_sha256=//p')

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
  if [ -n "$release_manifest_sha" ]; then
    case "$release_manifest_sha" in
      [0-9a-f]*) printf '%s\n' "$release_manifest_sha" | grep -Eq '^[0-9a-f]{64}$' || { echo "invalid release manifest checksum" >&2; exit 1; } ;;
      *) echo "invalid release manifest checksum" >&2; exit 1 ;;
    esac
    actual_release_manifest_sha=$(
      age --decrypt --identity "$identity" "$runtime_file" \
      | tar --extract --to-stdout --file=- etc/admirra/release-manifests/current.txt \
      | sha256sum \
      | cut -d ' ' -f 1
    )
    test "$actual_release_manifest_sha" = "$release_manifest_sha"
  fi
fi

run_id=$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')
suffix=$(printf '%s-%s' "$backup_id" "$run_id" | tr '[:upper:]' '[:lower:]')
container=admirra-restore-$suffix
volume=admirra-restore-$suffix
image=postgres:15.18-alpine@sha256:3d0f7584ed7d04e27fa050d6683a74746608faf21f202be78460d679cc56461f
started_at=$(date +%s)
application_container=
broker_container=
worker_containers=()
runtime_directory=

cleanup() {
  for worker_container in "${worker_containers[@]}"; do
    docker stop --time 10 "$worker_container" >/dev/null 2>&1 || true
    docker container rm "$worker_container" >/dev/null 2>&1 || true
  done
  if [ -n "$broker_container" ]; then
    docker stop --time 10 "$broker_container" >/dev/null 2>&1 || true
    docker container rm "$broker_container" >/dev/null 2>&1 || true
  fi
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
if docker container inspect "$container" >/dev/null 2>&1 || docker volume inspect "$volume" >/dev/null 2>&1; then
  echo "restore drill resources already exist" >&2
  exit 1
fi
trap cleanup EXIT HUP INT TERM

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
api_load_smoke=skipped
worker_preflight=skipped
worker_smoke=skipped
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

  docker run --rm \
    --network "container:$container" \
    --read-only \
    --tmpfs /tmp:size=64m \
    --user 10001:10001 \
    --memory 512m \
    --cpus 1 \
    --pids-limit 128 \
    --cap-drop ALL \
    --security-opt no-new-privileges:true \
    -e DATABASE_URL=postgresql://postgres:isolated-restore-only@127.0.0.1:5432/restore \
    -e APP_PROCESS_ROLE=worker \
    -e APP_RELEASE="restore-smoke-$expected_head" \
    -e "EXPECTED_SCHEMA_REVISION=$expected_head" \
    -e DB_AUTO_BOOTSTRAP=false \
    -e DB_POOL_SIZE=5 \
    -e DB_MAX_OVERFLOW=0 \
    -e DB_POOL_TIMEOUT=5 \
    -e RUN_SYNC_WORKER=false \
    -e RUN_API_SCHEDULER=false \
    -e DURABLE_TASKS=true \
    -e REPORT_DELIVERY_GUARDS=true \
    -e SHARED_READ_CACHE=false \
    -e LOG_TO_STDOUT=true \
    -v "$runtime_directory/root/Admirra/.env:/app/.env:ro" \
    -v "$runtime_directory/root/Admirra/secrets:/app/secrets:ro" \
    --entrypoint python \
    "$migration_image" -c 'from automation.work_preflight import check; check()'
  worker_preflight=passed

  if [ "${ADMIRRA_WORKER_SMOKE:-0}" = 1 ]; then
    broker_container=admirra-broker-restore-$suffix
    docker run -d \
      --name "$broker_container" \
      --network "container:$container" \
      --read-only \
      --user 999:999 \
      --tmpfs /data:rw,noexec,nosuid,size=64m,uid=999,gid=999,mode=0700 \
      --tmpfs /tmp:rw,noexec,nosuid,size=16m,uid=999,gid=999,mode=0700 \
      --memory 128m \
      --cpus 0.25 \
      --pids-limit 64 \
      --cap-drop ALL \
      --security-opt no-new-privileges:true \
      redis:7.4-alpine@sha256:ff02b58f971e7d7d156a1267e283fcbbeee91773b6aa36c49dac28ecfe28eadf \
      redis-server --bind 127.0.0.1 --protected-mode no --save '' --appendonly no >/dev/null
    for attempt in $(seq 1 30); do
      if docker exec "$broker_container" redis-cli ping 2>/dev/null | grep -qx PONG; then
        break
      fi
      if [ "$attempt" -eq 30 ]; then
        echo "isolated restore broker did not become ready" >&2
        exit 1
      fi
      sleep 1
    done

    start_worker() {
      local role=$1 memory=$2 cpus=$3 concurrency=$4 queues=$5
      local worker=admirra-worker-$role-restore-$suffix
      docker run -d \
        --name "$worker" \
        --network "container:$container" \
        --read-only \
        --tmpfs /tmp:size=128m \
        --user 10001:10001 \
        --memory "$memory" \
        --cpus "$cpus" \
        --pids-limit 128 \
        --cap-drop ALL \
        --security-opt no-new-privileges:true \
        -e DATABASE_URL=postgresql://postgres:isolated-restore-only@127.0.0.1:5432/restore \
        -e CELERY_BROKER_URL=redis://127.0.0.1:6379/0 \
        -e TASK_BROKER_PREFIX="restore:$suffix:" \
        -e APP_PROCESS_ROLE=worker \
        -e WW_TEST=1 \
        -e "WW_TEST_ID=restore-$suffix" \
        -e DB_POOL_SIZE=2 \
        -e DB_MAX_OVERFLOW=0 \
        -e APP_RELEASE="restore-smoke-$expected_head" \
        -e "EXPECTED_SCHEMA_REVISION=$expected_head" \
        -e DB_AUTO_BOOTSTRAP=false \
        -e RUN_SYNC_WORKER=false \
        -e RUN_API_SCHEDULER=false \
        -e DURABLE_TASKS=true \
        -e REPORT_DELIVERY_GUARDS=true \
        -e SHARED_READ_CACHE=false \
        -e LOG_TO_STDOUT=true \
        -e REJECTED_LEADS_DIR=/tmp/rejected-leads \
        -e OPENAI_API_KEY= \
        -e WORDSTAT_API_KEY= \
        -v "$runtime_directory/root/Admirra/.env:/app/.env:ro" \
        -v "$runtime_directory/root/Admirra/uploads:/app/uploads:ro" \
        -v "$runtime_directory/root/Admirra/secrets:/app/secrets:ro" \
        "$migration_image" python -m automation.work_worker \
        "--concurrency=$concurrency" "--queues=$queues" "--hostname=$role@restore" >/dev/null
      worker_containers+=("$worker")
    }
    start_worker manual 1280m 1.5 2 sync.manual
    start_worker nightly 1280m 1.5 2 sync.nightly,sync.backfill
    start_worker reports 768m 1 1 reports
    start_worker maintenance 768m 1 1 maintenance

    workers_ready=0
    for attempt in $(seq 1 60); do
      workers_ready=1
      for worker_container in "${worker_containers[@]}"; do
        if ! docker logs "$worker_container" 2>&1 | grep -q 'ready\.'; then
          workers_ready=0
          break
        fi
      done
      [ "$workers_ready" -eq 1 ] && break
      sleep 1
    done
    if [ "$workers_ready" -ne 1 ]; then
      echo "isolated restored worker set did not become ready" >&2
      for worker_container in "${worker_containers[@]}"; do
        docker logs --tail 20 "$worker_container" >&2 || true
      done
      exit 1
    fi

    ping_output=$(docker run --rm \
      --network "container:$container" \
      --read-only \
      --tmpfs /tmp:size=32m \
      --user 10001:10001 \
      --memory 256m \
      --cpus 0.5 \
      --pids-limit 64 \
      --cap-drop ALL \
      --security-opt no-new-privileges:true \
      -e CELERY_BROKER_URL=redis://127.0.0.1:6379/0 \
      -e TASK_BROKER_PREFIX="restore:$suffix:" \
      --entrypoint celery \
      "$migration_image" -A automation.celery_app:app inspect ping --timeout 10)
    for role in manual nightly reports maintenance; do
      printf '%s\n' "$ping_output" | grep -q "$role@restore: OK"
    done
    worker_smoke=passed
  fi

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
    -e WW_TEST=1 \
    -e "WW_TEST_ID=restore-$suffix" \
    -e DB_POOL_SIZE=5 \
    -e DB_MAX_OVERFLOW=0 \
    -e "EXPECTED_SCHEMA_REVISION=$expected_head" \
    -e DB_AUTO_BOOTSTRAP=false \
    -e RUN_SYNC_WORKER=false \
    -e RUN_API_SCHEDULER=false \
    -e DURABLE_TASKS=false \
    -e REDIS_ENABLED=false \
    -e SHARED_READ_CACHE=false \
    -e SMTP_ENABLED=false \
    -e LOG_TO_STDOUT=true \
    -e REJECTED_LEADS_DIR=/tmp/rejected-leads \
    -e OPENAI_API_KEY= \
    -e WORDSTAT_API_KEY= \
    -v "$runtime_directory/root/Admirra/.env:/app/.env:ro" \
    -v "$runtime_directory/root/Admirra/uploads:/app/uploads:ro" \
    -v "$runtime_directory/root/Admirra/secrets:/app/secrets:ro" \
    "$migration_image" >/dev/null

  ready=0
  for attempt in $(seq 1 60); do
    if docker exec "$application_container" python -c \
      'import json,urllib.request; data=json.load(urllib.request.urlopen("http://127.0.0.1:8001/api/health/ready", timeout=2)); assert data["status"] == "ok" and data["role"] == "api"' \
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
  if [ "${ADMIRRA_API_LOAD_SMOKE:-0}" = 1 ]; then
    test -s "$release_dir/api_load_smoke.py"
    : "${ADMIRRA_TEST_ACCOUNT_EMAIL:?Select the approved test account for read load}"
    docker exec -i -e "ADMIRRA_TEST_ACCOUNT_EMAIL=$ADMIRRA_TEST_ACCOUNT_EMAIL" \
      -e "ADMIRRA_DASHBOARD_BENCHMARK=${ADMIRRA_DASHBOARD_BENCHMARK:-0}" \
      "$application_container" python - <"$release_dir/api_load_smoke.py"
    api_load_smoke=passed
  fi
fi

duration=$(( $(date +%s) - started_at ))
echo "restore drill passed: backup=$backup_id schema=$restored_revision duration_seconds=$duration network=none migration=$([ -n "$migration_image" ] && echo applied || echo skipped) worker_preflight=$worker_preflight worker_smoke=$worker_smoke application=$application_smoke api_load=$api_load_smoke"
