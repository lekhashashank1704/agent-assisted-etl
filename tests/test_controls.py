"""Governance, persistence and operational boundary regressions."""

import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

from etl_agents.config import SourceLimits
from etl_agents.errors import StorageError
from etl_agents.pipeline import Pipeline, inspect
from etl_agents.planner import FIELDS, DemoPlanner, OpenAIPlanner, PlanningError, validate

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.mark.parametrize("limits", [SourceLimits(max_bytes=10), SourceLimits(max_rows=1)])
def test_input_limits_are_enforced_and_audited(tmp_path, limits):
    with Pipeline(tmp_path / "limited.db", limits) as pipe:
        result = pipe.run(DATA / "clean.csv")
        assert result["status"] == "failed"
        assert result["error_code"] == "SOURCE_INVALID"
        assert pipe.analytics() == []
        assert pipe.audit(result["run_id"])[-1]["event"] == "failed"


@pytest.mark.parametrize(
    "content", [b"\xff\xfe", b'order_id,customer_id,amount,created_at,status\na,c,1,"unclosed']
)
def test_invalid_encoding_and_csv_are_audited(pipe, tmp_path, content):
    source = tmp_path / "bad.csv"
    source.write_bytes(content)
    result = pipe.run(source)
    assert result["status"] == "failed"
    assert result["error_code"] == "SOURCE_INVALID"
    assert pipe.audit(result["run_id"])[-1]["event"] == "failed"


def test_missing_source_produces_safe_audit(pipe, tmp_path):
    result = pipe.run(tmp_path / "does-not-exist.csv")
    assert result["status"] == "failed"
    assert "does-not-exist" not in result["error"]


def test_approval_event_correlates_to_originating_run(pipe):
    proposal = pipe.run(DATA / "unknown.csv", DemoPlanner())
    pipe.approve(proposal["proposal_id"], "reviewer")
    events = pipe.audit(proposal["run_id"])
    assert any(event["event"] == "approved" for event in events)
    saved = pipe.proposals()[0]
    assert saved["approved_at"] and saved["approval_digest"]


def test_postapproval_mapping_modification_rejected(pipe):
    proposal = pipe.run(DATA / "unknown.csv", DemoPlanner())
    pipe.approve(proposal["proposal_id"], "reviewer")
    pipe.db.execute("UPDATE proposals SET mapping=?", (json.dumps(proposal["mapping"], indent=2),))
    result = pipe.run(DATA / "unknown.csv", approval=proposal["proposal_id"])
    assert result["error_code"] == "APPROVAL_INVALID"
    assert pipe.analytics() == []


def test_binding_rechecked_under_load_lock(pipe, monkeypatch):
    from etl_agents.contract import transform

    proposal = pipe.run(DATA / "unknown.csv", DemoPlanner())
    pipe.approve(proposal["proposal_id"], "reviewer")

    def mutate_during_validation(row, us_thousands=False):
        pipe.db.execute("UPDATE proposals SET options='{}'")
        return transform(row, us_thousands)

    monkeypatch.setattr("etl_agents.pipeline.transform", mutate_during_validation)
    result = pipe.run(DATA / "unknown.csv", approval=proposal["proposal_id"])
    assert result["error_code"] == "APPROVAL_INVALID"
    assert pipe.proposals()[0]["consumed"] == 0
    assert pipe.analytics() == []


def test_consumption_visible_to_second_connection(tmp_path):
    database = tmp_path / "shared.db"
    with Pipeline(database) as first, Pipeline(database) as second:
        result = first.run(DATA / "unknown.csv", DemoPlanner())
        first.approve(result["proposal_id"], "reviewer")
        assert second.run(DATA / "unknown.csv", approval=result["proposal_id"])["loaded"] == 1
        assert first.run(DATA / "unknown.csv", approval=result["proposal_id"])["status"] == "failed"
        assert second.proposals()[0]["consumed_at"]


def test_health_and_run_filtered_queries(pipe):
    result = pipe.run(DATA / "quarantine.csv")
    assert pipe.health() == {"database": "ok", "schema_version": 1}
    assert pipe.runs()[-1]["status"] == "quarantined"
    assert len(pipe.quarantine(result["run_id"])) == 2
    assert pipe.quarantine("missing") == []
    assert pipe.audit("missing") == []
    assert result["quarantined"] == 2
    assert pipe.quarantine(result["run_id"])[0]["reason"] == "invalid currency"


def test_future_schema_fails_closed(tmp_path):
    database = tmp_path / "future.db"
    with closing(sqlite3.connect(database)) as db, db:
        db.execute("PRAGMA user_version=99")
    with pytest.raises(StorageError, match="newer"):
        Pipeline(database)
    with closing(sqlite3.connect(database)) as db, db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 99


def test_legacy_schema_migration_preserves_orders(tmp_path):
    database = tmp_path / "legacy.db"
    with closing(sqlite3.connect(database)) as db, db:
        db.executescript("""
            CREATE TABLE orders(order_id TEXT PRIMARY KEY, customer_id TEXT, amount_cents INTEGER, created_at TEXT, status TEXT);
            CREATE TABLE proposals(id TEXT PRIMARY KEY,input_hash TEXT,contract TEXT,mapping TEXT,options TEXT,approved_by TEXT,consumed INTEGER DEFAULT 0);
            INSERT INTO orders VALUES('old','c',100,'2026-01-01T00:00:00+00:00','paid');
        """)
    with Pipeline(database) as pipe:
        assert pipe.health()["schema_version"] == 1
        assert pipe.analytics()[0]["total_cents"] == 100
        assert "approval_digest" in {
            row[1] for row in pipe.db.execute("PRAGMA table_info(proposals)")
        }


