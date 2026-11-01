import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from etl_agents.contract import transform
from etl_agents.pipeline import Pipeline, inspect
from etl_agents.planner import FIELDS, DemoPlanner, OpenAIPlanner, PlanningError, validate

DATA = Path(__file__).resolve().parents[1] / "data"


def test_clean_alias_and_analytics(pipe):
    assert pipe.run(DATA / "clean.csv")["loaded"] == 2
    assert pipe.run(DATA / "alias.csv")["loaded"] == 1
    assert pipe.analytics() == [
        {"status": "paid", "orders": 2, "total_cents": 2500},
        {"status": "pending", "orders": 1, "total_cents": 0},
    ]


@pytest.mark.parametrize(
    "amount,status,us,expected",
    [
        ("0", "paid", False, 0),
        ("12.34", "paid", False, 1234),
        ("1,234.56", "paid", True, 123456),
        ("", "pending", False, None),
    ],
)
def test_currency_valid(amount, status, us, expected):
    assert (
        transform(
            dict(zip(FIELDS, ["a", "c", amount, "2026-01-01T10:00:00+05:30", status], strict=True)),
            us,
        )[2]
        == expected
    )


@pytest.mark.parametrize(
    "amount,status,us",
    [
        ("-1", "paid", False),
        ("1.234", "paid", False),
        ("NaN", "paid", False),
        ("1e2", "paid", False),
        ("1,234.56", "paid", False),
        ("12,34", "paid", True),
        ("", "paid", False),
        ("", "cancelled", False),
        ("92233720368547758.08", "paid", False),
    ],
)
def test_currency_invalid(amount, status, us):
    with pytest.raises(ValueError):
        transform(
            dict(zip(FIELDS, ["a", "c", amount, "2026-01-01T00:00:00Z", status], strict=True)), us
        )


@pytest.mark.parametrize(
    "key,value",
    [
        ("order_id", " "),
        ("customer_id", ""),
        ("status", "PAID"),
        ("created_at", "2026-01-01T00:00:00"),
        ("created_at", "bad"),
    ],
)
def test_contract_rejections(key, value):
    row = dict(zip(FIELDS, ["a", "c", "1.00", "2026-01-01T00:00:00Z", "paid"], strict=True))
    row[key] = value
    with pytest.raises(ValueError):
        transform(row)


def test_utc():
    assert (
        transform(
            dict(zip(FIELDS, ["a", "c", "1", "2026-01-01T10:00:00+05:30", "paid"], strict=True))
        )[3]
        == "2026-01-01T04:30:00+00:00"
    )


def test_threshold(pipe):
    partial = pipe.run(DATA / "mixed.csv")
    assert (partial["status"], partial["loaded"], partial["invalid"]) == ("loaded", 4, 1)
    whole = pipe.run(DATA / "quarantine.csv")
    assert whole["status"] == "quarantined"
    assert pipe.db.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0] == 3


@pytest.mark.parametrize(
    "mapping",
    [
        dict(zip(FIELDS, FIELDS[:-1] + ("amount",), strict=True)),
        {"invented": "customer_id"},
        dict(zip(FIELDS, ("bogus",) + FIELDS[1:], strict=True)),
        dict(zip(FIELDS, ("customer_id", "order_id") + FIELDS[2:], strict=True)),
    ],
)
def test_invalid_proposals(mapping):
    with pytest.raises(PlanningError):
        validate(list(FIELDS), mapping)


def test_unknown_requires_approval(pipe):
    assert pipe.run(DATA / "unknown.csv")["status"] == "failed"
    result = pipe.run(DATA / "unknown.csv", DemoPlanner())
    assert result["status"] == "awaiting_approval"
    assert pipe.analytics() == []
    assert pipe.run(DATA / "unknown.csv", approval=result["proposal_id"])["status"] == "failed"
    pipe.approve(result["proposal_id"], "operator")
    assert pipe.run(DATA / "unknown.csv", approval=result["proposal_id"])["loaded"] == 1
    assert pipe.run(DATA / "unknown.csv", approval=result["proposal_id"])["status"] == "failed"
    with pytest.raises(ValueError):
        pipe.approve(result["proposal_id"], "operator")


