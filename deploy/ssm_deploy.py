"""Invoke the fixed deployment document and retain its non-secret result."""
import argparse
import base64
import io
import json
import re
import time
import tarfile
from pathlib import Path
import boto3

p = argparse.ArgumentParser()
p.add_argument('--instance', required=True)
p.add_argument('--sha', required=True)
p.add_argument('--output', required=True)
args = p.parse_args()
if not re.fullmatch(r'[0-9a-f]{40}', args.sha):
    p.error('sha must be a complete lowercase commit SHA')
client = boto3.client('ssm', region_name='ap-southeast-2')
command = client.send_command(
    InstanceIds=[args.instance], DocumentName='SWE40006-DeployTaskManager',
    Parameters={'ImageTag': [args.sha]}, TimeoutSeconds=900,
    Comment='SWE40006 immutable image deployment ' + args.sha,
)['Command']['CommandId']
deadline = time.monotonic() + 900
while time.monotonic() < deadline:
    time.sleep(10)
    try:
        result = client.get_command_invocation(CommandId=command, InstanceId=args.instance)
    except client.exceptions.InvocationDoesNotExist:
        continue
    if result['Status'] in ('Pending', 'InProgress', 'Delayed'):
        continue
    evidence = {key: result.get(key) for key in (
        'CommandId', 'InstanceId', 'Status', 'ResponseCode',
        'ExecutionStartDateTime', 'ExecutionEndDateTime',
        'StandardOutputContent', 'StandardErrorContent')}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(evidence, indent=2) + '\n')
    output = evidence['StandardOutputContent'] or ''
    for line in output.splitlines():
        if line.startswith('STAGING_TEST_ARTIFACTS_B64='):
            destination = Path(args.output).parent / 'staging-tests'
            destination.mkdir(parents=True, exist_ok=True)
            payload = base64.b64decode(line.split('=', 1)[1], validate=True)
            allowed = {'pytest.log', 'junit.xml', 'coverage.xml', 'result.json', 'test-image-digest.txt'}
            with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
                for member in archive.getmembers():
                    if member.name not in allowed or not member.isfile() or member.size > 2_000_000:
                        raise RuntimeError('Unexpected test evidence archive entry')
                    (destination / member.name).write_bytes(archive.extractfile(member).read())
            print('Staging XML, JSON and original test log retained in ' + str(destination))
        else:
            print(line)
    if result['Status'] != 'Success':
        print(evidence['StandardErrorContent'])
        raise SystemExit('Deployment failed: ' + result['Status'])
    break
else:
    raise SystemExit('Deployment timed out')
