# 2–3 minute recording script

**0:00–0:25** Show the README and architecture. “This fictional orders pipeline uses an OpenAI mapping planner only for schema drift. Validation, transformations, loading and analytics are deterministic.”

**0:25–0:55** Run `python lab/run_lab.py` and open output/lab/report.html. “This recording uses an explicitly scripted demo fixture, with no API calls. Clean columns and the approved cust_id alias load directly. Currency is integer cents.”

**0:55–1:25** Show the quality outcomes and unknown mapping. “Exactly 20% invalid rows permits a partial load; more than 20% quarantines the batch. client_ref requires an input-bound approval. The saved mapping is reviewed before resume.”

**1:25–1:55** Show failure, recovery and rerun. “An injected failure rolls back all writes. Recovery inserts two orders. A repeat inserts zero. Conflicting records also roll back the whole load.”

**1:55–2:30** Show SQL analytics, audit trail and passing test output. “The tests include mocked Responses API requests, refusals and failures. Live API validation is pending. This is a local portfolio demonstration; production would need authentication, stronger audit storage and orchestration.”
