#!/bin/sh
set -eu

role=${1:-}
case "$role" in
  ingress|api2) ;;
  *) echo "usage: $0 ingress|api2" >&2; exit 64 ;;
esac

systemctl disable --now "admirra-api2-monitor@${role}.timer" 2>/dev/null || true
systemctl stop "admirra-api2-monitor@${role}.service" 2>/dev/null || true
rm -f "/var/lib/admirra-api2-monitor/${role}.prom"
systemctl daemon-reload
