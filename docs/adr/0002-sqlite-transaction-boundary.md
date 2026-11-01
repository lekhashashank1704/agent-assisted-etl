# ADR 0002: SQLite as the atomic batch-load boundary

Status: Accepted

## Context

A runnable reference needs durable orders, approvals, run state and audit evidence with minimal infrastructure. Failure after an early insert must not leave a partial batch.

## Decision

Use one local SQLite database and explicit `BEGIN IMMEDIATE` transactions. Commit approval consumption, all order writes, success state and success audit events together. Persist quality/quarantine evidence separately before the load. Record a failed outcome only after load rollback. Compare existing canonical records rather than silently upserting them.

## Consequences

Recovery is inspectable and reruns do not duplicate orders. SQLite remains a single-writer resource; distributed concurrency, independent audit retention, large-scale loading and high availability need a different deployment design. File-backed tests exercise the same transaction behavior. A crash can leave `started` state requiring operator reconciliation.
