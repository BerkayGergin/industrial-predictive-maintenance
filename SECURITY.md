# Security Policy

## Scope

This repository is an educational condition-monitoring lab. It is not intended
to control or protect real machinery.

## Reporting a security issue

If GitHub private vulnerability reporting is enabled for this repository, use
that channel for security-sensitive reports. Do not post credentials, private
keys, tokens, personal data or exploit details in a public issue.

For non-sensitive hardening suggestions, a normal GitHub issue is appropriate.

## Secrets

Real credentials must never be committed. Use a local `.env` file, which is
excluded from both Git and Docker build context. If a real secret is ever pushed,
rotate or revoke it immediately; deleting only the visible file is not sufficient
because Git history may still contain it.

See `docs/security.md` for the lab threat model and production limitations.
