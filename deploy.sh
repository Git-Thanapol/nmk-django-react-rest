#!/usr/bin/env bash
# First-time deployment script for NMK (fully Dockerized).
# Run once on a fresh VPS after cloning the repository.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "======================================"
echo "  NMK — First-Time Docker Deployment  "
echo "======================================"

# ── 1. Check prerequisites ───────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "ERROR: docker not found. Install Docker first."
  echo "  https://docs.docker.com/engine/install/ubuntu/"
  exit 1
fi

if ! docker compose version &>/dev/null; then
  echo "ERROR: 'docker compose' plugin not found."
  echo "  Install docker-compose-plugin: sudo apt install docker-compose-plugin"
  exit 1
fi

if ! command -v openssl &>/dev/null; then
  echo "ERROR: openssl not found. Run: sudo apt install openssl"
  exit 1
fi

# ── 2. Ensure .env exists ────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo ""
  echo "No .env file found. Copying env.docker.example → .env ..."
  cp env.docker.example .env
  echo ""
  echo "ACTION REQUIRED: Fill in all 'changeme_*' values in .env, then re-run this script."
  echo ""
  echo "  nano .env"
  echo ""
  exit 1
fi

# Warn if placeholder values remain
if grep -q "changeme_" .env; then
  echo ""
  echo "WARNING: .env still contains placeholder values (changeme_*)."
  echo "         Edit .env before deploying to production."
  echo ""
  read -rp "Continue anyway? [y/N] " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
fi

# ── 3. Generate self-signed TLS certificate if missing ───────────────────────
CERT_DIR="$REPO_ROOT/docker/nginx/certs"
if [ ! -f "$CERT_DIR/cert.pem" ]; then
  echo ""
  echo "Generating self-signed TLS certificate..."
  mkdir -p "$CERT_DIR"

  SERVER_IP=$(grep -E '^ALLOWED_HOSTS=' .env | cut -d'=' -f2- | tr ',' '\n' | head -1 | tr -d ' ')
  SERVER_IP="${SERVER_IP:-127.0.0.1}"

  openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
    -keyout "$CERT_DIR/key.pem" \
    -out    "$CERT_DIR/cert.pem" \
    -subj   "/CN=${SERVER_IP}" \
    -addext "subjectAltName=IP:${SERVER_IP}" \
    2>/dev/null

  echo "  Certificate valid for ${SERVER_IP}, saved to $CERT_DIR"
fi

# ── 4. Build & start ─────────────────────────────────────────────────────────
echo ""
echo "Building Docker images (this may take a few minutes on first run)..."
docker compose build

echo ""
echo "Starting services..."
docker compose up -d

# ── 5. Wait and show startup logs ────────────────────────────────────────────
echo ""
echo "Waiting for web service to complete startup (migrations + collectstatic)..."
echo "Following logs for 30 seconds — press Ctrl+C to exit logs (services keep running)."
sleep 3
timeout 30 docker compose logs -f web || true

# ── 6. Final status ──────────────────────────────────────────────────────────
echo ""
echo "======================================"
echo "  Status"
echo "======================================"
docker compose ps

SERVER_IP=$(grep -E '^ALLOWED_HOSTS=' .env | cut -d'=' -f2- | tr ',' '\n' | head -1 | tr -d ' ')
echo ""
echo "Done! Open: https://${SERVER_IP:-your.server.ip}/"
echo "(Accept the self-signed certificate warning in your browser.)"
echo ""
echo "Useful commands:"
echo "  docker compose logs -f web          # live Django logs"
echo "  docker compose exec web python manage.py createsuperuser"
echo "  docker compose ps                   # service status"
echo "  ./update.sh                         # deploy code updates"
