#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "root required" >&2
  exit 2
fi
install -d -o root -g root -m 0700 /etc/admirra/backup
if [ ! -s /etc/admirra/backup/receiver_ed25519 ]; then
  ssh-keygen -q -t ed25519 -N '' -f /etc/admirra/backup/receiver_ed25519
fi
chmod 0600 /etc/admirra/backup/receiver_ed25519
chmod 0644 /etc/admirra/backup/receiver_ed25519.pub
echo "/etc/admirra/backup/receiver_ed25519.pub is ready for repository authorization"
