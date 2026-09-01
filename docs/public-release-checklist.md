# Public Release Checklist

Before publishing this repository:

1. Run `python scripts/repository_audit.py`.
2. Confirm `.env` is ignored with `git check-ignore .env`.
3. Review `git status` and `git diff --cached` before the first push.
4. Do not add screenshots containing usernames, email addresses, local paths, internal hostnames, tokens or real plant data.
5. Use a GitHub-provided `noreply` commit email if you do not want your personal email address stored in public commit metadata.
6. Enable GitHub secret scanning / push protection and dependency alerts for the public repository.
7. Keep the default localhost-only port bindings unless you intentionally design and secure a network-facing deployment.
8. Never treat a committed secret as safe after deleting the file; rotate or revoke the credential because it may remain in Git history.

The repository is intended to contain only synthetic data and local-development configuration.
