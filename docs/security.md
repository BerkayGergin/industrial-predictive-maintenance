# Security Notes

This repository is a local learning and demonstration lab. It is **not** an
internet-facing production deployment or a certified machine-protection system.

## Public-repository safety

- No real plant telemetry, API keys, broker credentials, certificates, usernames,
  email addresses, machine names or personal filesystem paths are required.
- `.env` is ignored by Git and by Docker's build context.
- The container image copies only runtime source directories; local secret files
  are not copied into image layers.
- Host-published ports bind to `127.0.0.1` by default, so the dashboard, OPC UA
  endpoint and database are not exposed to the LAN unless the operator changes
  the Compose configuration.
- The database password has no committed default. Create a local `.env` before
  starting the stack.

## Current lab security model

- OPC UA uses `SecurityPolicy=None` inside the local Docker lab.
- FastAPI has no login, RBAC or operator identity verification.
- Simulation command endpoints are intentionally writable from the local dashboard.
- Database authentication is local-development only.

These choices are acceptable only for the isolated learning environment described
by this repository.

## Production requirements

A production deployment would normally require:

- OPC UA application certificates and secure security policies.
- Trusted certificate stores, certificate rotation and explicit application/user authorization.
- Least-privilege access to writable OPC UA nodes.
- Managed secrets instead of plaintext environment files.
- Authenticated HTTPS, role-based API permissions and origin controls where applicable.
- Private network segmentation and firewall rules for database and OPC UA services.
- Audit logging for operator actions.
- Database migrations, encrypted backups, retention policy and monitoring.
- Calibrated sensor limits, real asset metadata and validation against plant data.
- Operational safety review before any connection to real machinery.

Do not expose the included OPC UA, API or database services directly to an
untrusted network.
