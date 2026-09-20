#!/bin/sh
set -eu

release_dir=/root/admirra-api2-canary-20260920
site=/etc/nginx/sites-available/admirra.ru
expected_site=c2c0cdb3f4997bfc90555ee4f6028ee4abbbd28cc60811fd18c92e5a177a6c20

test "$(sha256sum "$site" | cut -d ' ' -f 1)" = "$expected_site"
test ! -e /etc/nginx/conf.d/admirra-api2-upstream.conf
test ! -e /etc/nginx/snippets/admirra-api2-read-proxy.conf
curl -fsS --connect-timeout 2 --max-time 5 http://10.77.0.2:8001/api/health/ready >/dev/null

install -d -m 700 "$release_dir/backup"
cp -a "$site" "$release_dir/backup/admirra.ru"
nginx -T > "$release_dir/backup/nginx.before.txt" 2>&1

install -o root -g root -m 644 "$release_dir/admirra-api2-upstream.conf" /etc/nginx/conf.d/admirra-api2-upstream.conf
install -o root -g root -m 644 "$release_dir/admirra-api2-read-proxy.conf" /etc/nginx/snippets/admirra-api2-read-proxy.conf
install -o root -g root -m 644 "$release_dir/admirra.ru" "$site"

if ! nginx -t; then
    cp -a "$release_dir/backup/admirra.ru" "$site"
    unlink /etc/nginx/conf.d/admirra-api2-upstream.conf
    unlink /etc/nginx/snippets/admirra-api2-read-proxy.conf
    nginx -t
    exit 1
fi

systemctl reload nginx
curl -fsS --connect-timeout 3 --max-time 10 https://admirra.ru/ >/dev/null
install -m 600 /dev/null "$release_dir/activated"
nginx -T > "$release_dir/nginx.active.txt" 2>&1
printf '%s\n' 'API-2 read canary activated'
