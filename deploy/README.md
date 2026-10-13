# AWS deployment

The main CI workflow tests the application, builds and publishes an immutable
commit-tagged ECR image, deploys it to staging through the fixed SSM document,
and verifies HTTPS, database readiness and a real authenticated task workflow.
PR verification has no AWS deployment access.

Production is deliberately promoted with the separate **Manually promote
verified staging to production** workflow. Run it on main and enter the full
40-character SHA currently deployed to staging. The workflow requires the CI
run for that SHA to have succeeded and verifies that the staging endpoint
serves that SHA before deploying exactly the same image to production.

This is an operator-triggered production gate. It is not a GitHub Required
reviewers rule; configuring that rule requires repository administrator access.

Instances have separate encrypted disks, MariaDB volumes and secrets. The only
public ports are 80/443. SSH, MariaDB and metrics are not exposed. SSM invokes a
fixed command accepting only a SHA; the two deployment roles each target one
instance and cannot provision or delete infrastructure. EC2's instance role
reads images from only this ECR repository and supports Systems Manager.

Runtime secrets are generated on each instance, stored in /opt/swe40006/.env
with mode 0600, and retained across deployments. Never commit that file or
include it in screenshots. Database volumes are retained during application
updates. The deploy script restores the previous application image if readiness
fails; schema changes require a separate migration/backup plan.

The image and release SHA are visible in the deployment artifacts and HTTPS
response headers. Caddy obtains and renews trusted TLS certificates for the
fixed-IP sslip.io hostnames. This demonstration setup depends on that public
DNS service; an owned domain can replace it later.

Cost controls: two t3.micro instances in standard CPU-credit mode, 20 GiB gp3
each, no RDS/ALB/NAT gateway. Fixed IPv4 addresses and disks still consume
credits when instances are stopped. No automatic shutdown has been configured.
Smoke tests retain a generated account but delete their disposable test task.
