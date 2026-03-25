# Comments Service

Threaded discussion board with anonymous and authenticated posting, file attachments, captcha for guest users, soft delete, edit support, and live updates over websockets.

The project ships with a Django backend, a Vue frontend, Docker-based deployment, and a production-ready Redis channel layer for websocket fan-out across processes and containers.

## Features

- Top-level comments and nested replies
- Anonymous posting with captcha
- User registration and JWT login
- OpenAPI schema with Swagger UI and ReDoc
- Reserved usernames for registered users
- File uploads during comment and reply creation
- Attachment removal during comment edit
- Comment preview with server-side HTML sanitization
- Soft delete instead of hard delete
- Live refresh through websockets
- Pagination and ordering
- Django admin

## Stack

### Backend

- Python 3.12
- Django 6
- Django REST Framework
- Django Channels + Daphne
- Redis for cache and websocket channel layer in production
- PostgreSQL in Docker and production deployments
- SQLite + local memory cache for manual local development
- `django-simple-captcha` for guest posting
- `django-mptt` for threaded comment trees
- `django-storages` for optional S3-backed media

### Frontend

- Vue 3
- Vite
- Nginx in the frontend container for static hosting and reverse proxying

### Deployment

- Docker
- Docker Compose
- AWS EC2
- Optional S3 for media storage

## Project Layout

```text
backend/                  Django project and apps
backend/apps/comments/    Comment API, websocket events, caching, tests
backend/apps/users/       User model, JWT login, registration
frontend/                 Vue application
frontend/nginx/           Nginx config used by the frontend container
docker/backend/           Backend container entrypoint
Dockerfile                Backend image
docker-compose.yml        Full local/prod-like stack
.env.example              Environment template
```

## Main Routes

When the Docker stack is running, all public routes are served through the frontend container on `http://localhost` or `http://<host>:<FRONTEND_PORT>`.

- `GET /comments/` - list comments
- `POST /comments/` - create top-level comment
- `GET /comments/captcha/` - fetch captcha challenge for guest posting
- `POST /comments/preview/` - preview sanitized comment HTML
- `POST /comments/<id>/reply/` - create reply
- `PATCH /comments/<id>/` - edit comment
- `DELETE /comments/<id>/delete/` - soft delete comment
- `POST /api/register/` - create user account
- `POST /api/token/` - obtain JWT access and refresh tokens
- `POST /api/token/refresh/` - refresh JWT access token
- `GET /api/schema/` - raw OpenAPI schema
- `GET /api/docs/` - Swagger UI
- `GET /api/redoc/` - ReDoc
- `/admin/` - Django admin
- `ws://<host>/ws/comments/` - websocket feed for live comment updates

## Local Development

There are two supported local workflows:

- Docker Compose: closest to production
- Manual backend + frontend processes: fastest for app development

### Option 1: Docker Compose

This uses:

- PostgreSQL
- Redis
- Django running under Daphne
- Vue build served by Nginx
- production settings from the root `.env`

#### Prerequisites

- Docker
- Docker Compose plugin

#### Start

1. Copy the env template:

   ```bash
   cp .env.example .env
   ```

2. Review `.env`. For local use, the defaults are acceptable for a first run, but you should still replace secrets if the instance is reachable outside your machine.

3. Start the stack:

   ```bash
   docker compose up --build -d
   ```

4. Open:

   - Frontend: `http://localhost`
   - Comments API: `http://localhost/comments/`
   - Admin: `http://localhost/admin/`
   - JWT login: `http://localhost/api/token/`
   - Swagger UI: `http://localhost/api/docs/`
   - ReDoc: `http://localhost/api/redoc/`

#### Notes

- The backend container is not exposed directly to the host. It is reverse-proxied through the frontend Nginx container.
- On startup, the backend entrypoint runs migrations and `collectstatic`.
- If `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD` are set, the backend container also creates or updates that admin user automatically.

#### Stop

```bash
docker compose down
```

To remove named volumes too:

```bash
docker compose down -v
```

### Option 2: Run Backend and Frontend Separately

This workflow uses:

- Django dev settings by default
- SQLite database by default
- local memory cache by default
- no Redis requirement for comment listing

#### Backend

Requirements:

- Python 3.12
- `uv`

Commands:

```bash
uv sync --dev
uv run python backend/manage.py migrate
uv run python backend/manage.py runserver 127.0.0.1:8000
```

The default local backend URL is:

- `http://127.0.0.1:8000`

API documentation is also available directly from Django in manual local development:

- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- ReDoc: `http://127.0.0.1:8000/api/redoc/`
- OpenAPI schema: `http://127.0.0.1:8000/api/schema/`

#### Frontend

Requirements:

- Node.js 20+
- npm

Commands:

```bash
cd frontend
npm install
VITE_API_ORIGIN=http://127.0.0.1:8000 \
VITE_WS_ORIGIN=ws://127.0.0.1:8000 \
npm run dev
```

The default frontend dev URL is:

- `http://127.0.0.1:5173`

Without `VITE_API_ORIGIN` and `VITE_WS_ORIGIN`, the Vite dev server will try to call the API on its own origin instead of the Django backend.

## Authentication and Identity Rules

- Registered users log in with JWT.
- Registered users always post under their own account username and email.
- Anonymous users must provide username, email, and captcha.
- Anonymous users cannot use usernames that are already registered.
- Registration rejects duplicate usernames and duplicate emails.

