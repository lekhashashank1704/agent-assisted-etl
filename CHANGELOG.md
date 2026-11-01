# Changelog

Changes follow a chronological release log. Versions describe the application; contract and SQLite schema versions evolve independently.

## 0.2.0 - Unreleased

- Add bounded source inspection, structured error codes, operational CLI queries and health checks.
- Add versioned SQLite initialization with additive legacy upgrade support.
- Bind approval digests to exact proposals and revalidate under the load lock.
- Correlate approval audit events with the originating run; retain row-specific quarantine reasons.
- Add typed interfaces, lint/format/type/coverage checks and package validation.
- Add CI security and container workflows, contribution templates and operational documentation.
- Use a non-root multi-stage container image.

## 0.1.0 - Initial implementation

- Deterministic orders validation and transactional SQLite loading.
- Responses API schema planner and explicit scripted demo fixture.
- Input-bound approvals, quarantine, conflict rollback and idempotent reruns.
- Synthetic datasets, guided lab, HTML/JSON reporting and mocked API tests.

No release tag or published package is implied by this file.
