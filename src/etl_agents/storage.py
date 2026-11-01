"""Versioned SQLite initialization and explicit transaction ownership."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .config import SCHEMA_VERSION
from .errors import StorageError

DDL = (
    """CREATE TABLE IF NOT EXISTS orders(
        order_id TEXT PRIMARY KEY NOT NULL CHECK(length(trim(order_id)) > 0),
        customer_id TEXT NOT NULL CHECK(length(trim(customer_id)) > 0),
        amount_cents INTEGER CHECK(amount_cents IS NULL OR (typeof(amount_cents)='integer' AND amount_cents >= 0)),
        created_at TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('paid','pending','cancelled')),
        CHECK(amount_cents IS NOT NULL OR status='pending'))""",
    """CREATE TABLE IF NOT EXISTS runs(
        id TEXT PRIMARY KEY, input_hash TEXT, contract TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('started','awaiting_approval','quarantined','loaded','failed')),
        result TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS proposals(
        id TEXT PRIMARY KEY, input_hash TEXT NOT NULL, contract TEXT NOT NULL,
        mapping TEXT NOT NULL, options TEXT NOT NULL, approved_by TEXT,
        consumed INTEGER NOT NULL DEFAULT 0 CHECK(consumed IN (0,1)),
        run_id TEXT, approval_digest TEXT, approved_at TEXT, consumed_at TEXT)""",
    """CREATE TABLE IF NOT EXISTS quarantine(
        run_id TEXT NOT NULL, row_number INTEGER NOT NULL, raw TEXT NOT NULL, reason TEXT NOT NULL,
        FOREIGN KEY(run_id) REFERENCES runs(id))""",
    """CREATE TABLE IF NOT EXISTS audit(
        id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, event TEXT NOT NULL, detail TEXT NOT NULL,
        at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')))""",
)


@contextmanager
def transaction(db: sqlite3.Connection) -> Iterator[None]:
    """Serialize a unit of work; never implicitly nest transactions."""
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.commit()
    except BaseException:
        db.rollback()
        raise


def connect(database: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(database, isolation_level=None, timeout=10.0)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys=ON")
        with transaction(db):
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise StorageError("Database schema is newer than this application")
            if version == 0:
                for statement in DDL:
                    db.execute(statement)
                # Upgrade the original unversioned portfolio database additively.
                columns = {r[1] for r in db.execute("PRAGMA table_info(proposals)")}
                for name in ("run_id", "approval_digest", "approved_at", "consumed_at"):
                    if name not in columns:
                        db.execute(f"ALTER TABLE proposals ADD COLUMN {name} TEXT")
                db.execute("CREATE INDEX IF NOT EXISTS idx_audit_run ON audit(run_id,id)")
                db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_quarantine_run ON quarantine(run_id,row_number)"
                )
                db.execute("CREATE INDEX IF NOT EXISTS idx_runs_hash ON runs(input_hash)")
                db.execute("PRAGMA user_version=1")
        # FULL favors durable commits; WAL is deliberately not assumed by deployment.
        db.execute("PRAGMA synchronous=FULL")
        return db
    except BaseException:
        db.close()
        raise
