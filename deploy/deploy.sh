#!/bin/bash
set -euo pipefail
[[ ${1:-} =~ ^[0-9a-f]{40}$ ]] || { echo 'Expected a full commit SHA'; exit 2; }
exec 9>/var/lock/swe40006-deploy.lock
flock -w 600 9
cd /opt/swe40006
umask 077
REGISTRY=612153306600.dkr.ecr.ap-southeast-2.amazonaws.com
REPO=swe40006-taskmanager
NEW_SHA=$1
NEW_IMAGE="$REGISTRY/$REPO:$NEW_SHA"
aws ecr describe-images --region ap-southeast-2 --repository-name "$REPO" --image-ids "imageTag=$NEW_SHA" --query 'imageDetails[0].imageDigest' --output text > candidate-digest.txt
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin "$REGISTRY" >/dev/null
docker pull "$NEW_IMAGE"
OLD_SHA=$(sed -n 's/^RELEASE_SHA=//p' .env)
cp .env .env.previous
sed -i "s|^IMAGE_URI=.*|IMAGE_URI=$NEW_IMAGE|;s|^RELEASE_SHA=.*|RELEASE_SHA=$NEW_SHA|" .env
if ! docker compose up -d --wait --wait-timeout 240; then
    echo 'Candidate failed readiness; restoring previous application version.'
    mv .env.previous .env
    if [[ "$OLD_SHA" =~ ^[0-9a-f]{40}$ ]]; then docker compose up -d --wait --wait-timeout 180; fi
    exit 1
fi
python3 - <<'PY'
import json, urllib.request
with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=10) as r:
    result=json.load(r)
assert result == {'database':'connected','status':'ok'}, result
print(json.dumps(result))
PY
cp candidate-digest.txt current-digest.txt
printf '%s\n' "$NEW_SHA" > current-release.txt
docker compose ps
echo "RELEASE_OK=$NEW_SHA"
