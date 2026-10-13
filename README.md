# SWE40006 Project

Containerised task manager for SWE40006 Software Deployment and Evolution.
The frontend is based on the teammate's `n9w4k05.zip`. Its HTML/CSS layout is retained,
with JavaScript connected to a Flask API instead of browser localStorage.

## Implemented

- Registration, login, current-user lookup and logout using signed session cookies.
- MariaDB-compatible user/task models, password hashing and case-insensitive usernames.
- Task creation, listing, detail, editing, completion and deletion.
- Server-side task ownership checks, input validation and CSRF protection.
- JSON health checks and application HTTP metrics for Prometheus.
- API/integration tests, browser acceptance tests and a GitHub Actions verification workflow.
- Docker Compose starter with MariaDB persistent storage and database readiness checks.

AWS EC2/ECR deployment, staging approval configuration, Node Exporter and Grafana hosting
remain integration work for the DevOps team member. This repository does not provision
cloud resources or claim that a production deployment has already been completed.

## Quick start: Docker + MariaDB

Install Python and Docker Desktop, then run from the repository root:

```powershell
python scripts/setup_local.py
docker compose up --build -d
docker compose ps
```

Open http://localhost:8000/account.html. Register a new account; there are no seeded users.
The setup script creates a private `.env` with random session/database secrets.
Both the database and application are initialized automatically by Compose.
Normal `docker compose down` keeps the database volume; `down -v` deletes it.
The starter binds the website to localhost and does not expose the database port.

## Windows development without Docker

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts/setup_local.py
.\.venv\Scripts\python.exe -m flask --app wsgi init-db
.\.venv\Scripts\python.exe -m flask --app wsgi run --host 127.0.0.1 --port 8000
```

This development option uses a persistent SQLite file under `instance/`.
MariaDB is the project deployment database and is used by Docker Compose and CI.
Set `DATABASE_URL` in the private `.env` to use an existing MariaDB database locally.
Do not use Flask's development server for production.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not e2e" --cov=taskmanager --cov-report=term-missing --cov-fail-under=80
.\.venv\Scripts\python.exe -m playwright install chromium --only-shell
.\.venv\Scripts\python.exe -m pytest -m e2e
```

Tests use a temporary SQLite database by default. For actual MariaDB integration tests,
set `TEST_DATABASE_URL` to a separate database whose name contains `test`, then run the
same commands. Test fixtures drop and recreate tables in that database: **never point
TEST_DATABASE_URL at development, staging or production data**.

CI runs tests against an isolated MariaDB service, checks at least 80% backend line
coverage, runs Chromium acceptance tests, and builds the Docker image after tests pass.
Test reports, coverage and browser failure artifacts are retained by the workflow.

## Team handoff

- Frontend: edit `frontend/`; use the shared `taskApi` helper and the API contract in `docs/API.md`.
- Backend: `taskmanager/`, `tests/`, schema initialization and environment configuration.
- DevOps: use `Dockerfile`, `compose.yaml`, `.github/workflows/ci.yml`, `/health` and `/metrics`
  when adding ECR publication, staging, approval-gated production deployment and monitoring.
- Use separate Compose project names, databases, volumes and secrets for each environment.

Gunicorn uses one worker and four threads so the starter's in-process metrics are complete.
If adding multiple workers, implement the Prometheus client's multiprocess configuration.
Production requires `APP_ENV=production`, a random `SECRET_KEY` of at least 32 characters,
MariaDB, and HTTPS before login cookies will work. Add a reverse proxy/TLS and restrict
metrics access at the infrastructure layer. Login rate limiting is a further production
hardening task. Schema creation is non-destructive but does not migrate existing columns;
introduce explicit migrations when changing a deployed schema.

## Source and reference

The original teammate archive is kept locally at `reference/frontend-original.zip` on the
creator's desktop and is intentionally excluded from Git. Python caches and the unfinished
Selenium placeholder from the archive were not imported into the application.

- [Flask authentication tutorial](https://flask.palletsprojects.com/en/stable/tutorial/views/)
- [SQLAlchemy MariaDB support](https://docs.sqlalchemy.org/en/20/dialects/mysql.html)
- [Docker Compose readiness](https://docs.docker.com/compose/how-tos/startup-order/)
- [Playwright pytest integration](https://playwright.dev/python/docs/test-runners)
- [Prometheus multiprocess mode](https://prometheus.github.io/client_python/multiprocess/)
