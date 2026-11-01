"""Exercise the shipped operator backup command against real SQLite files."""

import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "backup.py"
DATA = Path(__file__).resolve().parents[1] / "data"


def command(source, output):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--db", str(source), "--output", str(output)],
        capture_output=True,
        text=True,
    )


def test_verified_backup_and_no_overwrite(pipe, tmp_path):
    pipe.run(DATA / "clean.csv")
    source = tmp_path / "test.db"
    destination = tmp_path / "backups" / "verified.db"
    result = command(source, destination)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["integrity"] == "ok"
    with closing(sqlite3.connect(destination)) as copy:
        assert copy.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 2
        assert copy.execute("SELECT COUNT(*) FROM audit").fetchone()[0] == len(pipe.audit())
    original = destination.read_bytes()
    assert command(source, destination).returncode == 1
    assert destination.read_bytes() == original
    assert command(source, source).returncode == 1
    assert pipe.health()["database"] == "ok"


def test_missing_source_does_not_create_backup(tmp_path):
    output = tmp_path / "backup.db"
    assert command(tmp_path / "missing.db", output).returncode == 1
    assert not output.exists()
