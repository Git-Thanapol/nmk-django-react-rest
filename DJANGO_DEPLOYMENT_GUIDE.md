# Django + React Deployment Guide (Separate Docker Instances)

This guide details how to deploy the **nmk** project from scratch. It uses separate Docker instances for the database and backend, while the frontend is built and served via Nginx on the host.

---

## 1. System Requirements & Dependencies

Install Docker, Nginx, and system libraries required by the project (OpenCV, WeasyPrint, PostgreSQL):

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git nginx python3-pip python3-venv \
    libpq-dev gcc python3-dev libexiv2-dev libboost-python-dev \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

---

## 2. Database Instance (Postgres)

Run the database in its own isolated Docker stack:

```bash
cd /var/www/nmk/postgres
# Ensure postgres/.env has DB credentials
docker compose up -d
```

### Database Initialization Scripts
Scripts in `./init-scripts/` are executed automatically **only when the volume is created for the first time**. 

To run `01-create-user.sql` manually on an existing database:
```bash
# Execute the script inside the running container
docker exec -i nmk_postgres psql -U postgres < ./init-scripts/01-create-user.sql
```
*(Replace `nmk_postgres` with the actual container name from `docker ps`)*

---

## 3. Backend Instance (Django)

### A. Dockerfile (`backend/Dockerfile`)
The backend requires several system libraries for PDF generation and image processing:

```dockerfile
FROM python:3.11-slim

# Install system dependencies for WeasyPrint, OpenCV, and Postgres
RUN apt-get update && apt-get install -y \
    libpq-dev gcc libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 libffi-dev shared-mime-info libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

COPY . .

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "backend.wsgi:application"]
```

### B. Docker Compose (`backend/docker-compose.yml`)
```yaml
version: '3.8'
services:
  api:
    build: .
    container_name: nmk_backend
    restart: unless-stopped
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - ./staticfiles:/app/staticfiles
      - ./media:/app/media
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - DB_HOST=host.docker.internal
```

---

## 4. Frontend Instance (React)

The frontend is built on the host and served as static files:

```bash
cd /var/www/nmk/frontend
npm install
npm run build
# Files will be in /var/www/nmk/frontend/dist
```

---

## 5. Nginx Configuration (The Glue)

Create `/etc/nginx/sites-available/nmk`:

```nginx
server {
    listen 80;
    server_name your_domain.com;

    # Frontend (React SPA)
    location / {
        root /var/www/nmk/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        include proxy_params;
    }

    # Django Admin
    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        include proxy_params;
    }

    # Static Files (CSS/JS for Admin/Templates)
    location /static/ {
        alias /var/www/nmk/backend/staticfiles/;
    }

    # Media Files (Uploads/PDFs)
    location /media/ {
        alias /var/www/nmk/backend/media/;
    }
}
```

---

## 6. Initialization & Maintenance

1. **Migrate DB:** `docker exec -it nmk_backend python manage.py migrate`
2. **Collect Static:** `docker exec -it nmk_backend python manage.py collectstatic --noinput`
3. **SSL:** `sudo certbot --nginx -d your_domain.com`
4. **Update:** `git pull && docker compose up -d --build && npm run build`


