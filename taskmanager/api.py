from functools import wraps
import re

from flask import Blueprint, current_app, g, jsonify, request, session
from flask_wtf.csrf import generate_csrf
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from .models import Task, User, db

api = Blueprint("api", __name__, url_prefix="/api")


class ValidationError(ValueError):
    pass


def json_body(allowed):
    if not request.is_json:
        raise ValidationError("Send a JSON object with Content-Type: application/json.")
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError("The request body must be a JSON object.")
    if set(body) - allowed:
        raise ValidationError("The request contains unsupported fields.")
    return body


def credentials(body, registering=False):
    username = body.get("username")
    password = body.get("password")
    if not isinstance(username, str) or not re.fullmatch(r"[\w.-]{3,50}", username.strip()):
        raise ValidationError("Username must contain 3-50 letters, numbers, dots, hyphens or underscores.")
    if not isinstance(password, str) or not 1 <= len(password) <= 128:
        raise ValidationError("Password must contain 1-128 characters.")
    if registering and len(password) < 8:
        raise ValidationError("Password must contain at least 8 characters.")
    return username.strip(), password


def task_values(body, creating=False):
    if not body:
        raise ValidationError("Provide at least one task field.")
    values = {}
    if creating or "title" in body:
        title = body.get("title")
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
            raise ValidationError("Task title must contain 1-200 characters.")
        values["title"] = title.strip()
    if creating or "description" in body:
        description = body.get("description", "")
        if not isinstance(description, str) or len(description) > 5000:
            raise ValidationError("Description must be text of at most 5000 characters.")
        values["description"] = description.strip()
    if "completed" in body:
        if not isinstance(body["completed"], bool):
            raise ValidationError("Completed must be a JSON boolean.")
        values["completed"] = body["completed"]
    return values


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if isinstance(user_id, int) else None
        if user is None:
            return jsonify(error="Please log in."), 401
        g.user = user
        return view(*args, **kwargs)
    return wrapped


def owned_task(task_id):
    return db.session.scalar(db.select(Task).where(Task.id == task_id, Task.user_id == g.user.id))


@api.get("/csrf")
def csrf_token():
    return jsonify(csrf_token=generate_csrf())


@api.post("/register")
def register():
    username, password = credentials(json_body({"username", "password"}), registering=True)
    user = User(username=username, username_key=username.casefold(), password_hash=generate_password_hash(password))
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="Username already exists."), 409
    return jsonify(user=user.to_dict()), 201


@api.post("/login")
def login():
    username, password = credentials(json_body({"username", "password"}))
    user = db.session.scalar(db.select(User).where(User.username_key == username.casefold()))
    # Hash a dummy value for an unknown user to keep the password-check path similar.
    stored_hash = user.password_hash if user else current_app.config["DUMMY_PASSWORD_HASH"]
    valid = check_password_hash(stored_hash, password)
    if not user or not valid:
        return jsonify(error="Incorrect username or password."), 401
    session.clear()
    session["user_id"] = user.id
    session.permanent = True
    return jsonify(user=user.to_dict())


@api.post("/logout")
def logout():
    session.clear()
    return "", 204


@api.get("/me")
@login_required
def me():
    return jsonify(user=g.user.to_dict())


@api.get("/tasks")
@login_required
def list_tasks():
    tasks = db.session.scalars(db.select(Task).where(Task.user_id == g.user.id).order_by(Task.id)).all()
    return jsonify(tasks=[task.to_dict() for task in tasks])


@api.post("/tasks")
@login_required
def create_task():
    values = task_values(json_body({"title", "description", "completed"}), creating=True)
    task = Task(user_id=g.user.id, **values)
    db.session.add(task)
    db.session.commit()
    return jsonify(task=task.to_dict()), 201


@api.get("/tasks/<int:task_id>")
@login_required
def get_task(task_id):
    task = owned_task(task_id)
    if task is None:
        return jsonify(error="Task not found."), 404
    return jsonify(task=task.to_dict())


@api.patch("/tasks/<int:task_id>")
@login_required
def update_task(task_id):
    task = owned_task(task_id)
    if task is None:
        return jsonify(error="Task not found."), 404
    values = task_values(json_body({"title", "description", "completed"}))
    for key, value in values.items():
        setattr(task, key, value)
    db.session.commit()
    return jsonify(task=task.to_dict())


@api.delete("/tasks/<int:task_id>")
@login_required
def delete_task(task_id):
    task = owned_task(task_id)
    if task is None:
        return jsonify(error="Task not found."), 404
    db.session.delete(task)
    db.session.commit()
    return "", 204
