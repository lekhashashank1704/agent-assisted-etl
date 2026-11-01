"""JSON-first command interface with predictable process exit semantics."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .config import SourceLimits
from .pipeline import Pipeline, inspect
from .planner import DemoPlanner, OpenAIPlanner


def positive_integer(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Must be a positive integer")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Agent-Assisted ETL: Schema Drift, Approvals & Recovery"
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--db", default="output/warehouse.db", help="SQLite database path")
    parser.add_argument("--max-input-bytes", type=positive_integer, default=10 * 1024 * 1024)
    parser.add_argument("--max-rows", type=positive_integer, default=100_000)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Inspect, validate and load a CSV batch")
    run.add_argument("csv")
    choice = run.add_mutually_exclusive_group()
    choice.add_argument("--planner", choices=["demo", "live"])
    choice.add_argument("--approval")
    run.add_argument("--us-thousands", action="store_true")
    run.add_argument(
        "--fail-after", type=positive_integer, help="Lab fault injection after N inserts"
    )
    approve = commands.add_parser("approve", help="Approve the exact saved proposal")
    approve.add_argument("proposal_id")
    approve.add_argument("--operator", required=True)
    info = commands.add_parser("inspect", help="Inspect a source without opening a database")
    info.add_argument("csv")
    for name in ("analytics", "proposals", "runs", "health"):
        commands.add_parser(name)
    for name in ("audit", "quarantine"):
        command = commands.add_parser(name)
        command.add_argument("--run-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        limits = SourceLimits(max_bytes=args.max_input_bytes, max_rows=args.max_rows)
        result: Any
        if args.command == "inspect":
            headers, rows, digest = inspect(args.csv, limits)
            result = {"columns": headers, "rows": len(rows), "input_hash": digest}
        else:
            if args.command == "health" and args.db != ":memory:" and not Path(args.db).is_file():
                raise ValueError("Database does not exist")
            if args.db != ":memory:":
                Path(args.db).parent.mkdir(parents=True, exist_ok=True)
            with Pipeline(args.db, limits) as pipe:
                if args.command == "run":
                    planner = (
                        DemoPlanner()
                        if args.planner == "demo"
                        else OpenAIPlanner()
                        if args.planner == "live"
                        else None
                    )
                    result = pipe.run(
                        args.csv, planner, args.approval, args.us_thousands, args.fail_after
                    )
                elif args.command == "approve":
                    pipe.approve(args.proposal_id, args.operator)
                    result = {"approved": args.proposal_id}
                elif args.command in ("audit", "quarantine"):
                    result = getattr(pipe, args.command)(args.run_id)
                else:
                    result = getattr(pipe, args.command)()
        print(json.dumps(result, indent=2))
        if isinstance(result, dict):
            if (
                result.get("status") in ("failed", "quarantined")
                or result.get("database", "ok") != "ok"
            ):
                return 1
            if result.get("status") == "awaiting_approval":
                return 2
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        error = (
            str(exc) if isinstance(exc, ValueError) else "Filesystem or database operation failed"
        )
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": error,
                    "error_code": getattr(exc, "code", "OPERATION_FAILED"),
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
