"""Deterministic inspection, approval, quality gating and transactional loading."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .config import CONTRACT_VERSION as VERSION
from .config import SourceLimits
from .contract import transform
from .errors import ApprovalError, ETLError, InjectedFailure, LoadConflict, SourceError
from .planner import Planner, PlanningError, known_mapping, validate
from .storage import connect, transaction


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def inspect(
    path: str | Path, limits: SourceLimits | None = None
) -> tuple[list[str], list[dict[Any, Any]], str]:
    """Hash and parse the same bounded byte snapshot; never sample cell data for AI."""
    limits = limits or SourceLimits()
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(limits.max_bytes + 1)
        if len(raw) > limits.max_bytes:
            raise SourceError("Input exceeds configured byte limit")
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
        headers = reader.fieldnames
        if (
            not headers
            or len(headers) > limits.max_columns
            or any(not h.strip() or len(h) > limits.max_header_length for h in headers)
            or len(headers) != len(set(headers))
        ):
            raise SourceError("Invalid or duplicate CSV headers")
        rows: list[dict[Any, Any]] = []
        for row in reader:
            if len(rows) >= limits.max_rows:
                raise SourceError("Input exceeds configured row limit")
            rows.append(row)
        return list(headers), rows, hashlib.sha256(raw).hexdigest()
    except (OSError, UnicodeError, csv.Error):
        raise SourceError(
            "Source is unreadable, is not UTF-8, or contains invalid CSV syntax"
        ) from None


def approval_binding(proposal: sqlite3.Row) -> str:
    payload = {key: proposal[key] for key in ("id", "input_hash", "contract", "mapping", "options")}
    return hashlib.sha256(canonical(payload).encode()).hexdigest()


class Pipeline:
    """Single-process facade; each instance owns exactly one SQLite connection."""

    def __init__(self, database: str | Path, limits: SourceLimits | None = None):
        self.db = connect(database)
        self.limits = limits or SourceLimits()

    def __enter__(self) -> Pipeline:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def close(self) -> None:
        self.db.close()

    def event(self, run: str, event: str, detail: Any) -> None:
        self.db.execute(
            "INSERT INTO audit(run_id,event,detail) VALUES(?,?,?)", (run, event, canonical(detail))
        )

    def approve(self, proposal_id: str, operator: str) -> None:
        if not operator.strip() or len(operator) > 128:
            raise ApprovalError("Operator must contain 1-128 characters")
        with transaction(self.db):
            proposal = self.db.execute(
                "SELECT * FROM proposals WHERE id=?", (proposal_id,)
            ).fetchone()
            if (
                not proposal
                or proposal["consumed"]
                or proposal["approved_by"]
                or proposal["contract"] != VERSION
            ):
                raise ApprovalError("Stale, consumed, or already approved proposal")
            mapping = json.loads(proposal["mapping"])
            validate(list(mapping), mapping)
            self.db.execute(
                """UPDATE proposals SET approved_by=?, approval_digest=?,
                approved_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?""",
                (operator.strip(), approval_binding(proposal), proposal_id),
            )
            self.event(
                proposal["run_id"] or proposal_id,
                "approved",
                {"operator": operator.strip(), "proposal_id": proposal_id},
            )

    def _approved_mapping(
        self, approval: str, digest: str, options: str, headers: list[str]
    ) -> dict[str, str]:
        proposal = self.db.execute("SELECT * FROM proposals WHERE id=?", (approval,)).fetchone()
        if (
            not proposal
            or not proposal["approved_by"]
            or proposal["consumed"]
            or proposal["input_hash"] != digest
            or proposal["contract"] != VERSION
            or proposal["options"] != options
            or proposal["approval_digest"] != approval_binding(proposal)
        ):
            raise ApprovalError("Stale, consumed, modified, or mismatched approval")
        return validate(headers, json.loads(proposal["mapping"]))

    def run(
        self,
        path: str | Path,
        planner: Planner | None = None,
        approval: str | None = None,
        us_thousands: bool = False,
        fail_after: int | None = None,
    ) -> dict[str, Any]:
        """Persist an attempt; commit load, approval consumption and success atomically."""
        run = uuid.uuid4().hex
        options = canonical({"us_thousands": us_thousands})
        result: dict[str, Any] = {
            "run_id": run,
            "input_hash": None,
            "loaded": 0,
            "skipped": 0,
            "invalid": 0,
            "quarantined": 0,
        }
        self.db.execute("INSERT INTO runs VALUES(?,?,?,?,?)", (run, None, VERSION, "started", "{}"))
        try:
            if planner is not None and approval is not None:
                raise ApprovalError("Planner and approval cannot be supplied together")
            if fail_after is not None and fail_after < 1:
                raise ValueError("Failure injection requires a positive insert count")
            headers, rows, digest = inspect(path, self.limits)
            result.update(input_hash=digest, source_rows=len(rows))
            self.db.execute("UPDATE runs SET input_hash=? WHERE id=?", (digest, run))
            self.event(
                run, "inspected", {"input_hash": digest, "rows": len(rows), "contract": VERSION}
            )
            if approval:
                mapping = self._approved_mapping(approval, digest, options, headers)
            else:
                try:
                    mapping = known_mapping(headers)
                except PlanningError:
                    if planner is None:
                        raise PlanningError("Unknown schema requires explicit planner") from None
                    mapping = validate(headers, planner.propose(headers))
                    proposal_id = uuid.uuid4().hex
                    with transaction(self.db):
                        self.db.execute(
                            "INSERT INTO proposals(id,input_hash,contract,mapping,options,run_id) VALUES(?,?,?,?,?,?)",
                            (proposal_id, digest, VERSION, canonical(mapping), options, run),
                        )
                        result.update(
                            status="awaiting_approval", proposal_id=proposal_id, mapping=mapping
                        )
                        self.event(
                            run,
                            "proposed",
                            {
                                "proposal_id": proposal_id,
                                "mapping": mapping,
                                "planner": type(planner).__name__,
                            },
                        )
                        self.finish(run, result)
                    return result
            self.event(run, "mapping_selected", {"mapping": mapping, "approval": approval})
            valid, invalid = [], []
            for number, row in enumerate(rows, 2):
                try:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError("Malformed CSV row")
                    record = transform(
                        {target: row[source] for source, target in mapping.items()}, us_thousands
                    )
                    valid.append(record)
                except ValueError as exc:
                    invalid.append((number, row, str(exc)))
            result["invalid"] = len(invalid)
            whole = not rows or len(invalid) * 5 > len(rows)
            reasons = {number: reason for number, _, reason in invalid}
            rejected = (
                invalid
                if not whole
                else [
                    (number, row, reasons.get(number, "batch exceeds quality threshold"))
                    for number, row in enumerate(rows, 2)
                ]
            )
            result["quarantined"] = len(rejected)
            with transaction(self.db):
                self.db.executemany(
                    "INSERT INTO quarantine VALUES(?,?,?,?)",
                    [(run, n, json.dumps(row), reason) for n, row, reason in rejected],
                )
                self.event(
                    run,
                    "validated",
                    {
                        "valid": len(valid),
                        "invalid": len(invalid),
                        "whole_batch": whole,
                        "quarantined": len(rejected),
                    },
                )
                if whole:
                    result["status"] = "quarantined"
                    self.finish(run, result)
            if whole:
                return result
            with transaction(self.db):
                if approval:
                    # Re-read the complete binding under the write lock, not only consumption.
                    self._approved_mapping(approval, digest, options, headers)
                    self.db.execute(
                        """UPDATE proposals SET consumed=1,
                        consumed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?""",
                        (approval,),
                    )
                loaded, skipped = 0, 0
                for record in valid:
                    old = self.db.execute(
                        "SELECT order_id,customer_id,amount_cents,created_at,status FROM orders WHERE order_id=?",
                        (record[0],),
                    ).fetchone()
                    if old and tuple(old) != record:
                        raise LoadConflict("Conflicting existing order")
                    if old:
                        skipped += 1
                    else:
                        self.db.execute("INSERT INTO orders VALUES(?,?,?,?,?)", record)
                        loaded += 1
                        if fail_after is not None and loaded >= fail_after:
                            raise InjectedFailure("Injected load failure")
                result.update(status="loaded", loaded=loaded, skipped=skipped)
                self.event(
                    run,
                    "load_committed",
                    {"inserted": loaded, "skipped": skipped, "approval": approval},
                )
                self.finish(run, result)
            return result
        except (ETLError, ValueError, sqlite3.Error) as exc:
            safe_message = str(exc) if isinstance(exc, ValueError) else "Storage operation failed"
            result.update(
                status="failed",
                error=safe_message,
                error_code=getattr(
                    exc,
                    "code",
                    "VALIDATION_ERROR" if isinstance(exc, ValueError) else "STORAGE_ERROR",
                ),
                loaded=0,
                skipped=0,
            )
            with transaction(self.db):
                self.finish(run, result)
            return result

    def finish(self, run: str, result: dict[str, Any]) -> dict[str, Any]:
        self.db.execute(
            "UPDATE runs SET status=?,result=? WHERE id=?",
            (result["status"], canonical(result), run),
        )
        self.event(run, result["status"], result)
        return result

    def analytics(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.db.execute(
                "SELECT status, COUNT(*) AS orders, COALESCE(SUM(amount_cents),0) AS total_cents FROM orders GROUP BY status ORDER BY status"
            )
        ]

    def audit(self, run_id: str | None = None) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.db.execute(
                "SELECT * FROM audit WHERE (? IS NULL OR run_id=?) ORDER BY id", (run_id, run_id)
            )
        ]

    def runs(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute("SELECT * FROM runs ORDER BY rowid")]

    def proposals(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute("SELECT * FROM proposals ORDER BY rowid")]

    def quarantine(self, run_id: str | None = None) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.db.execute(
                "SELECT * FROM quarantine WHERE (? IS NULL OR run_id=?) ORDER BY rowid",
                (run_id, run_id),
            )
        ]

    def health(self) -> dict[str, Any]:
        return {
            "database": self.db.execute("PRAGMA quick_check").fetchone()[0],
            "schema_version": self.db.execute("PRAGMA user_version").fetchone()[0],
        }
