"""Create a verified SQLite backup without modifying the source or overwriting files."""

from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path


def backup(source: Path, destination: Path) -> dict[str, str]:
    source = source.resolve(strict=True)
    destination = destination.resolve()
    if source == destination:
        raise ValueError("Backup destination must differ from the source")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Reserve the output exclusively. A failed copy is retained for investigation;
    # it must not be treated as verified unless this command exits successfully.
    with destination.open("xb"):
        pass
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as origin:
        with closing(sqlite3.connect(destination)) as target:
            origin.backup(target)
            integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise ValueError("Backup integrity verification failed")
    return {"status": "verified", "backup": destination.name, "integrity": integrity}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(backup(args.db, args.output), indent=2))
        return 0
    except (OSError, ValueError, sqlite3.Error):
        parser.exit(
            1,
            "Backup failed: verify source, destination, permissions and integrity. Existing files are never overwritten.\n",
        )


if __name__ == "__main__":
    raise SystemExit(main())
