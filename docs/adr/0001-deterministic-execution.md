# ADR 0001: Deterministic execution with a schema reasoning boundary

Status: Accepted

## Context

Legacy column names can drift without changing the intended data contract. Allowing generated transformation code would expand review scope and permit unsafe behavior beyond a schema mapping.

## Decision

Use the Responses API only to propose a full mapping from source names to the five contract fields. Send names and contract metadata only. Validate the bijection locally and require an explicit operator decision. Execute fixed Python transformations and fixed SQL only. The demo fixture is selected explicitly and never substitutes for a failed live request.

## Consequences

The model has a narrow, reviewable role. An operator still owns semantic correctness. Unsupported shape changes require contract/code changes rather than generated logic. Timeouts, refusals and invalid proposals block unknown schemas. Offline CI can test the complete deterministic path and mock the provider boundary without spending API credits.
