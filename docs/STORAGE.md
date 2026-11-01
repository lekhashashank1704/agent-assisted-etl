# Storage and migration contract

Application version, contract version (`orders-v1`) and storage version (`PRAGMA user_version=1`) are independent.

| Table | Key / scope | Purpose |
|---|---|---|
| orders | order_id | Canonical customer, integer cents, UTC timestamp and status |
| runs | id | Input hash, contract, state and serialized outcome |
| proposals | id | Exact mapping/options, input/contract, originating run, reviewer, approval digest and timestamps |
| quarantine | run_id + record number | Rejected raw row and validation reason |
| audit | monotonic id, run_id | Event category, JSON detail and UTC event time |

Indexes support run-scoped audit/quarantine queries and input-hash lookup. Fresh databases enforce IDs, statuses, nonnegative integer money, pending-only NULL money and quarantine-to-run foreign keys. SQL is fixed or parameterized. The migration's dynamically assembled ALTER statement uses an internal constant list of column names, never source or model data.

## Upgrade behavior

Initialization executes schema migration under `BEGIN IMMEDIATE`. An unversioned initial database is upgraded additively: missing tables/indexes and proposal governance columns are created without rewriting orders. Existing original tables retain their original constraints; they are not silently rebuilt. Application validation remains mandatory for legacy files.

Old approved proposals have no binding digest and cannot resume until explicitly reapproved. An already-approved legacy proposal must be replaced by a new proposal/approval rather than editing stored approval data. Historical audit entries are preserved as recorded, including legacy proposal-based correlation IDs. Newly created proposals correlate approval events to the originating run.

A database whose version is newer than the application is refused. Downgrades are not automatic. Before any deployment, create a verified backup, test the migration on a copy, and keep the corresponding application build. The current migration is version 1; no generic migration framework or zero-downtime migration promise is implied.

## Durability and retention

Write transactions are explicit. FULL synchronous mode is configured; journal mode remains the deployment default. Do not copy a live database file as a backup. Use SQLite's online backup API through `scripts/backup.py`, or stop every writer before taking a filesystem copy. Keep output reports, quarantine and audit data under the same access and retention controls as source data. No deletion/retention automation is implemented.

SQLite aggregate sums use signed 64-bit integers. Individual amounts are bounded to that range; an aggregate outside that range can fail and must not be treated as a valid report.
