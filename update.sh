#!/usr/bin/env bash
# Update deployment script for NMK.
# Run after pushing code changes to redeploy the web service.
# Database data and uploaded media files are never touched.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "======================================"
echo "  NMK — Update Deployment             "
echo "======================================"

# ── 1. Pull latest code ──────────────────────────────────────────────────────
echo ""
echo "Pulling latest code from git..."
git pull

# ── 2. Rebuild web image ─────────────────────────────────────────────────────
echo ""
echo "Rebuilding web image..."
docker compose build web

# ── 3. Restart web service ───────────────────────────────────────────────────
echo ""
echo "Restarting web service..."
echo "(Migrations and collectstatic run automatically via entrypoint.)"
docker compose up -d web

# ── 4. Wait and show logs ────────────────────────────────────────────────────
echo ""
echo "Following startup logs for 20 seconds — press Ctrl+C to exit (services keep running)."
sleep 3
timeout 20 docker compose logs -f web || true

# ── 5. Status ────────────────────────────────────────────────────────────────
echo ""
echo "======================================"
echo "  Status"
echo "======================================"
docker compose ps
echo ""
echo "Update complete."
