#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "deploy-alertmanager.sh must run as root" >&2
  exit 2
fi

release_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=quay.io/prometheus/alertmanager@sha256:e9733bafb1bdef9b00e25a21f8f99dc26a22224bf16641ad754d1649f4c3357a
config=/etc/admirra/monitoring/alertmanager.yml
receiver=/etc/admirra/monitoring/telegram-token

for file in "$config" "$receiver"; do
  if [ ! -f "$file" ] || [ -L "$file" ] || [ ! -s "$file" ]; then
    echo "required Alertmanager configuration is missing or unsafe" >&2
    exit 2
  fi
  if [ "$(stat -c '%u:%g:%a' "$file")" != "0:65534:440" ]; then
    echo "Alertmanager configuration must be root:65534 mode 0440" >&2
    exit 2
  fi
done

docker run --rm \
  --network none \
  --read-only \
  --user 65534:65534 \
  --entrypoint /bin/amtool \
  -v "$config:/etc/alertmanager/alertmanager.yml:ro" \
  -v "$receiver:/etc/alertmanager/secrets/telegram-token:ro" \
  "$image" \
  check-config /etc/alertmanager/alertmanager.yml

docker compose \
  --project-name admirra-alerting \
  -f "$release_dir/compose.alertmanager.yml" \
  config --quiet
docker compose \
  --project-name admirra-alerting \
  -f "$release_dir/compose.alertmanager.yml" \
  up -d

attempt=1
while [ "$attempt" -le 30 ]; do
  if curl --fail --silent --show-error --max-time 3 http://127.0.0.1:9093/-/ready >/dev/null 2>&1; then
    exit 0
  fi
  attempt=$((attempt + 1))
  sleep 1
done

echo "Alertmanager did not become ready" >&2
exit 1
