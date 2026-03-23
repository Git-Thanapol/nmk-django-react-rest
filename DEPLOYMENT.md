# Deployment Guideline: NMK Project (Django + React + PostgreSQL)

This document provides a step-by-step guide for deploying the NMK project on a **Ubuntu Server** using **Docker (PostgreSQL)**, **Gunicorn**, and **Nginx**.

---

## 1. Prerequisites

### Update System & Install Dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip nginx curl git libpq-dev
```

### Install Docker (For PostgreSQL)
```bash
# Add Docker's official GPG key:
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository to Apt sources:
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

---

## 2. Project Setup

### Clone Repository
```bash
mkdir -p /var/www
sudo chown $USER:$USER /var/www
cd /var/www
git clone <repository_url> nmk
cd nmk
```

### Setup Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# If you need to install Gunicorn separately (should be in requirements.txt)
# pip install gunicorn
```

### Configure Environment Variables
Copy the `.env.example` and fill in your production values.
```bash
cp .env.example .env
nano .env
```
*Make sure `DEBUG=False` and `DB_HOST=localhost` (if Docker ports are mapped to host).*

---

## 3. Database: PostgreSQL in Docker

We use the existing `postgres/docker-compose.yml` file.

```bash
cd /var/www/nmk/postgres
# Docker compose will use values from ../backend/.env if you symlink or use -e
# For simplicity, we can symlink the .env
ln -s /var/www/nmk/backend/.env .env
docker compose up -d
```

Verify the database is running:
```bash
docker ps
```

---

## 4. Backend: Gunicorn & Systemd

### Static Files
```bash
cd /var/www/nmk/backend
source venv/bin/activate
python manage.py collectstatic --noinput
python manage.py migrate
```

### Gunicorn Configuration
Ensure `/var/www/nmk/backend/gunicorn.conf.py` exists (it's already provided in the repository).

### Create Systemd Service
```bash
sudo nano /etc/systemd/system/nmk.service
```
Paste the content of `gunicorn.service.example` from the repository (adjust paths if needed).

```bash
sudo systemctl daemon-reload
sudo systemctl start nmk
sudo systemctl enable nmk
```

Check status:
```bash
sudo systemctl status nmk
```

---

## 5. Frontend: React Build

```bash
cd /var/www/nmk/frontend
# Install Node.js if not already (using NVM is recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 20

npm install
npm run build
```
This creates a `dist/` directory in `frontend/`.

---

## 6. Nginx Setup

### Configure Nginx
```bash
sudo nano /etc/nginx/sites-available/nmk
```
Paste the content of `nginx.conf.example` from the repository.

### Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/nmk /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Fix Permissions
Nginx needs access to the static/media and socket files.
```bash
sudo usermod -aG $USER www-data
sudo chmod 710 /var/www/nmk
# Ensure /tmp/gunicorn.nmk.sock is accessible (Gunicorn does this usually)
```

---

## 7. SSL (HTTPS) with Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 8. Common Maintenance Commands

- **Restart Backend:** `sudo systemctl restart nmk`
- **View Logs:**
  - Nginx Access: `tail -f /var/log/nginx/nmk_access.log`
  - Nginx Error: `tail -f /var/log/nginx/nmk_error.log`
  - Gunicorn Error: `journalctl -u nmk -f`
- **Update Project:**
  ```bash
  cd /var/www/nmk
  git pull
  source backend/venv/bin/activate
  pip install -r backend/requirements.txt
  python backend/manage.py migrate
  python backend/manage.py collectstatic --noinput
  cd frontend && npm install && npm run build
  sudo systemctl restart nmk
  ```
