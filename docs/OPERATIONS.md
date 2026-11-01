# Operator runbook

## Before a batch

Confirm the intended database path, application/contract versions, source provenance and parsing options. Run `etl-agents inspect data/clean.csv` and record the hash. Source limits default to 10 MiB and 100,000 records. Increase them only after reviewing memory capacity. Use `etl-agents --db output/warehouse.db health` for an existing warehouse.

## Schema approval

1. Run the unknown schema with an explicitly selected planner: `etl-agents --db output/warehouse.db run data/unknown.csv --planner demo` for the fixture, or `--planner live` only after configuring API access.
2. Inspect `proposals`. Verify every source field, target meaning, input hash, contract and currency option. Structural validation cannot prove a mapping is semantically correct.
3. Approve the returned ID using `approve ID --operator NAME`. Operator text is attribution only; enforce real reviewer identity outside this process.
4. Resume with the same bytes/options using `run data/unknown.csv --approval ID`.
5. Verify the terminal run state, committed load count and analytics. A committed approval is single use; a failed transaction leaves it unconsumed.

## Response matrix

| Symptom | Evidence | Recovery |
|---|---|---|
| Awaiting approval | status + proposal ID | Review, approve and resume exact source/options |
| Whole batch quarantined | invalid ratio, run-scoped quarantine | Correct source; rerun as a new input |
| Partial quarantine | invalid/quarantined counters | Review rejected records; valid rows already committed |
| Provider refusal/failure | PLANNER_REJECTED | Fix provider access or schema ambiguity; no mock fallback |
| Conflicting existing record | ORDER_CONFLICT and failed run | Reconcile upstream correction; never delete/overwrite blindly |
| Load failure | failed outcome, zero loaded count | Resolve cause, rerun same input; confirm no unexpected orders |
| Busy/locked database | STORAGE_ERROR or command-level error | Stop competing writer, retry after lock holder exits |
| Interrupted attempt at started | runs and audit | Reconcile warehouse and source hash, then rerun; do not mark success manually |
| Consumed/mismatched approval | APPROVAL_INVALID | Create and review a new proposal; do not patch the approval row |

Invalid source encoding, headers and resource-limit failures are recorded as failed runs with no trusted input hash. Quarantine/validation evidence persists even when loading rolls back. Repeated attempts have distinct run IDs and can repeat rejected-row evidence; order-level deduplication does not deduplicate run history.

## Recovery exercise

```sh
etl-agents --db output/recovery.db run data/recovery.csv --fail-after 1
etl-agents --db output/recovery.db analytics
etl-agents --db output/recovery.db run data/recovery.csv
etl-agents --db output/recovery.db run data/recovery.csv
```

Expected committed inserts: 0, then 2, then 0. The first command intentionally exits 1. Check audit events rather than interpreting shell exit alone.

## Backup and restoration

```sh
python scripts/backup.py --db output/warehouse.db --output output/backups/warehouse.db
```

The utility opens the source read-only, refuses existing destinations, uses SQLite backup and checks integrity of the copy. Protect the backup like the source. To restore, stop every writer, preserve the current file for investigation, and point the CLI at a verified backup copy. Run health and reconcile expected order counts before resuming ingestion. Recovery point/time objectives must be measured in the target deployment; none are asserted here.

## Escalation evidence

Capture application/storage/contract versions, run ID, input hash, parsing options, stable error code, sanitized audit events and database health. Never include API keys, real source rows or private report attachments in public issues.
