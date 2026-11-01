# Architecture

## Component boundaries

The application separates uncertain schema reasoning from deterministic data handling. A CSV batch is the execution unit; `order_id` is the warehouse identity. The source is inspected once into a bounded byte snapshot, and its SHA-256 binds the subsequent approval and load.

```mermaid
flowchart LR
    CSV[Untrusted CSV] --> I[Bounded inspection / SHA-256]
    I --> K{Known schema?}
    K -->|yes| T[Fixed Python transformations]
    K -->|no| P[Schema planner: OpenAI or explicit fixture]
    P --> V[Local mapping validation]
    V --> A[Operator approval]
    A --> B[Input / contract / proposal / options binding]
    B --> T
    T --> Q{Deterministic quality gate}
    Q --> X[Row or batch quarantine]
    Q --> L[Transactional SQLite load]
    L --> R[Conflict: rollback]
    L --> S[Static SQL analytics]
    I --> U[Run state and audit]
    A --> U
    Q --> U
    L --> U
```

| Module | Responsibility | External effects |
|---|---|---|
| config | Contract identity and source resource limits | None |
| planner | Proposal generation and local mapping validation | Optional Responses API request |
| contract | Currency, ID, timestamp and status transformations | None |
| storage | Versioned schema initialization and transaction ownership | SQLite |
| pipeline | Approval, quality gate, loading, queries and audit | SQLite |
| cli | Argument validation, JSON output and process status | Filesystem and stdout/stderr |

## Approval and load sequence

```mermaid
sequenceDiagram
    actor Operator
    participant CLI
    participant Planner
    participant DB as SQLite
    CLI->>Planner: Column names + contract only
    Planner-->>CLI: Structured mapping proposal
    CLI->>CLI: Validate full bijection and known fields
    CLI->>DB: Save proposal + originating run
    Operator->>CLI: Approve saved proposal ID
    CLI->>DB: Persist reviewer + exact binding digest
    Operator->>CLI: Resume same input and options
    CLI->>CLI: Inspect and validate rows
    CLI->>DB: BEGIN IMMEDIATE
    CLI->>DB: Recheck complete approval binding
    CLI->>DB: Consume approval and compare/insert orders
    alt All records consistent
        CLI->>DB: Save success outcome and COMMIT
    else Conflict or injected failure
        CLI->>DB: ROLLBACK
        CLI->>DB: Persist failed outcome separately
    end
```

A proposal is saved atomically with its pending outcome. Quality evidence and quarantine rows form a separate transaction before loading, so they survive a failed load. Approval consumption, all order changes, successful run state and successful audit events share one transaction. A failed load therefore leaves its approval available for a recovery attempt.

## Failure model

The SQLite connection is process-local and uses a 10-second lock timeout, explicit write transactions, foreign keys and FULL synchronous mode. A process crash releases SQLite locks; uncommitted writes are rolled back by SQLite. A crash can leave an attempt at `started`; the operator reconciles the run history and warehouse before rerunning. The implementation does not claim distributed exactly-once processing or automated stuck-run reconciliation.

Only the planner calls an LLM. Live mode uses bounded SDK retries, suppresses raw provider errors and never falls back to a fixture. Every source row stays local. Model output is data and cannot alter Python transformations or SQL statements.
