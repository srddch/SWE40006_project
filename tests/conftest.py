import os
from threading import Thread

import pytest
from sqlalchemy.engine import make_url
from werkzeug.serving import make_server

from taskmanager import create_app
from taskmanager.models import db


@pytest.fixture
def app(tmp_path):
    url = os.getenv("TEST_DATABASE_URL", "sqlite:///" + str(tmp_path / "test.db"))
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite" and "test" not in (parsed.database or "").lower():
        raise RuntimeError("TEST_DATABASE_URL must name an isolated database containing 'test'.")
    application = create_app({"TESTING": True, "SECRET_KEY": "test-session-key-not-for-deployment",
        "SQLALCHEMY_DATABASE_URI": url, "WTF_CSRF_ENABLED": True})
    with application.app_context():
        db.drop_all()
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def live_url(app):
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=5)


def send(client, method, path, body=None):
    token = client.get("/api/csrf").get_json()["csrf_token"]
    return client.open(path, method=method, json=body, headers={"X-CSRFToken": token})


def register(client, username="alice", password="correct-password"):
    return send(client, "POST", "/api/register", {"username": username, "password": password})


def login(client, username="alice", password="correct-password"):
    return send(client, "POST", "/api/login", {"username": username, "password": password})
