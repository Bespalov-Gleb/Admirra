#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ] || [ "$#" -ne 1 ]; then
  echo "usage: install-repository.sh AUTHORIZED_PUBLIC_KEY_FILE (as root)" >&2
  exit 2
fi
public_key_file=$1
release_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
test -s "$public_key_file"
command -v age-keygen >/dev/null

if ! id -u admirra-backup >/dev/null 2>&1; then
  useradd --system --home-dir /var/lib/admirra-backup --create-home --shell /bin/bash admirra-backup
fi

install -o root -g root -m 0755 "$release_dir/receive.py" /usr/local/sbin/admirra-backup-receive
install -d -o admirra-backup -g admirra-backup -m 0700 /var/lib/admirra-backup /var/lib/admirra-backup/.ssh /var/lib/admirra-backup/postgres
install -d -o root -g root -m 0700 /etc/admirra/backup

if [ ! -s /etc/admirra/backup/age.key ]; then
  umask 077
  age-keygen -o /etc/admirra/backup/age.key >/dev/null
fi
age-keygen -y /etc/admirra/backup/age.key >/etc/admirra/backup/age-recipient.txt
chmod 0600 /etc/admirra/backup/age.key
chmod 0644 /etc/admirra/backup/age-recipient.txt

public_key=$(tr -d '\r\n' <"$public_key_file")
case "$public_key" in
  ssh-ed25519\ *) ;;
  *) echo "expected an ssh-ed25519 public key" >&2; exit 1 ;;
esac
printf 'restrict,command="/usr/local/sbin/admirra-backup-receive" %s\n' "$public_key" \
  >/var/lib/admirra-backup/.ssh/authorized_keys
chown admirra-backup:admirra-backup /var/lib/admirra-backup/.ssh/authorized_keys
chmod 0600 /var/lib/admirra-backup/.ssh/authorized_keys

echo "encrypted backup repository prepared; timer not enabled"
