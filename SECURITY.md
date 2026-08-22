# Security policy

Please report vulnerabilities privately through GitHub Security Advisories or directly to
the repository owner. Do not include database URLs, secret keys, bearer tokens, source
evidence bodies, raw cloud snapshots, customer identifiers, screenshots, or production
logs in public reports.

This source release is a deployable application architecture, not an operated
service. Deployer responsibilities include TLS, OIDC integration, secret rotation, CORS,
rate limiting, PostgreSQL RLS role design, backup/recovery, monitoring, logging policy,
network segmentation, migration approval, and independent security review.