## Configuration

The root `.env.example` documents the main production-oriented settings. The most important ones are:

- `DJANGO_SETTINGS_MODULE`
- `DJANGO_SECRET_KEY`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `CORS_ALLOWED_ORIGINS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `REDIS_URL`
- `CACHE_URL`
- `CHANNEL_LAYERS_REDIS_URL`
- `COMMENTS_CACHE_TIMEOUT`
- `SESSION_COOKIE_SECURE`
- `CSRF_COOKIE_SECURE`
- `SECURE_SSL_REDIRECT`
- `SECURE_HSTS_SECONDS`
- `USE_S3`
- `FRONTEND_PORT`
- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`

### Media Storage

By default, uploads are stored locally:

- Docker deployment: named `media_data` volume
- Manual local development: `backend/media/`

If you want durable media outside the EC2 instance, set `USE_S3=True` and provide the AWS storage credentials and bucket settings supported by Django Storages.

## AWS EC2 Deployment

This repository can be deployed directly to a single EC2 instance with Docker Compose.

### Recommended Sizing

Observed local idle container memory usage is small, but you should size the instance for build-time usage, Postgres growth, Redis, Docker overhead, logs, and uploads.

- Minimum for low traffic if you only run containers: `2 GiB RAM / 2 vCPU`
- Practical baseline if you build on the EC2 host with `docker compose up --build`: `4 GiB RAM / 2 vCPU`
- EBS volume: `20 GiB gp3` minimum
- Better upload/log headroom: `30 GiB gp3`

Reasonable choices:

- `t3.small` or `t4g.small` for very low traffic
- `t3.medium` or `t4g.medium` for safer day-one deployment

If you are not sure, start with `t3.medium` or `t4g.medium`.

### Security Group

Open only the ports you actually need:

- `22` for SSH
- `80` for HTTP
- `443` for HTTPS if you terminate TLS on the instance

Do not expose:

- `5432`
- `6379`
- backend `8000`

### Deployment Steps

1. Launch an EC2 instance.
2. Attach at least `20 GiB` of gp3 storage.
3. Install Docker and the Docker Compose plugin on the instance.
4. Clone this repository onto the instance.
5. Copy the env template:

   ```bash
   cp .env.example .env
   ```

6. Update `.env` with:

   - strong `DJANGO_SECRET_KEY`
   - strong `POSTGRES_PASSWORD`
   - strong `DJANGO_SUPERUSER_PASSWORD`
   - actual `ALLOWED_HOSTS`
   - actual `CSRF_TRUSTED_ORIGINS`
   - actual `CORS_ALLOWED_ORIGINS`
   - `FRONTEND_PORT=80` unless you need a different public port

7. Start the stack:

   ```bash
   docker compose up --build -d
   ```

8. Verify:

   ```bash
   docker compose ps
   docker compose logs backend --tail 100
   docker compose logs frontend --tail 100
   ```

9. Open the API documentation:

   - Swagger UI: `http://<your-ec2-host>/api/docs/`
   - ReDoc: `http://<your-ec2-host>/api/redoc/`
   - OpenAPI schema: `http://<your-ec2-host>/api/schema/`

### Production Settings to Enable

For a real public deployment behind HTTPS, update `.env` to use secure cookie and redirect settings:

```env
DEBUG=False
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
```

If you use subdomains and intend to preload HSTS, also enable:

```env
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

### HTTPS

The current stack serves HTTP on the frontend container. For HTTPS in production, terminate TLS in one of these places:

- AWS Application Load Balancer
- reverse proxy on the instance
- another edge layer such as CloudFront or Caddy/Nginx in front of the app

The Django production settings already support `SECURE_PROXY_SSL_HEADER`, so HTTPS termination in front of the app is the intended production pattern.

### Data Persistence on EC2

The Docker Compose deployment persists state in named volumes:

- `postgres_data`
- `redis_data`
- `media_data`
- `static_data`

This means:

- Postgres data survives container recreation
- uploaded files survive container recreation
- data does not survive instance loss unless the EBS volume survives or you back it up

For stronger durability:

- use managed Postgres instead of local Postgres
- move uploads to S3
- keep regular backups of the database volume

## Testing

Backend tests:

```bash
uv run python backend/manage.py test apps.users apps.comments.tests
```

Frontend production build:

```bash
cd frontend
npm run build
```

General Django checks:

```bash
uv run python backend/manage.py check
```

## Troubleshooting

### `OperationalError: no such table`

For manual local development, run migrations:

```bash
uv run python backend/manage.py migrate
```

### Docker stack is up but `localhost:8000` does not respond

That is expected with the current Compose setup. The backend is only available behind the frontend reverse proxy. Use:

- `http://localhost/comments/`
- `http://localhost/api/token/`
- `http://localhost/admin/`

### Docker build snapshot error

If Docker fails with a BuildKit snapshot error on the host, the issue is usually Docker cache state rather than app code. Typical recovery steps are:

```bash
docker builder prune -af
docker compose build --no-cache
```

### Uploaded files should not live on the EC2 disk

Enable S3-backed media storage and move uploads off the instance.

## Current Status

The repository currently includes:

- working registration and login
- reserved username enforcement for registered users
- comment and reply attachment uploads
- soft delete
- websocket-based live refresh
- Docker Compose deployment
- EC2-friendly production settings
