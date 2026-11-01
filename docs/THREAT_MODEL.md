# Threat model

## Assets and assumptions

Assets are source records, canonical orders, approval decisions, audit history and API credentials. Trusted code is the reviewed Python application. Source CSV files and model output are untrusted. SQLite and the local operating-system account are trusted infrastructure; database-owner compromise is outside the integrity guarantees provided here.

| Threat | Implemented mitigation | Residual risk |
|---|---|---|
| Prompt injection in column names | Treat metadata as data; send no cells; validate output locally | Model can still suggest a plausible but semantically wrong bijection; review required |
| Invented/dropped/colliding fields | Require full bijection and preserve known fields | Structural checks cannot establish business meaning |
| Changed source after approval | Hash exact bytes consumed; bind contract/options/proposal | Reviewer must verify source provenance |
| Modified proposal after approval | Approval checksum and locked recheck | Database administrator can alter checksum too; no signature |
| Replayed approval | Consume inside load transaction, recheck under write lock | No authenticated identity or separate approver role |
| Money/timestamp corruption | Fixed Decimal-to-cents parsing and timezone validation | One assumed currency; no exchange-rate policy |
| Partial writes or conflict overwrite | Static parameterized SQL, conflict comparison, atomic load | Local storage availability and filesystem durability still matter |
| Resource exhaustion | Byte, record, column and header-size limits | Bounded in-memory batches only; no streaming |
| Secret/provider error leakage | Environment credentials; fixed sanitized provider failure | SDK/infrastructure diagnostics outside this application need separate review |
| Audit deletion or false operator names | Persistent correlated events | Local database owner can rewrite history; external audit/RBAC required |
| Dependency compromise | Version bounds, snapshot constraints, review workflows, static/advisory checks | Bounds/snapshots are not artifact signatures; hosted controls must run |

No remote service endpoint, authentication system, managed key vault, tenant isolation or compliance certification is implemented. The container runs without root by default, but runtime mounts and permissions remain deployment responsibilities.