@pytest.mark.parametrize("amount,status", [(-1, "paid"), (None, "paid"), (1, "invalid")])
def test_fresh_database_constraints(pipe, amount, status):
    with pytest.raises(sqlite3.IntegrityError):
        pipe.db.execute(
            "INSERT INTO orders VALUES(?,?,?,?,?)",
            ("o", "c", amount, "2026-01-01T00:00:00Z", status),
        )


def test_identical_duplicate_inside_batch_is_skipped(pipe, tmp_path):
    source = tmp_path / "same.csv"
    line = "o,c,1,2026-01-01T00:00:00Z,paid\n"
    source.write_text(",".join(FIELDS) + "\n" + line + line)
    result = pipe.run(source)
    assert (result["loaded"], result["skipped"]) == (1, 1)


@pytest.mark.parametrize("operator", ["", " ", "x" * 129])
def test_operator_validation(pipe, operator):
    result = pipe.run(DATA / "unknown.csv", DemoPlanner())
    with pytest.raises(ValueError):
        pipe.approve(result["proposal_id"], operator)


def test_cli_operational_commands_and_inspect_has_no_database_side_effect(tmp_path):
    database = tmp_path / "cli.db"

    def cli(*args):
        return subprocess.run(
            [sys.executable, "-m", "etl_agents", "--db", str(database), *map(str, args)],
            capture_output=True,
            text=True,
        )

    assert cli("inspect", DATA / "clean.csv").returncode == 0
    assert not database.exists()
    assert cli("health").returncode == 1
    assert not database.exists()
    assert cli("run", DATA / "clean.csv").returncode == 0
    for command in ("health", "runs", "quarantine"):
        assert cli(command).returncode == 0
    assert cli("run", DATA / "clean.csv", "--fail-after", "0").returncode == 2
    assert cli("run", DATA / "unknown.csv", "--planner", "demo", "--approval", "x").returncode == 2


def test_planner_rejects_oversized_metadata_before_api_request():
    class NoCalls:
        @property
        def responses(self):
            raise AssertionError("Invalid metadata reached the API")

    with pytest.raises(PlanningError):
        OpenAIPlanner(NoCalls()).propose(["x" * 129, *FIELDS[1:]])


def test_duplicate_headers_rejected_by_mapping_validator():
    with pytest.raises(PlanningError):
        validate([*FIELDS, "status"], dict(zip(FIELDS, FIELDS, strict=True)))


def test_invalid_limit_configuration():
    with pytest.raises(ValueError):
        SourceLimits(max_rows=0)


def test_byte_limit_boundary(tmp_path):
    source = tmp_path / "headers.csv"
    raw = (",".join(FIELDS) + "\n").encode()
    source.write_bytes(raw)
    assert inspect(source, SourceLimits(max_bytes=len(raw)))[1] == []


def test_report_escapes_source_metadata(tmp_path):
    import runpy

    renderer = runpy.run_path(str(DATA.parent / "lab" / "report.py"))
    report = {
        "scenarios": [{"scenario": "<script>alert(1)</script>", "status": "loaded", "loaded": 1}],
        "analytics": [{"status": "paid", "orders": 1, "total_cents": 100}],
        "audit": [
            {
                "id": 1,
                "run_id": "<untrusted>",
                "event": "<event>",
                "detail": "<script>evil</script>",
            }
        ],
    }
    renderer["write_report"](report, tmp_path)
    page = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "<script>" not in page
    assert "&lt;script&gt;" in page
    assert json.loads((tmp_path / "results.json").read_text(encoding="utf-8")) == report


def test_cli_json_interface_and_operational_failures(tmp_path, capsys):
    from etl_agents.cli import main

    database = tmp_path / "direct.db"

    def execute(*args):
        code = main(["--db", str(database), *map(str, args)])
        captured = capsys.readouterr()
        return code, json.loads(captured.out or captured.err)

    assert execute("inspect", DATA / "clean.csv")[1]["rows"] == 2
    assert not database.exists()
    assert execute("health")[0] == 1
    assert execute("run", DATA / "clean.csv")[0] == 0
    code, proposal = execute("run", DATA / "unknown.csv", "--planner", "demo")
    assert code == 2
    assert execute("approve", proposal["proposal_id"], "--operator", "direct-reviewer")[0] == 0
    assert execute("run", DATA / "unknown.csv", "--approval", proposal["proposal_id"])[0] == 0
    assert execute("run", DATA / "unknown.csv", "--approval", proposal["proposal_id"])[0] == 1
    for command in ("proposals", "runs", "analytics", "health", "audit", "quarantine"):
        assert execute(command)[0] == 0
    assert execute("run", DATA / "quarantine.csv")[0] == 1
    assert execute("inspect", tmp_path / "missing.csv")[0] == 1


def test_conflicting_library_execution_options_are_audited(pipe):
    assert (
        pipe.run(DATA / "clean.csv", planner=DemoPlanner(), approval="x")["error_code"]
        == "APPROVAL_INVALID"
    )
    assert pipe.run(DATA / "clean.csv", fail_after=0)["status"] == "failed"


def test_malformed_model_entry_rejected():
    from types import SimpleNamespace
    from unittest.mock import Mock

    client = Mock()
    client.responses.create.return_value = SimpleNamespace(
        status="completed", output_text='{"mappings":[{"source":12,"target":"order_id"}]}'
    )
    with pytest.raises(PlanningError):
        OpenAIPlanner(client).propose(list(FIELDS))
