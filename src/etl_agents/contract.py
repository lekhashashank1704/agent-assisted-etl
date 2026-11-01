"""Fixed transformations and local contract validation; no generated code."""

import re
from datetime import UTC, datetime
from decimal import Decimal

OrderRecord = tuple[str, str, int | None, str, str]


def transform(row: dict[str, str], us_thousands: bool = False) -> OrderRecord:
    for key in ("order_id", "customer_id"):
        if not row[key].strip():
            raise ValueError("empty " + key)
    status = row["status"].strip()
    if status not in ("paid", "pending", "cancelled"):
        raise ValueError("invalid status")
    amount = row["amount"].strip()
    cents = None
    if not amount:
        if status != "pending":
            raise ValueError("amount required")
    else:
        pattern = (
            r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]{1,2})?"
            if us_thousands
            else r"[0-9]+(?:\.[0-9]{1,2})?"
        )
        if not re.fullmatch(pattern, amount):
            raise ValueError("invalid currency")
        cents = int(Decimal(amount.replace(",", "")) * 100)
        if cents > 9223372036854775807:
            raise ValueError("currency exceeds SQLite integer range")
    try:
        dt = datetime.fromisoformat(row["created_at"].strip().replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError("timezone required")
        timestamp = dt.astimezone(UTC).isoformat()
    except (ValueError, OverflowError):
        raise ValueError("invalid timestamp or missing timezone") from None
    return (row["order_id"].strip(), row["customer_id"].strip(), cents, timestamp, status)
