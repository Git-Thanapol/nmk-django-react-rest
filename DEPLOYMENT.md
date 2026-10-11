# Deployment Guide: NMK (Fully Dockerized)

All services run in Docker: PostgreSQL, Django/Gunicorn, and Nginx.  
The root `docker-compose.yml` is the single source of truth.

---

## Prerequisites (VPS)

```bash
# Install Docker (Ubuntu)
sudo apt update
sudo apt install -y ca-certificates curl gnupg openssl git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow your user to run docker without sudo
sudo usermod -aG docker $USER
newgrp docker
```

---

## First-Time Deployment

Production domain: **https://www.myaccbase.com** (`myaccbase.com` redirects to `www`).
The domain's DNS must have A records for both names pointing to the server **before** step 3.

```bash
# 1. Clone the repository
mkdir -p /var/www && cd /var/www
git clone <repository_url> nmk
cd nmk

# 2. Create and fill in your environment file
cp env.docker.example .env
nano .env          # fill in ALL changeme_* values (see comments in the file)

# 3. Get the Let's Encrypt certificate (port 80 must be free, so do this BEFORE deploy.sh)
mkdir -p docker/certbot/www docker/certbot/conf
docker run --rm -p 80:80 -v "$PWD/docker/certbot/conf:/etc/letsencrypt" certbot/certbot   certonly --standalone -d www.myaccbase.com -d myaccbase.com   --email <your-email> --agree-tos --no-eff-email

# 4. Run the deploy script
chmod +x deploy.sh
./deploy.sh

# 5. Enable automatic certificate renewal (daily, 03:17)
echo "17 3 * * * root $PWD/docker/certbot/renew.sh >> /var/log/nmk-certbot-renew.log 2>&1" \
  | sudo tee /etc/cron.d/nmk-certbot
sudo chmod 644 /etc/cron.d/nmk-certbot
```

`deploy.sh` will:
- Generate a self-signed TLS cert (stored in `docker/nginx/certs/`, gitignored). It is only used for requests that do not match the domain, such as the raw IP, which redirect to the domain.
- Build the Docker images
- Start all three containers (db → web → nginx)
- Run database migrations and `collectstatic` automatically
- Create the Django superuser from `ADMIN_DJANGO_USERNAME` / `ADMIN_DJANGO_PASSWORD`

Access the app at `https://www.myaccbase.com/`.

> **Different domain?** Replace `www.myaccbase.com` / `myaccbase.com` in
> `docker/nginx/default.conf` and in the certbot command above.

---

## Updating After Code Changes

```bash
cd /var/www/nmk
./update.sh
```

`update.sh` will:
- `git pull` the latest code
- Rebuild only the `web` image
- Restart the web container (migrations + collectstatic run automatically)
- Leave the database and media files untouched

---

## Environment Variables (`.env`)

Copy `env.docker.example` to `.env` and fill in every value.  
The real `.env` is gitignored — never commit it.

| Variable | Notes |
|----------|-------|
| `DB_HOST` | Must be `db` (the compose service name) |
| `SECRET_KEY` | Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `ALLOWED_HOSTS` | Comma-separated hostnames, no http/https prefix: `www.myaccbase.com,myaccbase.com` (add the server IP if you want to reach it by IP) |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated, with scheme: `https://www.myaccbase.com,https://myaccbase.com` |
| `WEB_CONCURRENCY` | Gunicorn workers — use `7` for a 3-core VPS |

---

## HTTPS / Let's Encrypt

- Certificate files live in `docker/certbot/conf/` (gitignored, contains the private key). Back this folder up or be ready to re-issue.
- Renewal: `docker/certbot/renew.sh` runs daily from `/etc/cron.d/nmk-certbot`, renews if the cert is within 30 days of expiry, then reloads nginx. Log: `/var/log/nmk-certbot-renew.log`.
- Manual renewal / check: `./docker/certbot/renew.sh`
- Certificate expiry: `echo | openssl s_client -connect www.myaccbase.com:443 -servername www.myaccbase.com 2>/dev/null | openssl x509 -noout -enddate`
- HSTS is enabled (1 year, preload). Do not serve the site over plain HTTP once browsers have seen it.

---

## Maintenance Commands

```bash
# Live logs
docker compose logs -f web      # Django/Gunicorn logs
docker compose logs -f nginx    # Nginx access/error logs
docker compose logs -f db       # PostgreSQL logs

# Service status
docker compose ps

# Django management commands
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py shell
docker compose exec web python manage.py migrate

# Restart a single service
docker compose restart web
docker compose restart nginx

# Full restart
docker compose down && docker compose up -d

# Database backup
docker compose exec db pg_dump -U $DB_USER $DB_NAME > backup_$(date +%Y%m%d).sql

# Database restore
docker compose exec -T db psql -U $DB_USER $DB_NAME < backup_YYYYMMDD.sql
```

---

## Architecture

```
Internet → nginx:443 (TLS, Let's Encrypt) → web:8000 (Gunicorn/Django)
          nginx:80  → ACME challenge + redirect to HTTPS
                                   ↕
                               db:5432 (PostgreSQL)

Volumes:
  postgres_data   — PostgreSQL data (persistent, never deleted by update.sh)
  static_volume   — Django collectstatic output (shared nginx ↔ web, read-only for nginx)
  media_volume    — User uploads + generated reports (shared nginx ↔ web, read-only for nginx)
  private_media_volume — Bug report file attachments (web only; NOT served by nginx,
                         downloaded through a login-protected Django view)
  docker/nginx/certs/  — Self-signed TLS cert for non-domain requests (host dir, gitignored)
  docker/certbot/conf/ — Let's Encrypt certs and account (host dir, gitignored)
```

> **Backup reminder:** `media_volume` holds uploaded CSVs, purchase attachments, and
> generated PDF/Excel reports. `private_media_volume` holds bug report attachments
> (may contain customer data). Include both, plus `docker/certbot/conf/`, in your backup
> routine alongside the database.
