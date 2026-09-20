#!/bin/bash
set -euo pipefail

config_dir=${ADMIRRA_BACKUP_CONFIG_DIR:-/etc/admirra/backup}
database_container=${ADMIRRA_DB_CONTAINER:-admirra-db-1}
repository_host=${ADMIRRA_BACKUP_HOST:-10.77.0.2}
repository_user=${ADMIRRA_BACKUP_USER:-admirra-backup}

private_key=$config_dir/receiver_ed25519
known_hosts=$config_dir/known_hosts
recipient_file=$config_dir/age-recipient.txt

for file in "$private_key" "$known_hosts" "$recipient_file"; do
  test -s "$file"
done
test "$(stat -c '%a' "$private_key")" = 600

recipient=$(tr -d '\r\n' <"$recipient_file")
case "$recipient" in
  age1*) ;;
  *) echo "invalid age recipient" >&2; exit 1 ;;
esac

/usr/local/sbin/admirra-capture-release-manifest >/dev/null
release_manifest_file=/etc/admirra/release-manifests/current.txt
test -s "$release_manifest_file"
release_manifest_sha=$(sha256sum "$release_manifest_file" | cut -d ' ' -f 1)

backup_id=$(date -u +%Y%m%dT%H%M%SZ)-$(openssl rand -hex 4)
ssh_options=(
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=yes
  -o "UserKnownHostsFile=$known_hosts"
  -i "$private_key"
)

docker inspect "$database_container" >/dev/null
schema_revision=$(docker exec "$database_container" psql -U postgres -d saas_project -Atc \
  "SELECT version_num FROM alembic_version ORDER BY version_num LIMIT 1")
test -n "$schema_revision"

database_receipt=$(
  docker exec "$database_container" pg_dump -U postgres -d saas_project \
    --format=custom --compress=6 --no-owner --no-privileges \
  | age --encrypt --recipient "$recipient" \
  | ssh "${ssh_options[@]}" "$repository_user@$repository_host" "put $backup_id database"
)

globals_receipt=$(
  docker exec "$database_container" pg_dumpall -U postgres --globals-only \
  | age --encrypt --recipient "$recipient" \
  | ssh "${ssh_options[@]}" "$repository_user@$repository_host" "put $backup_id globals"
)

for path in \
  /root/Admirra/.env \
  /root/Admirra/secrets \
  /root/Admirra/uploads \
  /root/Admirra/docker-compose.yml \
  /root/Admirra/nginx.conf \
  /etc/admirra \
  /etc/nginx \
  /etc/wireguard \
  /etc/letsencrypt; do
  test -e "$path"
done
runtime_receipt=$(
  tar --create --file=- --numeric-owner --one-file-system --directory=/ \
    root/Admirra/.env \
    root/Admirra/secrets \
    root/Admirra/uploads \
    root/Admirra/docker-compose.yml \
    root/Admirra/nginx.conf \
    etc/admirra \
    etc/nginx \
    etc/wireguard \
    etc/letsencrypt \
  | age --encrypt --recipient "$recipient" \
  | ssh "${ssh_options[@]}" "$repository_user@$repository_host" "put $backup_id runtime"
)

created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf 'backup_id=%s\ncreated_at=%s\nschema_revision=%s\nrelease_manifest_sha256=%s\n%s\n%s\n%s\n' \
  "$backup_id" "$created_at" "$schema_revision" "$release_manifest_sha" \
  "$database_receipt" "$globals_receipt" "$runtime_receipt" \
| age --encrypt --recipient "$recipient" \
| ssh "${ssh_options[@]}" "$repository_user@$repository_host" "put $backup_id manifest" >/dev/null

echo "logical backup completed: $backup_id schema=$schema_revision"
