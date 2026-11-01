# Control-to-evidence matrix

| Requirement | Implementation | Behavioral evidence |
|---|---|---|
| Only metadata enters AI request | planner.OpenAIPlanner | test_mocked_api_request_privacy_and_shape |
| Ambiguous/invented mappings rejected | planner.validate | test_invalid_proposals; test_duplicate_headers_rejected_by_mapping_validator |
| Unknown schema fails closed | pipeline.run; planner adapter | test_api_failure_fails_closed_and_redacts; API refusal cases |
| Explicit reviewer approval | Pipeline.approve | test_unknown_requires_approval; test_operator_validation |
| Input/version/options binding | _approved_mapping | test_stale_input_and_options |
| Exact proposal binding and lock recheck | approval_binding; load transaction | test_postapproval_mapping_modification_rejected; test_binding_rechecked_under_load_lock |
| Single-use consumption | load transaction | test_consumption_visible_to_second_connection |
| Money/null/timezone contract | contract.transform | currency/null rejection cases; test_utc |
| Quality threshold | pipeline.run | test_threshold; test_empty_batch |
| Transactional recovery | storage.transaction; pipeline.run | test_transaction_and_idempotency; test_approval_rollback_and_recovery |
| Conflicts roll back prior inserts | deterministic order comparison | test_conflict_rolls_back_prior_insert; test_within_batch_conflict |
| Auditable inspection failures | pipeline.run | source-limit, missing-file and encoding cases |
| Database compatibility | storage.connect | legacy migration and future-schema rejection tests |
| Operator query interface | cli; query methods | subprocess CLI operational and exit-code tests |
| Bounded transient retries | SDK configuration | transport-mocked transient/nontransient request tests |

Evidence means tests in this repository, not an external audit or attestation. Consult VALIDATION.md for the checks actually executed on the current environment.
