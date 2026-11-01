# Security policy

## Reporting

Do not include credentials or private records in public issues. If GitHub private vulnerability reporting is enabled, use the repository Security tab to report privately. Otherwise contact the repository owner through a private channel already known to you before sharing exploit details. This project does not claim a staffed response SLA or a formal vulnerability disclosure program.

## Scope and trust boundaries

This is a local reference implementation using synthetic data. CSV cells stay local; only column names and contract metadata are sent to OpenAI. Column names can themselves contain sensitive information, so sanitize source metadata before enabling live mode. Keys are read by the SDK from the environment and are never included in application results.

Model responses are untrusted. Local validation enforces a complete one-to-one mapping and preserves known fields. Model output is never executed. A reviewed approval binds the exact input hash, contract, saved proposal and parsing options, and is rechecked under the load lock. Its checksum detects accidental proposal mutation; it is not a signature or protection against an administrator who can alter both the proposal and checksum.

SQLite access is the effective security boundary. Operator names provide attribution, not authentication or separation of duties. Database owners can change or remove audit history. Restrict filesystem access and never use untrusted database files. Encryption, RBAC, externally retained audit logs and key management must be supplied by a production deployment.

## Verification and maintenance

CI defines static analysis and dependency-advisory checks. Dependabot proposes updates; changes still require review and tests. Workflow permissions are read-only by default and no publishing credentials are configured. These files do not prove that hosted checks or repository protection settings are enabled.

Only the current unreleased implementation is maintained. See docs/THREAT_MODEL.md for risks and docs/OPERATIONS.md for recovery and backup procedures. Never commit real workload databases, environment files, reports containing private data or plaintext secrets.
