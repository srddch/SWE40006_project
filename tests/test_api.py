import pytest
from werkzeug.security import check_password_hash

from taskmanager.api import ValidationError, task_values
from taskmanager.models import User, db
from conftest import login, register, send


def test_registration_persists_only_password_hash(app, client):
    response = register(client)
    assert response.status_code == 201
    assert set(response.json["user"]) == {"id", "username"}
    with app.app_context():
        user = db.session.scalar(db.select(User))
        assert user.password_hash != "correct-password"
        assert check_password_hash(user.password_hash, "correct-password")


def test_duplicate_username_is_case_insensitive(client):
    assert register(client, "Alice").status_code == 201
    assert register(client, "alice").status_code == 409


@pytest.mark.parametrize("body", [
    {"username":"a", "password":"correct-password"},
    {"username":"alice", "password":"short"},
    {"username":None, "password":"correct-password"},
    {"username":"alice", "password":42},
    {"username":"alice", "password":"correct-password", "role":"admin"},
])
def test_invalid_registration_is_rejected(client, body):
    assert send(client, "POST", "/api/register", body).status_code == 400


def test_login_and_logout_session(client):
    register(client)
    assert login(client, password="wrong-password").status_code == 401
    assert login(client, username="unknown").status_code == 401
    assert login(client, username="ALICE").status_code == 200
    assert client.get("/api/me").json["user"]["username"] == "alice"
    assert send(client, "POST", "/api/logout").status_code == 204
    assert client.get("/api/me").status_code == 401


@pytest.mark.parametrize("method,path,body", [
    ("GET","/api/tasks",None), ("GET","/api/tasks/1",None),
    ("POST","/api/tasks",{"title":"test"}),
    ("PATCH","/api/tasks/1",{"title":"test"}),
    ("DELETE","/api/tasks/1",None),
])
def test_task_routes_require_login(client, method, path, body):
    assert send(client, method, path, body).status_code == 401


def test_task_crud_and_persistence_across_sessions(app, client):
    register(client)
    login(client)
    created = send(client, "POST", "/api/tasks", {"title":"  First task  ","description":"Details"})
    assert created.status_code == 201
    task = created.json["task"]
    assert task["title"] == "First task" and task["completed"] is False
    task_id = task["id"]
    assert client.get(f"/api/tasks/{task_id}").json["task"] == task
    updated = send(client, "PATCH", f"/api/tasks/{task_id}", {"title":"Updated", "completed":True})
    assert updated.json["task"]["completed"] is True
    other_session = app.test_client()
    login(other_session)
    assert other_session.get("/api/tasks").json["tasks"][0]["title"] == "Updated"
    assert send(client,"DELETE",f"/api/tasks/{task_id}").status_code == 204
    assert client.get("/api/tasks").json == {"tasks":[]}
    assert client.get(f"/api/tasks/{task_id}").status_code == 404
    assert send(client,"PATCH",f"/api/tasks/{task_id}",{"title":"gone"}).status_code == 404
    assert send(client,"DELETE",f"/api/tasks/{task_id}").status_code == 404


def test_users_cannot_access_or_change_each_others_tasks(app, client):
    register(client)
    login(client)
    task_id = send(client,"POST","/api/tasks",{"title":"Private"}).json["task"]["id"]
    bob = app.test_client()
    register(bob,"bobby")
    login(bob,"bobby")
    assert bob.get("/api/tasks").json == {"tasks":[]}
    assert bob.get(f"/api/tasks/{task_id}").status_code == 404
    assert send(bob,"PATCH",f"/api/tasks/{task_id}",{"title":"Stolen"}).status_code == 404
    assert send(bob,"DELETE",f"/api/tasks/{task_id}").status_code == 404
    assert send(bob,"POST","/api/tasks",{"title":"Spoofed","user_id":1}).status_code == 400
    assert client.get(f"/api/tasks/{task_id}").json["task"]["title"] == "Private"


@pytest.mark.parametrize("body", [{"title":" "}, {"title":5}, {"title":"x"*201},
    {"title":"task","description":None}, {"title":"task","description":"x"*5001},
    {"title":"task","completed":"false"}])
def test_invalid_task_payloads(client, body):
    register(client)
    login(client)
    assert send(client,"POST","/api/tasks",body).status_code == 400


def test_empty_patch_and_non_object_json(client):
    register(client)
    login(client)
    task_id = send(client,"POST","/api/tasks",{"title":"task"}).json["task"]["id"]
    assert send(client,"PATCH",f"/api/tasks/{task_id}",{}).status_code == 400
    assert send(client,"POST","/api/tasks",[]).status_code == 400
    token = client.get("/api/csrf").json["csrf_token"]
    assert client.post("/api/tasks",data="invalid",headers={"X-CSRFToken":token}).status_code == 400


def test_missing_and_invalid_csrf_tokens_block_writes(client):
    payload = {"username":"alice","password":"correct-password"}
    assert client.post("/api/register",json=payload).status_code == 400
    assert client.post("/api/register",json=payload,headers={"X-CSRFToken":"forged"}).status_code == 400
    assert register(client).status_code == 201


def test_health_checks_schema_and_database(app, client):
    assert client.get("/health").json == {"status":"ok","database":"connected"}
    with app.app_context():
        db.drop_all()
    assert client.get("/health").status_code == 503


def test_static_files_errors_and_metrics(client):
    assert client.get("/").status_code == 200
    assert client.get("/account.html").status_code == 200
    assert 'id="register-message"' in client.get("/account.html").text
    assert client.get("/static/api.js").status_code == 200
    assert client.get("/api/missing").status_code == 404
    assert "taskmanager_http_requests_total" in client.get("/metrics").text
    assert client.get("/api/csrf").headers["Cache-Control"] == "no-store"


def test_init_db_is_non_destructive(app, client):
    register(client)
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0
    with app.app_context():
        assert db.session.scalar(db.select(User)).username == "alice"


def test_database_errors_are_safe_json(app, client):
    with app.app_context():
        db.drop_all()
    response = register(client)
    assert response.status_code == 503
    assert response.json == {"error":"Database unavailable. Please try again later."}


def test_unit_task_validation():
    assert task_values({"title":" hello ","description":" details ","completed":True},True) == {
        "title":"hello","description":"details","completed":True}
    with pytest.raises(ValidationError):
        task_values({})
