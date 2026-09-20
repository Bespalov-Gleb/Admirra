#!/bin/sh
set -eu

role=${1:-}
case "$role" in
  ingress|api2) ;;
  *) echo "usage: $0 ingress|api2" >&2; exit 64 ;;
esac

source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
install_dir=/opt/admirra-api2-canary
unit_dir=/etc/systemd/system

install -d -m 0755 "$install_dir" /var/lib/admirra-api2-monitor
install -m 0755 "$source_dir/check_canary.py" "$install_dir/check_canary.py"
install -m 0644 "$source_dir/systemd/admirra-api2-monitor@.service" "$unit_dir/admirra-api2-monitor@.service"
install -m 0644 "$source_dir/systemd/admirra-api2-monitor@.timer" "$unit_dir/admirra-api2-monitor@.timer"

systemd-analyze verify \
  "$unit_dir/admirra-api2-monitor@.service" \
  "$unit_dir/admirra-api2-monitor@.timer"
systemctl daemon-reload
systemctl enable --now "admirra-api2-monitor@${role}.timer"
systemctl start "admirra-api2-monitor@${role}.service"
systemctl show \
  --property=Result \
  --property=ExecMainStatus \
  --property=ActiveState \
  "admirra-api2-monitor@${role}.service"