def test_stale_input_and_options(pipe, tmp_path):
    result = pipe.run(DATA / "unknown.csv", DemoPlanner())
    pipe.approve(result["proposal_id"], "operator")
    changed = tmp_path / "changed.csv"
    changed.write_bytes((DATA / "unknown.csv").read_bytes() + b"\n")
    assert pipe.run(changed, approval=result["proposal_id"])["status"] == "failed"
    assert (
        pipe.run(DATA / "unknown.csv", approval=result["proposal_id"], us_thousands=True)["status"]
        == "failed"
    )
    pipe.db.execute("UPDATE proposals SET contract='old'")
    assert pipe.run(DATA / "unknown.csv", approval=result["proposal_id"])["status"] == "failed"


def test_approval_rollback_and_recovery(pipe):
    result = pipe.run(DATA / "unknown.csv", DemoPlanner())
    pipe.approve(result["proposal_id"], "operator")
    assert (
        pipe.run(DATA / "unknown.csv", approval=result["proposal_id"], fail_after=1)["status"]
        == "failed"
    )
    assert pipe.analytics() == []
    assert pipe.db.execute("SELECT consumed FROM proposals").fetchone()[0] == 0
    assert pipe.run(DATA / "unknown.csv", approval=result["proposal_id"])["loaded"] == 1


def test_transaction_and_idempotency(pipe):
    assert pipe.run(DATA / "recovery.csv", fail_after=1)["status"] == "failed"
    assert pipe.analytics() == []
    assert pipe.run(DATA / "recovery.csv")["loaded"] == 2
    assert pipe.run(DATA / "recovery.csv")["loaded"] == 0
    assert any(e["event"] == "failed" for e in pipe.audit())


def test_conflict_rolls_back_prior_insert(pipe):
    pipe.run(DATA / "clean.csv")
    before = pipe.analytics()
    assert pipe.run(DATA / "conflict.csv")["status"] == "failed"
    assert pipe.analytics() == before
    assert not pipe.db.execute("SELECT 1 FROM orders WHERE order_id='o15'").fetchone()


