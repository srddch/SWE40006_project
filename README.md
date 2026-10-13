SWE40006 Project

A task manager built to demonstrate a DevOps workflow using Flask, MariaDB, Docker and GitHub Actions.

Features

User registration, login and logout

Task creation, editing, completion and deletion

Persistent database storage and user data isolation

Automated API and browser tests

Health checks and Prometheus metrics

Run Locally

Requires Python and Docker Desktop.

python scripts/setup_local.py
docker compose up --build -d

Open http://localhost:8000/account.html and register an account.

Documentation

docs/API.md — API routes and frontend integration

docs/VERIFICATION.md — verification results

GitHub Actions runs automated tests and builds the Docker image.
