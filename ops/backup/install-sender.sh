#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ] || [ "$#" -ne 2 ]; then
  echo "usage: install-sender.sh AGE_RECIPIENT_FILE KNOWN_HOSTS_FILE (as root)" >&2
  exit 2
fi
recipient_file=$1
known_hosts_file=$2
release_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
command -v age >/dev/null
test -s "$recipient_file"
test -s "$known_hosts_file"

install -d -o root -g root -m 0700 /etc/admirra/backup
install -o root -g root -m 0644 "$recipient_file" /etc/admirra/backup/age-recipient.txt
install -o root -g root -m 0644 "$known_hosts_file" /etc/admirra/backup/known_hosts
if [ ! -s /etc/admirra/backup/receiver_ed25519 ]; then
  ssh-keygen -q -t ed25519 -N '' -f /etc/admirra/backup/receiver_ed25519
fi
chmod 0600 /etc/admirra/backup/receiver_ed25519
chmod 0644 /etc/admirra/backup/receiver_ed25519.pub

install -o root -g root -m 0755 "$release_dir/create_logical_backup.sh" /usr/local/sbin/admirra-create-logical-backup
install -o root -g root -m 0644 "$release_dir/systemd/admirra-logical-backup.service" /etc/systemd/system/admirra-logical-backup.service
install -o root -g root -m 0644 "$release_dir/systemd/admirra-logical-backup.timer" /etc/systemd/system/admirra-logical-backup.timer
systemctl daemon-reload

echo "backup sender prepared; authorize receiver_ed25519.pub before first run; timer not enabled"
