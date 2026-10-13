"""Invoke the fixed deployment document and retain its non-secret result."""
import argparse
import json
import re
import time
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
        'StandardOutputContent', 'StandardErrorContent')}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(evidence, indent=2) + '\n')
    print(evidence['StandardOutputContent'])
    if result['Status'] != 'Success':
        print(evidence['StandardErrorContent'])
        raise SystemExit('Deployment failed: ' + result['Status'])
    break
else:
    raise SystemExit('Deployment timed out')
