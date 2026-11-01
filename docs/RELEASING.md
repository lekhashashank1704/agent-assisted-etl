# Release procedure

The repository currently has an unreleased 0.2.0 application version. No package registry or container registry publication is configured.

1. Review the changelog and compatibility impact. Update application versions in pyproject.toml and src/etl_agents/__init__.py together. Change the contract or SQLite schema version only when its semantics change.
2. Run all quality gates, tests, scripted scenarios, package build and advisory audit. Review the diff and confirm all fixtures and artifacts are synthetic. Record checks actually performed in VALIDATION.md.
3. Build an sdist and wheel with `python -m build`. Install the wheel into a clean environment and verify `etl-agents --version`, contract loading and diagnostics. Retain checksums with the release evidence.
4. For schema changes, take a verified backup and rehearse migration/restore on copies. Document approval invalidation. Do not assume a previous application can read a newer schema.
5. Obtain maintainer approval, merge through a protected branch, and create a version tag only after approval. This guide does not authorize automatic publishing or tagging.
6. If a release is published later, attach reviewed artifacts, checksums and release notes. Use short-lived trusted publishing rather than committing long-lived credentials.

## Rollback

Stop writers first. For application-only regressions, use the previously verified build if it accepts the current schema. For storage-incompatible changes, preserve the affected database and restore a verified backup copy; reconcile transactions after the backup point before resuming. Never force an older application past its schema-version guard.

Recommended repository settings: required passing verify/security checks, CODEOWNERS review, blocked force pushes and restricted bypass. These are recommendations to configure in GitHub, not controls enforced merely by adding files.
