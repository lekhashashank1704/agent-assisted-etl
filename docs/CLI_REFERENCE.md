# CLI reference

`etl-agents` and `python -m etl_agents` expose the same interface. Use the virtual environment's Python. Global options must precede the subcommand.

```text
etl-agents [--db PATH] [--max-input-bytes N] [--max-rows N] COMMAND
```

| Option | Default | Meaning |
|---|---|---|
| --db | output/warehouse.db | SQLite file; parent created for database operations |
| --max-input-bytes | 10485760 | Maximum bytes inspected in memory |
| --max-rows | 100000 | Maximum data records inspected |
| --version | n/a | Application version |

| Command | Options | Result |
|---|---|---|
| inspect CSV | none | Headers, data-row count and SHA-256; no database side effect |
| run CSV | --planner demo/live OR --approval ID; --us-thousands; --fail-after N | One durable attempt |
| proposals | none | Saved mappings, binding data and approval state |
| approve ID | --operator NAME | Approve the exact persisted proposal |
| runs | none | Durable execution history |
| quarantine | --run-id ID | Rejected records and source record numbers |
| audit | --run-id ID | Chronological events, optionally scoped to one run |
| analytics | none | Counts and cents by status, computed with static SQL |
| health | none | SQLite quick_check and storage schema version |

`health` rejects a missing database. It opens existing files through the normal version-check/migration path; it is an operator command, not a passive network readiness endpoint. `--fail-after` is explicit lab fault injection and must be positive.

## Exit and error contract

| Exit | Meaning |
|---|---|
| 0 | Successful command or committed batch, including zero-insert reruns |
| 1 | Failed operation, rejected approval, unhealthy storage or batch quarantine |
| 2 | Batch awaiting approval; argparse also uses 2 for invalid command syntax |

Inspect `status` in JSON to distinguish awaiting approval from argument errors. Successful output and run outcomes use stdout. Pre-run argument errors use argparse stderr; operational errors use JSON stderr. Run failures include `error_code`, `error`, `run_id`, and zero committed `loaded` count.

| Error code | Operator action |
|---|---|
| SOURCE_INVALID | Correct source encoding/syntax or authorized resource limits |
| PLANNER_REJECTED | Review schema; resolve provider access or ambiguous proposal |
| APPROVAL_INVALID | Inspect saved proposal and obtain a new valid approval |
| ORDER_CONFLICT | Reconcile source versus existing order; do not force overwrite |
| INJECTED_FAILURE | Remove explicit lab fault injection and rerun |
| STORAGE_ERROR | Check integrity, permissions and competing writers |
| VALIDATION_ERROR | Correct execution parameters |
| OPERATION_FAILED | Inspect command setup and database availability |

`invalid` counts rows violating the contract. `quarantined` counts retained rejected rows, which may include otherwise valid rows in a whole-batch rejection. `loaded` counts new committed orders; `skipped` counts identical existing orders. On rollback, both load counters are zero. Record numbers start at 2 and refer to logical CSV records, not physical lines inside multiline cells.
