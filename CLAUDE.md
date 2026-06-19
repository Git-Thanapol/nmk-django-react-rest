# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**nmk** is a Django-based Business Management System (ERP/POS) for Thai market operations. It handles multi-company inventory management, purchasing, sales, and e-commerce platform integration (Shopee, Lazada, TikTok) with Thai tax compliance features.

## Development Commands

### Backend (Django)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Run development server
python manage.py runserver

# Run tests
python manage.py test api

# Custom management commands
python manage.py import_products
python manage.py import_mapping

# Collect static files (production)
python manage.py collectstatic
```

### Database (PostgreSQL via Docker)

```bash
cd postgres
docker-compose up -d       # Start PostgreSQL
docker-compose down        # Stop PostgreSQL
```

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev      # Dev server with HMR
npm run build    # Production build
npm run lint     # ESLint
```

## Architecture

### Backend Structure

The Django project lives in `backend/`. There is a single Django app `api/` that contains all business logic (monolithic structure). Settings are in `backend/backend/settings.py`.

**Key files:**
- `api/models.py` — All database models (~726 lines)
- `api/views.py` — All views, both Django template views and DRF APIViews (~1392 lines)
- `api/urls.py` — URL routing for both template views and REST API
- `api/forms.py` — Django ModelForms and FormSets for inline items
- `api/admin.py` — Admin configuration with custom actions
- `api/tasks.py` — Background threading for CSV imports (no Celery)

**Utility modules (`api/utils_*.py`):**
- `utils_processors.py` — Parses Shopee/Lazada/TikTok CSV files into pandas DataFrames
- `utils_import_core.py` — Converts DataFrames into Invoice + InvoiceItem records
- `utils_pdf.py` — WeasyPrint HTML→PDF for Withholding Tax certificates
- `utils_reports.py` — Purchase/Sales VAT tax reports and stock reports via openpyxl
- `utils_vat_import.py` / `utils_vat_export.py` — VAT data import and Excel export
- `utils_product_mapping.py` — SKU mapping logic for platform products

### Core Data Models

Multi-company support: most models carry a `company` FK.

- **Company** — Legal entities; all other models belong to a company
- **Product** — Master catalog with SKU, cost price, selling price; `current_stock` is a computed property (purchased qty minus sold qty)
- **ProductMapping / ProductAlias** — Maps platform product names → internal SKUs (prevents duplicates across platforms)
- **Vendor** — Suppliers linked to companies
- **SellingChannel** — Dynamic sales channels (Shopee, Lazada, TikTok, etc.)
- **PurchaseOrder / PurchaseItem** — Purchase orders with FIFO/batch cost tracking
- **Invoice / InvoiceItem** — Sales invoices; InvoiceItem stores `cost_price` at time of sale for profit tracking
- **WithholdingTaxCert** — Thai 50 Tawi certificates
- **Transaction** — General ledger entries
- **ImportLog** — Audit trail for platform CSV imports (PROCESSING → COMPLETED/FAILED)

### URL Structure

Template-based views serve the main business UI:
- `/purchases/`, `/invoices/`, `/products/`, `/vendors/`, `/transactions/`
- `/import/platforms/` — Shopee/Lazada/TikTok CSV upload
- `/reports/`, `/vat-tracking/`, `/tax/50tawi/`
- `/companies/`

REST API (DRF, JWT-protected):
- `/api/token/`, `/api/token/refresh/`, `/api/user/register/`
- `/api/notes/` — CRUD for React frontend
- `/api/vat/import/`, `/api/vat/report/`, `/api/vat/export/`
- `/api/vat/buy-orders/`
- `/api/purchases/check-duplicate/`

### Authentication

- Django session auth for template views
- JWT (djangorestframework-simplejwt) for REST API (30min access token, 1-day refresh)
- React frontend uses JWT and stores tokens client-side

### Frontend

React 19 + Vite SPA in `frontend/`. Currently minimal — the main business UI uses Django templates. The React SPA handles: Login/Register, Notes, and VAT Tracking pages. `frontend/src/api.js` wraps fetch with JWT handling; `frontend/src/constants.js` defines the backend base URL.

### Background Processing

CSV imports run via Python `threading` (no Celery). `tasks.py:run_import_background()` processes files, updates `ImportLog` status, and stores error reports as Excel files.

### Thai-Specific Features

- `pybaht` — converts numbers to Thai Baht text for invoices
- `Asia/Bangkok` timezone, Thai locale throughout
- Withholding Tax (50 Tawi) certificate PDF generation (4-copy layout)
- Purchase/Sales VAT tax reports in Thai format

## Environment Configuration

Copy `backend/.env` for local dev. Key variables:

```
DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
SECRET_KEY
ALLOWED_HOSTS
DEBUG=True
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
CSRF_TRUSTED_ORIGINS=
```

Production uses `backend/.env.prod` with `DEBUG=False` and secure cookie/HTTPS settings. Security settings (`SECURE_SSL_REDIRECT`, `HSTS`, secure cookies) are toggled via env vars in `settings.py`.

## Deployment

Production stack: Gunicorn + Nginx on Ubuntu, PostgreSQL in Docker. See `DEPLOYMENT.md` for the full guide.

```bash
# Production startup
gunicorn backend.wsgi:application --workers 8 --bind 0.0.0.0:8000
```
