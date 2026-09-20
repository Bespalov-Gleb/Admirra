#!/bin/sh
set -eu

release_dir=/root/admirra-api2-canary-20260920
site=/etc/nginx/sites-available/admirra.ru

test -f "$release_dir/backup/admirra.ru"
cp -a "$release_dir/backup/admirra.ru" "$site"
if test -e /etc/nginx/conf.d/admirra-api2-upstream.conf; then
    unlink /etc/nginx/conf.d/admirra-api2-upstream.conf
fi
if test -e /etc/nginx/snippets/admirra-api2-read-proxy.conf; then
    unlink /etc/nginx/snippets/admirra-api2-read-proxy.conf
fi
nginx -t
systemctl reload nginx
printf '%s\n' 'API-2 read canary rolled back'
