# Contributing

## Local workflow

Use Python 3.11 or later. Create an isolated environment and install `python -m pip install -e ".[dev]"`. Use synthetic data only.

Before submitting a change:

```sh
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest --cov --cov-report=term-missing
python -m bandit -c pyproject.toml -r src/etl_agents
python -m build
python lab/run_lab.py
```

The application coverage gate is 85% with branch measurement enabled. Add tests around observable behavior: transaction boundaries, approval binding, contract semantics and failure recovery. Tests disable direct socket connections; API tests must use injected clients or mock HTTP transports. Never introduce a fallback from live mode to fixture mode.

## Change discipline

Keep changes focused and explain the problem, resulting behavior, actual verification and remaining risk in the pull request template. Run `python -m ruff check --fix .` and `python -m ruff format .` before review. Avoid unrelated formatting changes in feature pull requests.

A contract semantic change requires a new contract version and stale-approval tests. A storage change requires a versioned, transactional migration, preservation tests and rollback guidance. Never rewrite existing order records to resolve a conflict automatically.

Use descriptive commits such as `fix: revalidate approval before loading` and branches such as `fix/approval-binding`. Update the changelog for operator-visible changes. Maintainer review is routed through CODEOWNERS; repository rules must enforce it separately.

## Review expectations

Review input boundaries, deterministic behavior, safe errors, parameterized SQL, compatibility, data retention and test evidence. There is no contributor license agreement; contributions use the repository's MIT license. Be respectful, specific and evidence-driven in technical discussion.
