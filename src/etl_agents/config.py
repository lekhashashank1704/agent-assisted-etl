"""Explicit execution limits; credentials remain exclusively in the environment."""

from dataclasses import dataclass

CONTRACT_VERSION = "orders-v1"
FIELDS = ("order_id", "customer_id", "amount", "created_at", "status")
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SourceLimits:
    """Bound in-memory inspection before any model request or warehouse write."""

    max_bytes: int = 10 * 1024 * 1024
    max_rows: int = 100_000
    max_columns: int = 32
    max_header_length: int = 128

    def __post_init__(self) -> None:
        if min(self.max_bytes, self.max_rows, self.max_columns, self.max_header_length) < 1:
            raise ValueError("Source limits must be positive")
