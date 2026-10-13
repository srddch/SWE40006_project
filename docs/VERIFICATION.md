# Local verification record

Verified on 13 October 2026 before the initial repository publication.

| Check | Result |
| --- | --- |
| SQLite unit/API run | 28 passed; 2 browser tests excluded from this run |
| Actual MariaDB 11.4 + Chromium acceptance run | 30 passed in 88.27 seconds |
| Backend line coverage in the MariaDB run | 99.20% (251 executable statements; 2 uncovered) |
| JavaScript syntax | account.js, script.js and api.js passed Node syntax checks |
| Docker image build | Passed on Linux Python 3.13 |
| Docker Compose readiness | MariaDB and Gunicorn/Flask services healthy |
| Browser against the Compose application | Login and saved task rendering passed |
| App restart with the same MariaDB volume | Saved task, completion flag and login session retained |
| /health and /metrics | Responded successfully |
| Final CSRF/metrics regression checks | 2 passed after request-timing initialization was adjusted |

The tests include password-hash storage, duplicate usernames, invalid inputs, failed login,
unauthenticated requests, CSRF rejection, task CRUD, user ownership boundaries, database
error handling, browser reload persistence, logout and two separate browser users.

SQLite checks used Python 3.12 on Windows. MariaDB checks used an isolated Docker database;
the app was also built and smoke-tested in its Linux Gunicorn container. Private setup
secrets, local databases, test caches and the teammate's original archive are excluded from Git.

These results are local verification, not proof of an AWS deployment or a passing remote
GitHub Actions run. The remote workflow must complete independently after publication.
