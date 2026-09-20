server {
    server_name admirra.ru www.admirra.ru;

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ~ ^/api/assistant/conversations/ {
        client_max_body_size 25m;
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Initial API-2 canary: only verified, read-only endpoints. Non-GET methods
    # are internally routed to the original API and never enter the read pool.
    location @admirra_primary_api {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        proxy_next_upstream off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;
    }

    location = /api/auth/me {
        error_page 418 = @admirra_primary_api;
        if ($request_method !~ ^(GET|HEAD)$) { return 418; }
        include /etc/nginx/snippets/admirra-api2-read-proxy.conf;
    }

    location = /api/clients {
        error_page 418 = @admirra_primary_api;
        if ($request_method !~ ^(GET|HEAD)$) { return 418; }
        include /etc/nginx/snippets/admirra-api2-read-proxy.conf;
    }

    location = /api/folders {
        error_page 418 = @admirra_primary_api;
        if ($request_method !~ ^(GET|HEAD)$) { return 418; }
        include /etc/nginx/snippets/admirra-api2-read-proxy.conf;
    }

    location = /api/notifications {
        error_page 418 = @admirra_primary_api;
        if ($request_method !~ ^(GET|HEAD)$) { return 418; }
        include /etc/nginx/snippets/admirra-api2-read-proxy.conf;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        # Byesu/Claude может формировать сложный AI-комментарий дольше
        # стандартных 60 секунд. Backend ограничен 100 секундами.
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8001/docs;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8001/openapi.json;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen [::]:443 ssl ipv6only=on; # managed by Certbot
    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/admirra.ru/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/admirra.ru/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot


}
server {
    if ($host = www.admirra.ru) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    if ($host = admirra.ru) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    listen 80;
    listen [::]:80;
    server_name admirra.ru www.admirra.ru;
    return 404; # managed by Certbot




}
