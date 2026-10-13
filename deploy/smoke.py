"""Verify TLS, the deployed version, DB readiness and a real task workflow."""
import argparse
import json
import secrets
import time
from pathlib import Path
import requests

p = argparse.ArgumentParser()
p.add_argument('--url', required=True)
p.add_argument('--sha', required=True)
p.add_argument('--environment', required=True, choices=['staging', 'production'])
p.add_argument('--output', required=True)
args = p.parse_args()
assert args.url.startswith('https://'), 'HTTPS is required'
session = requests.Session()
deadline = time.monotonic() + 240
while True:
    try:
        health = session.get(args.url + '/health', timeout=10)
        health.raise_for_status()
        assert health.json() == {'database': 'connected', 'status': 'ok'}
        assert health.headers['X-Release-SHA'] == args.sha
        assert health.headers['X-Deployment-Environment'] == args.environment
        break
    except (requests.RequestException, AssertionError, KeyError):
        if time.monotonic() >= deadline:
            raise
        time.sleep(10)

def request(method, path, expected, **kwargs):
    if method != 'GET':
        csrf = session.get(args.url + '/api/csrf', timeout=10)
        csrf.raise_for_status()
        kwargs['headers'] = {'X-CSRFToken': csrf.json()['csrf_token']}
    response = session.request(method, args.url + path, timeout=15, **kwargs)
    assert response.status_code == expected, (path, response.status_code)
    return response

username = 'deploy_' + secrets.token_hex(8)
password = secrets.token_urlsafe(24)
credentials = {'username': username, 'password': password}
request('POST', '/api/register', 201, json=credentials)
request('POST', '/api/login', 200, json=credentials)
assert any(cookie.secure for cookie in session.cookies if cookie.name == 'session')
task = request('POST', '/api/tasks', 201, json={'title': 'Deployment smoke test'}).json()['task']
request('PATCH', '/api/tasks/' + str(task['id']), 200, json={'completed': True})
request('POST', '/api/logout', 204)
request('POST', '/api/login', 200, json=credentials)
saved = request('GET', '/api/tasks', 200).json()['tasks']
assert any(t['id'] == task['id'] and t['completed'] for t in saved)
request('DELETE', '/api/tasks/' + str(task['id']), 204)
request('POST', '/api/logout', 204)
assert session.get(args.url + '/metrics', timeout=10).status_code == 404
evidence = {'url': args.url, 'sha': args.sha, 'environment': args.environment,
            'tls_verified': True, 'database': 'connected',
            'registration_login_crud_logout_persistence': 'passed',
            'secure_session_cookie': True, 'public_metrics_blocked': True,
            'note': 'Generated smoke account retained; disposable task removed.'}
Path(args.output).parent.mkdir(parents=True, exist_ok=True)
Path(args.output).write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps(evidence, indent=2))
