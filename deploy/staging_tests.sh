#!/bin/bash
# Run on staging only, from the fixed SSM deployment command under its host lock.
set -euo pipefail
[[ ${1:-} =~ ^[0-9a-f]{40}$ ]] || { echo 'Expected full commit SHA'; exit 2; }
SHA=$1
REGISTRY=612153306600.dkr.ecr.ap-southeast-2.amazonaws.com
REPOSITORY=swe40006-taskmanager
TEST_IMAGE="$REGISTRY/$REPOSITORY:test-$SHA"
RUN="swe40006-test-${SHA:0:12}-$$"
DB="$RUN-db"
RUNNER="$RUN-runner"
EVIDENCE="/opt/swe40006/test-evidence/$SHA/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$EVIDENCE"
chmod 700 "$EVIDENCE"
cleanup() {
    # Only this test run's containers/network/anonymous test DB volume are removed.
    docker rm -fv "$RUNNER" "$DB" >/dev/null 2>&1 || true
    docker network rm "$RUN" >/dev/null 2>&1 || true
}
trap cleanup EXIT
aws ecr describe-images --region ap-southeast-2 --repository-name "$REPOSITORY" \
    --image-ids "imageTag=test-$SHA" --query 'imageDetails[0].imageDigest' \
    --output text > "$EVIDENCE/test-image-digest.txt"
DIGEST=$(cat "$EVIDENCE/test-image-digest.txt")
[[ $DIGEST =~ ^sha256:[0-9a-f]{64}$ ]] || exit 2
docker pull "$TEST_IMAGE" > "$EVIDENCE/image-pull.log" 2>&1
docker network create --label swe40006.purpose=isolated-tests "$RUN" >/dev/null
docker run -d --name "$DB" --network "$RUN" --memory=192m --memory-swap=384m \
    --label swe40006.purpose=isolated-tests \
    -e MARIADB_DATABASE=taskmanager_test -e MARIADB_USER=test_runner \
    -e MARIADB_PASSWORD=isolated-test-only -e MARIADB_ROOT_PASSWORD=isolated-test-root-only \
    --health-cmd='healthcheck.sh --connect --innodb_initialized' \
    --health-interval=2s --health-timeout=3s --health-retries=60 \
    mariadb:11.4 --innodb-buffer-pool-size=32M --max-connections=15 >/dev/null
READY=false
for _ in $(seq 1 120); do
    if [[ $(docker inspect --format '{{.State.Health.Status}}' "$DB") == healthy ]]; then
        READY=true; break
    fi
    sleep 2
done
if [[ $READY != true ]]; then docker logs "$DB"; exit 1; fi
echo "STAGING_TEST_HOST=$(hostname)"
echo "STAGING_TEST_SHA=$SHA"
echo "STAGING_TEST_IMAGE_DIGEST=$DIGEST"
set +e
timeout --signal=TERM --kill-after=15s 600 docker run --name "$RUNNER" --network "$RUN" --memory=512m --memory-swap=1g \
    --shm-size=128m --pids-limit=256 --init --cap-drop=ALL \
    --security-opt=no-new-privileges --label swe40006.purpose=isolated-tests \
    -e RELEASE_SHA="$SHA" -e TEST_IMAGE_DIGEST="$DIGEST" \
    -e STAGING_INSTANCE_ID=i-088f4da7f4434ea8e \
    -e "TEST_DATABASE_URL=mysql+pymysql://test_runner:isolated-test-only@$DB:3306/taskmanager_test?charset=utf8mb4" \
    -v "$EVIDENCE:/evidence" "$TEST_IMAGE" > "$EVIDENCE/container.log" 2>&1
RESULT=$?
set -e
if [[ -f "$EVIDENCE/pytest.log" ]]; then cat "$EVIDENCE/pytest.log"; else cat "$EVIDENCE/container.log"; fi
if [[ -f "$EVIDENCE/result.json" ]]; then
    python3 -c 'import json,sys; print("STAGING_SUITE_RESULT="+json.dumps(json.load(open(sys.argv[1])),separators=(",",":")))' "$EVIDENCE/result.json"
fi
# Compress the XML/log/JSON evidence so it fits the bounded SSM response.
# Large failure traces/screenshots remain in EVIDENCE on the staging host.
python3 - "$EVIDENCE" <<'PY'
import base64, io, pathlib, sys, tarfile
root=pathlib.Path(sys.argv[1]); buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w:gz') as archive:
    for name in ('pytest.log','junit.xml','coverage.xml','result.json','test-image-digest.txt'):
        path=root/name
        if path.is_file(): archive.add(path,arcname=name)
encoded=base64.b64encode(buffer.getvalue()).decode()
if len(encoded) > 16000: raise SystemExit('Test evidence exceeds safe SSM response size')
print('STAGING_TEST_ARTIFACTS_B64='+encoded)
PY
echo "STAGING_TEST_EVIDENCE_PATH=$EVIDENCE"
if [[ $RESULT -ne 0 ]]; then echo "STAGING_SUITE_FAILED=$SHA"; exit "$RESULT"; fi
echo "STAGING_SUITE_PASSED=$SHA"
