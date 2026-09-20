#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ] || [ "$#" -ne 2 ]; then
  echo "usage: install-sender.sh AGE_RECIPIENT_FILE SERVER_ED25519_PUBLIC_KEY_FILE (as root)" >&2
  exit 2
fi
recipient_file=$1
host_key_file=$2
release_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
command -v age >/dev/null
test -s "$recipient_file"
test -s "$host_key_file"

install -d -o root -g root -m 0700 /etc/admirra/backup
install -o root -g root -m 0644 "$recipient_file" /etc/admirra/backup/age-recipient.txt
set -- $(sed -n '1{s/[[:space:]].*$//;p;}' "$host_key_file") \
       $(sed -n '1{s/^[^[:space:]]*[[:space:]]*//;s/[[:space:]].*$//;p;}' "$host_key_file")
if [ "$1" != "ssh-ed25519" ] || [ -z "${2:-}" ]; then
  echo "expected an ssh-ed25519 host public key" >&2
  exit 1
fi
printf '10.77.0.2 %s %s\n' "$1" "$2" >/etc/admirra/backup/known_hosts
chmod 0644 /etc/admirra/backup/known_hosts
test -s /etc/admirra/backup/receiver_ed25519
chmod 0600 /etc/admirra/backup/receiver_ed25519
chmod 0644 /etc/admirra/backup/receiver_ed25519.pub

install -o root -g root -m 0755 "$release_dir/create_logical_backup.sh" /usr/local/sbin/admirra-create-logical-backup
install -o root -g root -m 0755 "$release_dir/capture_release_manifest.sh" /usr/local/sbin/admirra-capture-release-manifest
install -d -o root -g root -m 0700 /etc/admirra/release-manifests
install -o root -g root -m 0644 "$release_dir/systemd/admirra-logical-backup.service" /etc/systemd/system/admirra-logical-backup.service
install -o root -g root -m 0644 "$release_dir/systemd/admirra-logical-backup.timer" /etc/systemd/system/admirra-logical-backup.timer
systemctl daemon-reload

echo "backup sender prepared; authorize receiver_ed25519.pub before first run; timer not enabled"
