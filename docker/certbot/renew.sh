#!/usr/bin/env bash
# Renew Let's Encrypt certs and reload nginx. Run daily from cron.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
docker run --rm \
  -v "$PWD/docker/certbot/conf:/etc/letsencrypt" \
  -v "$PWD/docker/certbot/www:/var/www/certbot" \
  certbot/certbot renew --webroot -w /var/www/certbot --quiet
docker compose exec -T nginx nginx -s reload
