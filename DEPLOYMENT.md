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

```bash
# 1. Clone the repository
mkdir -p /var/www && cd /var/www
git clone <repository_url> nmk
cd nmk

# 2. Create and fill in your environment file
cp env.docker.example .env
nano .env          # fill in ALL changeme_* values (see comments in the file)

# 3. Run the deploy script
chmod +x deploy.sh
./deploy.sh
```

`deploy.sh` will:
- Generate a self-signed TLS cert for your server IP (stored in `docker/nginx/certs/`, gitignored)
- Build the Docker images
- Start all three containers (db → web → nginx)
- Run database migrations and `collectstatic` automatically
- Create the Django superuser from `ADMIN_DJANGO_USERNAME` / `ADMIN_DJANGO_PASSWORD`

Access the app at `https://<your-server-ip>/` — accept the self-signed cert warning once.

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
| `ALLOWED_HOSTS` | Your VPS public IP (no http/https prefix) |
| `CSRF_TRUSTED_ORIGINS` | `https://your.server.ip` |
| `WEB_CONCURRENCY` | Gunicorn workers — use `7` for a 3-core VPS |

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
Internet → nginx:443 (TLS) → web:8000 (Gunicorn/Django)
                                   ↕
                               db:5432 (PostgreSQL)

Volumes:
  postgres_data   — PostgreSQL data (persistent, never deleted by update.sh)
  static_volume   — Django collectstatic output (shared nginx ↔ web, read-only for nginx)
  media_volume    — User uploads + generated reports (shared nginx ↔ web, read-only for nginx)
  docker/nginx/certs/  — Self-signed TLS cert (host dir, gitignored)
```

> **Backup reminder:** `media_volume` holds uploaded CSVs, purchase attachments, and
> generated PDF/Excel reports. Include it in your backup routine alongside the database.
