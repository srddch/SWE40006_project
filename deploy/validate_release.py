"""Require the exact successful staging run before automatic or manual promotion."""
import json
import os
import re
from pathlib import Path
import requests

sha = os.environ['CANDIDATE_SHA']
assert re.fullmatch(r'[0-9a-f]{40}', sha), 'Enter a full 40-character commit SHA'
config = json.loads(Path('deploy/environments.json').read_text())
staging_url = config['environments']['staging']['url']
health = requests.get(staging_url + '/health', timeout=15)
health.raise_for_status()
assert health.json() == {'status': 'ok', 'database': 'connected'}
assert health.headers['X-Release-SHA'] == sha, 'Candidate must match the current staging release'
assert health.headers['X-Deployment-Environment'] == 'staging'
headers = {'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json'}
api = 'https://api.github.com/repos/srddch/SWE40006_project/actions/workflows/ci.yml/runs'
response = requests.get(api, params={'head_sha': sha, 'status': 'success', 'per_page': 20}, headers=headers, timeout=15)
response.raise_for_status()
qualified = [r for r in response.json()['workflow_runs']
             if r['head_branch'] == 'main' and r['event'] in ('push', 'workflow_dispatch')]
assert qualified, 'No successful test-and-staging workflow exists for this commit'
source_run = os.environ.get('SOURCE_RUN_ID', '')
if os.environ.get('RELEASE_TRIGGER') == 'workflow_run':
    assert source_run.isdigit(), 'Automatic promotion must identify its source run'
    qualified = [r for r in qualified if str(r['id']) == source_run]
    assert qualified, 'Automatic trigger does not match the successful candidate run'
print(json.dumps({'approved_candidate': sha, 'staging_url': staging_url,
                  'qualified_run': qualified[0]['html_url'],
                  'trigger': os.environ.get('RELEASE_TRIGGER', 'workflow_dispatch'),
                  'status': 'eligible'}))
