# Frontend/backend API contract

All API responses are JSON except successful logout/delete responses (204, no body).
Frontend pages and API are served by Flask on the same origin. Authentication is a
signed, HttpOnly session cookie, not a localStorage username or a client-supplied user ID.

## CSRF

Before a POST/PATCH/DELETE, fetch `GET /api/csrf` and put the returned `csrf_token` in
the `X-CSRFToken` header. Send cookies (`credentials: "same-origin"`). Fetch a new token
after login or logout because the session changes. `frontend/api.js` handles this.
Send JSON bodies with `Content-Type: application/json`.

## Routes

| Method | Route | Request | Success |
| --- | --- | --- | --- |
| GET | `/api/csrf` | None | 200 `{"csrf_token":"..."}` |
| POST | `/api/register` | `{"username":"alice","password":"choose-a-password"}` | 201 `{"user":{"id":1,"username":"alice"}}` |
| POST | `/api/login` | Same credentials | 200 user object; sets session cookie |
| POST | `/api/logout` | None | 204; clears session cookie |
| GET | `/api/me` | None | 200 current user object |
| GET | `/api/tasks` | None | 200 `{"tasks":[...]}` |
| POST | `/api/tasks` | `{"title":"Task","description":"Details","completed":false}` | 201 `{"task":{...}}` |
| GET | `/api/tasks/<id>` | None | 200 task object |
| PATCH | `/api/tasks/<id>` | One or more of title/description/completed | 200 updated task object |
| DELETE | `/api/tasks/<id>` | None | 204 |
| GET | `/health` | None | 200 ready; 503 if database/schema unavailable |
| GET | `/metrics` | None | Prometheus text exposition |

Task format:

```json
{"id":1,"user_id":1,"title":"Task","description":"Details","completed":false}
```

- IDs are server-generated integers. Do not create IDs in the browser.
- Username: 3-50 Unicode letters/numbers, underscores, dots or hyphens; comparison is case-insensitive.
- New password: 8-128 characters. Only a hash is stored; hashes/passwords are never returned.
- Title: 1-200 characters after trimming. Description: optional text, maximum 5000 characters.
- Completed: a JSON boolean. Unknown fields, including caller-supplied `user_id`, are rejected.
- Users only see their own tasks. Requests for another user's task return 404.
- Errors use `{"error":"Human-readable message"}`. Common codes: 400 invalid input/CSRF,
  401 not logged in/invalid credentials, 404 task not found, 409 duplicate username, 503 database unavailable.

Registration does not log the user in automatically. Login redirects to the dashboard;
logout redirects to the account page. Browser refresh reloads saved tasks from the database.
Opening the HTML files directly is no longer a supported mode: start the Flask server.

## Database initialization

`flask --app wsgi init-db` creates missing `users` and `tasks` tables. It does not delete
existing rows. Back up and explicitly migrate deployed databases before schema changes.
