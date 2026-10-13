from datetime import timedelta
import os
from pathlib import Path
import secrets
import time

import click
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request, send_from_directory
from flask_wtf.csrf import CSRFError, CSRFProtect
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash

from .api import ValidationError, api
from .models import db

csrf = CSRFProtect()


def create_app(test_config=None):
    project = Path(__file__).resolve().parent.parent
    load_dotenv(project / ".env", override=False)
    production = os.getenv("APP_ENV", "development").lower() == "production"
    secret = os.getenv("SECRET_KEY", "")
    database = os.getenv("DATABASE_URL", "sqlite:///taskmanager.db")
    if production and (len(secret) < 32 or database.startswith("sqlite:")):
        raise RuntimeError("Production requires a SECRET_KEY of at least 32 characters and a MariaDB DATABASE_URL.")
    app = Flask(__name__, static_folder=str(project / "frontend"), static_url_path="/static")
    app.config.update(
        SECRET_KEY=secret or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI=database,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=production,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
        MAX_CONTENT_LENGTH=65536,
        DUMMY_PASSWORD_HASH=generate_password_hash(secrets.token_hex(16)),
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    app.register_blueprint(api)

    registry = CollectorRegistry()
    requests = Counter("taskmanager_http_requests_total", "HTTP requests", ["method", "endpoint", "status"], registry=registry)
    latency = Histogram("taskmanager_http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"], registry=registry)
    app.extensions["metrics_registry"] = registry

    @app.before_request
    def start_timer():
        g.request_started = time.perf_counter()

    csrf.init_app(app)

    @app.after_request
    def response_headers(response):
        if request.path != "/metrics":
            endpoint = request.endpoint or "unmatched"
            requests.labels(request.method, endpoint, str(response.status_code)).inc()
            latency.labels(request.method, endpoint).observe(time.perf_counter() - getattr(g, "request_started", time.perf_counter()))
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    @app.get("/index.html")
    def dashboard():
        return send_from_directory(project / "frontend", "index.html")

    @app.get("/account.html")
    def account():
        return send_from_directory(project / "frontend", "account.html")

    @app.get("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            # Readiness includes schema initialization, not just a TCP connection.
            db.session.execute(text("SELECT id FROM users LIMIT 1"))
            return jsonify(status="ok", database="connected")
        except SQLAlchemyError:
            db.session.rollback()
            return jsonify(status="unavailable", database="unavailable"), 503

    @app.get("/metrics")
    def metrics():
        return generate_latest(registry), 200, {"Content-Type": CONTENT_TYPE_LATEST}

    @app.cli.command("init-db")
    def init_db():
        """Create missing tables without deleting existing application data."""
        db.create_all()
        click.echo("Database tables are ready.")

    @app.errorhandler(ValidationError)
    def validation_error(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return jsonify(error="CSRF validation failed. Refresh the page and try again."), 400

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        app.logger.warning("Database operation failed.")
        return jsonify(error="Database unavailable. Please try again later."), 503

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error=error.description), error.code
        return error

    return app