def test_duplicate_headers(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("a,a\n1,2\n")
    with pytest.raises(ValueError):
        inspect(path)


def test_malformed_rows_quarantine(pipe, tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text(",".join(FIELDS) + "\na,c,1,2026-01-01T00:00:00Z,paid,extra\n")
    assert pipe.run(path)["status"] == "quarantined"


def client_response(text, status="completed"):
    client = Mock()
    client.responses.create.return_value = SimpleNamespace(status=status, output_text=text)
    return client


def test_mocked_api_request_privacy_and_shape():
    headers = ["order_id", "client_ref", "amount", "created_at", "status"]
    pairs = [{"source": h, "target": "customer_id" if h == "client_ref" else h} for h in headers]
    client = client_response(json.dumps({"mappings": pairs}))
    assert OpenAIPlanner(client).propose(headers)["client_ref"] == "customer_id"
    call = client.responses.create.call_args.kwargs
    assert call["text"]["format"]["strict"] is True
    assert call["store"] is False
    assert set(json.loads(call["input"])) == {"columns", "contract"}
    assert "rows" not in call["input"]


@pytest.mark.parametrize(
    "text,status",
    [
        ("", "completed"),
        ("{}", "completed"),
        ('{"mappings":[]}', "incomplete"),
        ('{"mappings":[]}', "completed"),
        ('{"refusal":"no"}', "completed"),
        (
            '{"mappings":[{"source":"x","target":"amount"},{"source":"x","target":"status"}]}',
            "completed",
        ),
    ],
)
def test_api_refusals_invalid_and_incomplete(text, status):
    with pytest.raises(PlanningError):
        OpenAIPlanner(client_response(text, status)).propose(list(FIELDS))


def test_api_failure_fails_closed_and_redacts(pipe):
    client = Mock()
    client.responses.create.side_effect = RuntimeError("sensitive request detail")
    result = pipe.run(DATA / "unknown.csv", OpenAIPlanner(client))
    assert result["status"] == "failed"
    assert "sensitive" not in json.dumps(pipe.audit())
    assert pipe.analytics() == []


def test_sdk_timeout_retry_configuration(monkeypatch):
    factory = Mock()
    monkeypatch.setattr("openai.OpenAI", factory)
    with pytest.raises(PlanningError):
        OpenAIPlanner().propose(list(FIELDS))
    factory.assert_called_once_with(timeout=20.0, max_retries=2)


def test_sdk_transient_retries_are_bounded(monkeypatch):
    import httpx
    from openai import OpenAI

    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            503, json={"error": {"message": "unavailable", "type": "server_error"}}
        )

    monkeypatch.setattr("openai._base_client.time.sleep", lambda _: None)
    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        client = OpenAI(api_key="test-placeholder", http_client=http, timeout=20.0, max_retries=2)
        with pytest.raises(PlanningError):
            OpenAIPlanner(client).propose(list(FIELDS))
    assert len(calls) == 3


def test_sdk_nontransient_failure_not_retried(monkeypatch):
    import httpx
    from openai import OpenAI

    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            401, json={"error": {"message": "unauthorized", "type": "authentication_error"}}
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        client = OpenAI(api_key="test-placeholder", http_client=http, timeout=20.0, max_retries=2)
        with pytest.raises(PlanningError):
            OpenAIPlanner(client).propose(list(FIELDS))
    assert len(calls) == 1


def test_empty_batch(pipe, tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text(",".join(FIELDS) + "\n")
    assert pipe.run(path)["status"] == "quarantined"


def test_within_batch_conflict(pipe, tmp_path):
    path = tmp_path / "duplicates.csv"
    path.write_text(
        ",".join(FIELDS) + "\na,c,1,2026-01-01T00:00:00Z,paid\na,c,2,2026-01-01T00:00:00Z,paid\n"
    )
    assert pipe.run(path)["status"] == "failed"
    assert pipe.analytics() == []


def test_persisted_approval_resume(tmp_path):
    db = tmp_path / "persistent.db"
    p = Pipeline(db)
    proposal = p.run(DATA / "unknown.csv", DemoPlanner())["proposal_id"]
    p.close()
    p = Pipeline(db)
    p.approve(proposal, "operator")
    p.close()
    p = Pipeline(db)
    try:
        assert p.run(DATA / "unknown.csv", approval=proposal)["loaded"] == 1
        assert any(e["event"] == "approved" for e in p.audit())
    finally:
        p.close()


def test_cli_smoke_and_expected_exit_codes(tmp_path):
    import subprocess
    import sys

    def cli(*args):
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "etl_agents.cli",
                "--db",
                str(tmp_path / "cli.db"),
                *map(str, args),
            ],
            capture_output=True,
            text=True,
        )

    assert cli("inspect", DATA / "clean.csv").returncode == 0
    assert cli("run", DATA / "clean.csv").returncode == 0
    awaiting = cli("run", DATA / "unknown.csv", "--planner", "demo")
    assert awaiting.returncode == 2
    proposal = json.loads(awaiting.stdout)["proposal_id"]
    assert cli("approve", proposal, "--operator", "cli-tester").returncode == 0
    assert cli("run", DATA / "unknown.csv", "--approval", proposal).returncode == 0
    assert cli("run", DATA / "unknown.csv", "--approval", proposal).returncode == 1
    for command in ("analytics", "audit", "proposals"):
        assert cli(command).returncode == 0
