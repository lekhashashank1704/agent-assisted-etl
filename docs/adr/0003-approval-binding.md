# ADR 0003: Exact execution binding for schema approvals

Status: Accepted

## Context

A reusable schema-wide approval could authorize changed data, a different contract or different currency parsing. A check outside the load lock alone can become stale before consumption.

## Decision

Persist the exact input SHA-256, contract version, mapping JSON and parsing options under a proposal ID. At approval, store a digest of that binding and reviewer attribution. Revalidate the full binding at resume and again under the load lock. Consume only when the order transaction commits.

## Consequences

Any changed bytes/options/proposal require review. A failed load can recover with the same unconsumed approval. A committed load cannot reuse it, including for an identical source. The digest detects accidental mutation but is not a signature against a privileged database writer. There is no authenticated reviewer, independent second approver or wall-clock approval TTL in this implementation.
