# Production monitoring and staging recovery drills

Run monitoring separately on the production EC2 host from /opt/swe40006-monitoring:

    docker compose config --quiet
    docker compose pull
    docker compose up -d

Prometheus scrapes host CPU/RAM/root-disk/I/O/network metrics from Node Exporter,
application HTTP request and latency metrics from Flask, and trusted HTTPS/database
health for staging and production through Blackbox Exporter. Alerts are evaluated
by Prometheus and delivered to the local Alertmanager. The local dashboard receiver
has no external email, SMS or webhook destination configured.

Grafana is provisioned with the Prometheus data source and the ten-panel SWE40006
overview. All monitoring listeners bind only to 127.0.0.1 on EC2. Grafana anonymous
access is Viewer-only inside this private boundary, login and account creation are
disabled, and no initial administrator is created. It is not publicly accessible.

To view it with an existing authorized AWS CLI session:

    aws ssm start-session --region ap-southeast-2 --target i-0ce962fcfeb18ff74 --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["3000"],"localPortNumber":["13000"]}'

Open http://127.0.0.1:13000/d/swe40006-overview in your own browser. Keep that
terminal session open while viewing; Ctrl+C closes the private tunnel. The AWS
Session Manager plugin must be installed from the official AWS distribution.
Monitoring ports remain closed in the EC2 security group.

Prometheus data retention is three days / 256 MB. Monitoring adds no EC2 instance
or managed cloud subscription. Containers have memory limits for the t3.micro host;
review resource use before extending retention or adding more monitoring targets.

Staging exercises retain a generated test account and evidence task. They recreate
DB/app containers without deleting named volumes, redeploy the same immutable image,
and attempt a deliberately failing image to verify restoration of the prior image.
A separately controlled staging outage tests the WebsiteUnavailable alert and its
recovery. Production is never deliberately stopped during these exercises.

The failing image is a private test fixture, not a source commit, and is ineligible
for the production workflow because it has no successful main CI run. Application
image rollback does not roll back database schema or provide disaster recovery.
Schema migrations and backups require their own plan.
