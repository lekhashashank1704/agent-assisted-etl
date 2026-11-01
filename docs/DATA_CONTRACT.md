# Orders contract: orders-v1

Exactly five fields are required: `order_id`, `customer_id`, `amount`, `created_at`, `status`. Extra columns are not silently discarded. Reordering is allowed; duplicate/empty headers are rejected. `cust_id` is a preapproved alias; `client_ref` requires a reviewed proposal.

- IDs are trimmed, nonempty strings. Orders use `order_id` as the warehouse primary key.
- Status is exactly `paid`, `pending`, or `cancelled` after trimming.
- Amount uses ASCII digits, is nonnegative and has at most two decimal places. No exponent, symbol or implicit locale conversion. Empty amount becomes NULL only for pending orders.
- `--us-thousands` explicitly allows properly grouped commas, e.g. `1,234.56`. CSV fields containing commas must be quoted. Money is stored as signed-64-bit integer cents; larger values are rejected.
- Timestamps are ISO-8601, require explicit timezones, and normalize to UTC. Naive timestamps fail validation.
- More than 20% invalid rows quarantines every source row and loads none. Exactly 20% loads valid rows and quarantines invalid rows. Empty batches are quarantined.
- Malformed CSV rows count as invalid. Quarantine records source row number, raw synthetic row JSON and reason, tied to the run.
- Exact existing records are skipped. Any changed existing order blocks and rolls back the entire load, including new records inserted earlier in that transaction.

Change `VERSION` when contract semantics change. No currency code or cross-currency aggregation is implemented; all fixtures assume one fictional currency.
