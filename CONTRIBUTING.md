# Contributing

Thanks for improving the project.

## Development setup

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

For the complete stack:

```bash
python scripts/init_env.py
docker compose up --build
```

## Pull requests

Keep changes focused and explain the problem, design choice, test coverage and
any impact on the OPC UA model, database schema, API or simulation behavior.

Add or update tests for behavior changes. Update documentation when public
interfaces or operational steps change.

## Security and privacy

Never include real credentials, private certificates/keys, personal data,
real plant telemetry or organization-internal addresses in commits, issues,
screenshots or test fixtures.

Run this before publishing a branch:

```bash
python scripts/repository_audit.py
```
