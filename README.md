"# nmk-django-react-rest" 

# nmk-django-react-rest

A full‑stack template combining Django (REST API) and React (single‑page app). This README explains the stack, tech choices, database, Docker usage, folder structure and common developer workflows.

## Stack & technologies
- Backend: Django + Django REST Framework
- Frontend: React (Create React App or similar)
- API: JSON REST endpoints
- Database: PostgreSQL (recommended for production; SQLite may be used for quick local dev)
- Containerization: Docker & docker-compose
- Dev tools: node/npm or yarn, pip, virtualenv/venv
- Optional: gunicorn + nginx for production

## Project goals
- Clear separation between API (Django) and client (React)
- Containerized local development
- Opinionated defaults for quick bootstrap and production readiness

## Prerequisites
- Docker & docker-compose
- git
- (local dev without Docker) Python 3.9+, node 14+/16+
- PostgreSQL service if not using Docker compose

## Environment variables (example)
Create a `.env` file (or supply env in docker-compose):
```
DJANGO_SECRET_KEY=replace_me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://user:password@db:5432/app_db
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=app_db
POSTGRES_HOST=db
POSTGRES_PORT=5432
FRONTEND_PORT=3000
BACKEND_PORT=8000
```

## Docker (recommended)
Typical docker-compose workflow:
- Build and start containers:
    ```
    docker-compose up --build
    ```
- Run migrations:
    ```
    docker-compose exec web python manage.py migrate
    ```
- Create superuser:
    ```
    docker-compose exec web python manage.py createsuperuser
    ```
- Stop and remove:
    ```
    docker-compose down
    ```

Common docker-compose services:
- web — Django app (gunicorn for prod or manage.py runserver for dev)
- db — PostgreSQL
- frontend — React dev server (or serve built static files in production)
- nginx — optional reverse proxy / static file server in production

## Local development (without Docker)
Backend:
```
python -m venv .venv
source .venv/bin/activate    # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
export $(cat .env | xargs)   # or set env vars individually
python manage.py migrate
python manage.py runserver
```
Frontend:
```
cd frontend
npm install
npm start      # runs dev server on :3000
npm run build  # creates production bundle
```

## Database
- Development: SQLite is acceptable for quick testing (set in Django settings)
- Production: PostgreSQL recommended
- Use Django migrations to manage schema:
    ```
    python manage.py makemigrations
    python manage.py migrate
    ```

## CORS & auth
- Configure CORS (django-cors-headers) to allow the React dev server origin (e.g., http://localhost:3000).
- Use token-based auth (DRF Token, JWT) depending on needs. Ensure secure cookies or HTTPS in production.

## Static files & media
- Collect static for production:
    ```
    python manage.py collectstatic
    ```
- Serve static files via nginx in production. Configure MEDIA_ROOT and MEDIA_URL for user uploads.

## Tests
- Backend: Django test framework or pytest-django:
    ```
    python manage.py test
    # or with pytest
    pytest
    ```
- Frontend: Jest/React Testing Library:
    ```
    cd frontend
    npm test
    ```

## Folder structure (example)
- backend/ or server/
    - manage.py
    - project_name/
        - settings.py
        - urls.py
        - wsgi.py
    - apps/
        - app1/
        - app2/
    - requirements.txt
- frontend/
    - package.json
    - public/
    - src/
        - components/
        - pages/
        - services/    (API clients)
- docker-compose.yml
- Dockerfile (backend)
- Dockerfile.frontend (optional)
- .env
- README.md

Adjust paths/names to match actual repository layout.

## Useful commands
- Build and run containers: `docker-compose up --build`
- Run Django shell: `docker-compose exec web python manage.py shell`
- Run migrations: `docker-compose exec web python manage.py migrate`
- Rebuild frontend production bundle: `cd frontend && npm run build`
- Linting: `flake8` (Python), `eslint` (JS/React)

## Deployment notes
- Use gunicorn for Django in production behind nginx.
- Use environment variables for secrets and DB credentials.
- Use HTTPS and secure cookies for auth.
- Consider CI pipelines to run tests, lint, and build artifacts.

## Troubleshooting
- "Cannot connect to DB" — ensure DB service is up and credentials match `.env`.
- Migrations failing — check applied migrations and database permissions.
- CORS errors — add dev origin to CORS whitelist.

## Next steps for this repo
- Add CI (GitHub Actions) to test and build.
- Add health checks and monitoring.
- Implement production-ready Dockerfiles and nginx configuration.

License and contribution guidelines: add LICENSE and CONTRIBUTING.md as needed.

<!-- End of README -->