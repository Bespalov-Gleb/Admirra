#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "install-external-heartbeat.sh must run as root" >&2
  exit 2
fi

source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
install_dir=/opt/admirra-public-heartbeat
state_dir=/var/lib/admirra-public-heartbeat
unit_dir=/etc/systemd/system

install -d -o root -g root -m 0755 "$install_dir" "$state_dir"
install -o root -g root -m 0755 "$source_dir/external_heartbeat.py" "$install_dir/external_heartbeat.py"
install -o root -g root -m 0644 \
  "$source_dir/systemd/admirra-public-heartbeat.service" \
  "$unit_dir/admirra-public-heartbeat.service"
install -o root -g root -m 0644 \
  "$source_dir/systemd/admirra-public-heartbeat.timer" \
  "$unit_dir/admirra-public-heartbeat.timer"

if [ -f /etc/admirra/monitoring/heartbeat-telegram.json ]; then
  install -d -o root -g root -m 0755 "$unit_dir/admirra-public-heartbeat.service.d"
  install -o root -g root -m 0644 \
    "$source_dir/systemd/admirra-public-heartbeat-telegram.conf" \
    "$unit_dir/admirra-public-heartbeat.service.d/telegram.conf"
fi

systemd-analyze verify \
  "$unit_dir/admirra-public-heartbeat.service" \
  "$unit_dir/admirra-public-heartbeat.timer"
systemctl daemon-reload
systemctl enable --now admirra-public-heartbeat.timer
systemctl start admirra-public-heartbeat.service
systemctl show \
  --property=Result \
  --property=ExecMainStatus \
  --property=ActiveState \
  admirra-public-heartbeat.service
