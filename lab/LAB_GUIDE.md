# Guided lab (50–60 minutes)

Prerequisite: Python 3.11+, a terminal, repository installed with `pip install -e ".[dev]"`. No API key is needed. Use a new database path for manual exercises. All records are synthetic.

1. **0–5 min — inspect boundaries.** Read the architecture and contract. Run `python -m etl_agents.cli inspect data/clean.csv`. Identify the hash, header list and row count. Explain why rows never go to the planner.
2. **5–10 min — clean and alias.** Run clean.csv and alias.csv against `--db output/exercise.db`. Predict and verify three total orders; no approval is needed for cust_id.
3. **10–15 min — money.** Run currency.csv without `--us-thousands`, inspect quarantine/audit, then rerun with the flag. Verify 123456 cents, without floating-point arithmetic.
4. **15–22 min — quality.** Run mixed.csv and quarantine.csv. Compare exactly 20% with more than 20%. Query `quarantine` with SQLite or inspect audit validation counts. Explain why the whole second batch is rejected.
5. **22–30 min — schema approval.** Run unknown.csv with `--planner demo`. This is a scripted fixture, not AI inference. Review returned mapping and input hash using `proposals`. Approve the ID with `approve ID --operator learner`, then resume with `run data/unknown.csv --approval ID`. Verify a second resume rejects consumed approval.
6. **30–38 min — rollback.** Run recovery.csv with `--fail-after 1`. Compare analytics before/after: no orders commit. Read the failed audit event.
7. **38–43 min — recover and repeat.** Run recovery.csv normally, then again. The first inserts two orders; the second inserts zero. Run conflict.csv after clean.csv; confirm o15 does not commit.
8. **43–50 min — complete demo.** Run `python lab/run_lab.py`. Open output/lab/report.html and results.json. Find the proposal, approval, validation and failure events.
9. **50–60 min — challenge.** Run `python -m pytest -q`. Read mocked API tests. Explain why structurally valid output still needs a human decision. Discuss RBAC, tamper resistance and streaming as production extensions. Live API testing remains optional and separately authorized.

All CLI commands accept the database option before the subcommand. Awaiting approval exits 2; quarantine/failure exits 1. These are expected lab outcomes, not shell setup errors. The full script asserts expected outcomes and exits 0 only when all scenarios succeed.
