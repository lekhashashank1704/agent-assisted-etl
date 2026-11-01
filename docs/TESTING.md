# Testing strategy

## Test layers

- **Contract:** parametrized currency, pending/null, IDs, statuses and timezone cases.
- **State/transactions:** real temporary SQLite files for quarantine, conflicting orders, rollback, recovery, approval consumption and reopen/resume behavior.
- **Governance:** mutated proposal binding, input/contract/options mismatches, lock-time rechecks and audit correlation.
- **Interfaces:** subprocess CLI checks for JSON output, explicit nonzero outcomes and inspection without database side effects.
- **Provider adapter:** injected SDK clients and HTTP mock transports for structured request shape, refusal, incomplete output, bounded transient retries and authentication failure. No paid calls.
- **Operations:** schema migration, health diagnostics, resource limits and backup preservation.

Tests disable direct socket connections in the pytest process. Subprocess CLI cases explicitly select deterministic operations or the fixture planner; the harness does not constitute an operating-system network sandbox.

## Gates

```sh
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest --cov --cov-report=term-missing --cov-report=xml --junitxml=reports/junit.xml
python -m bandit -c pyproject.toml -r src/etl_agents
python -m build
python lab/run_lab.py
```

Branch measurement is enabled and the application coverage threshold is 85%. A passing percentage is a regression gate, not proof of correctness. Do not replace failure-path assertions with tests that mirror implementation details.

CI defines Python 3.11-3.14 on Linux plus Python 3.14 on Windows. Local evidence applies only to the platform recorded in VALIDATION.md. The separate dependency audit checks every exact version in requirements/constraints.txt against advisory services without dependency resolution and therefore needs network access. CLI logic is covered through direct JSON-interface tests, alongside independent subprocess smoke tests. Container checks need Docker. Live API behavior requires an authorized, separately recorded validation session.
