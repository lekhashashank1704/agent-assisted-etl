# Agent-Assisted ETL: Schema Drift, Approvals & Recovery

Developed a Python and SQLite reference implementation for governed schema drift handling. An OpenAI Responses API planner proposes mappings for unknown columns; local validation and input-bound operator approvals gate deterministic transformations and transactional loading. The pipeline implements row/batch quarantine, conflict rejection, rollback, idempotent reruns, recovery, SQL analytics and a correlated audit trail.

The repository includes versioned storage initialization, typed interfaces, operational runbooks, architecture decision records, a threat model, CI/security workflows and a non-root container definition. Local verification: 77 passing tests, 98.62% application coverage with branch measurement and 11 verified synthetic-data scenarios. The planner demo is explicitly scripted; live API validation is pending. No production deployment, compliance certification or measured business improvement is claimed.
