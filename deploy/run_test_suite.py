"""Run the existing complete suite inside the isolated EC2 test container."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

root = Path('/evidence')
root.mkdir(parents=True, exist_ok=True)
command = [sys.executable, '-m', 'pytest', '--cov=taskmanager',
           '--cov-report=term-missing', '--cov-report=xml:/evidence/coverage.xml',
           '--cov-fail-under=80', '--junitxml=/evidence/junit.xml',
           '--output=/evidence/browser-results', '--screenshot=only-on-failure',
           '--tracing=retain-on-failure']
started = datetime.datetime.now(datetime.timezone.utc)
completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, check=False)
(root / 'pytest.log').write_text(completed.stdout)
print(completed.stdout, end='', flush=True)
summary = {
    'execution_location': 'isolated Docker test environment on AWS staging EC2',
    'instance_id': os.environ['STAGING_INSTANCE_ID'],
    'sha': os.environ['RELEASE_SHA'],
    'test_image_digest': os.environ['TEST_IMAGE_DIGEST'],
    'started_at_utc': started.isoformat(),
    'finished_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'database': 'isolated taskmanager_test MariaDB service; no deployment volume',
    'command': command,
    'exit_code': completed.returncode,
    'status': 'failed',
}
if (root / 'junit.xml').exists():
    tree = ET.parse(root / 'junit.xml').getroot()
    suites = list(tree.iter('testsuite'))
    summary.update({name: sum(int(s.attrib.get(name, 0)) for s in suites)
                    for name in ('tests', 'failures', 'errors', 'skipped')})
if (root / 'coverage.xml').exists():
    summary['coverage_percent'] = round(
        float(ET.parse(root / 'coverage.xml').getroot().attrib['line-rate']) * 100, 2)
if (completed.returncode == 0 and summary.get('tests', 0) > 0
        and summary.get('failures', 0) == 0 and summary.get('errors', 0) == 0
        and summary.get('coverage_percent', 0) >= 80):
    summary['status'] = 'passed'
(root / 'result.json').write_text(json.dumps(summary, indent=2) + '\n')
print('STAGING_SUITE_RESULT=' + json.dumps(summary, separators=(',', ':')), flush=True)
raise SystemExit(0 if summary['status'] == 'passed' else (completed.returncode or 1))
