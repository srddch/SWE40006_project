# Complete staging tests and automatic production promotion

`main` push runs the CI suite, builds the application and matching test image,
and publishes both immutable ECR tags. The staging job invokes the existing
fixed SSM document. On staging, the installed test hook runs the full existing
Pytest API/integration/Chromium suite against a separate temporary MariaDB
container. It publishes no database ports and mounts no deployment database
volume. The test containers and their anonymous database volume are removed
after each run; XML, JSON and logs are retained.

Only a successful complete CI/staging workflow triggers automatic production
promotion through `workflow_run`. The production workflow uses the triggering
run's `head_sha`, checks that this same successful main-branch run qualifies and
that staging still serves that version, then deploys the existing application
image and runs public HTTPS/CRUD checks. `workflow_dispatch` remains available
as a manual fallback. Production never runs the destructive test fixture.

## Installed staging hook

On staging only, `/usr/local/bin/swe40006-deploy` contains `deploy/deploy.sh` and
`/usr/local/bin/swe40006-staging-tests` contains `deploy/staging_tests.sh`.
The deployment script invokes the test hook under its deployment lock. The
production host has no test hook. No new SSM/IAM permission is needed: the
existing staging role can invoke only its fixed deployment document/instance,
and the EC2 role reads both tags from the existing project ECR repository.

## Evidence

The `staging-deployment-evidence` artifact includes the SSM result, public smoke
result and `staging-tests/{pytest.log,junit.xml,coverage.xml,result.json}`.
`result.json` records the target instance, commit, test-image digest, test
counts, coverage and UTC times. Its SSM result binds execution to the actual
EC2 instance. Host copies are retained under `/opt/swe40006/test-evidence/`.
The production workflow records `workflow_run` as its trigger, the source
CI run ID and candidate SHA, and retains its deployment/smoke artifacts.

The existing test suite starts a test application from the matching source
inside the staging test container. Public smoke checks separately verify the
deployed staging application. This keeps test-fixture cleanup away from the
application's stored data while testing both code and deployed operation.
