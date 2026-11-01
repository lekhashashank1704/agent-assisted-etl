"""Scripted demo fixture. Never calls the API."""

import argparse
import json
import uuid
from pathlib import Path

from report import write_report

from etl_agents.pipeline import Pipeline
from etl_agents.planner import DemoPlanner


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="output/lab")
    out = Path(parser.parse_args().output)
    out.mkdir(parents=True, exist_ok=True)
    database = out / ("lab-" + uuid.uuid4().hex + ".db")
    pipe = Pipeline(database)
    data = Path(__file__).resolve().parents[1] / "data"
    scenarios = []

    def run(name, file, expected="loaded", **kwargs):
        result = pipe.run(data / file, **kwargs)
        assert result["status"] == expected, result
        scenarios.append({"scenario": name, **result})
        return result

    try:
        run("1 Clean batch", "clean.csv")
        run("2 Preapproved alias", "alias.csv")
        run("3 US currency", "currency.csv", us_thousands=True)
        run("4a Partial quarantine (20%)", "mixed.csv")
        run("4b Whole quarantine (>20%)", "quarantine.csv", "quarantined")
        proposal = run(
            "5 Unknown mapping", "unknown.csv", "awaiting_approval", planner=DemoPlanner()
        )
        pipe.approve(proposal["proposal_id"], "demo-operator")
        run("6 Approved resume", "unknown.csv", approval=proposal["proposal_id"])
        before = pipe.analytics()
        run("7 Injected failure", "recovery.csv", "failed", fail_after=1)
        assert pipe.analytics() == before
        assert run("8 Recovery", "recovery.csv")["loaded"] == 2
        assert run("9 Idempotent rerun", "recovery.csv")["loaded"] == 0
        before = pipe.analytics()
        run("10 Conflict rollback", "conflict.csv", "failed")
        assert pipe.analytics() == before
        report = {
            "planner": "DemoPlanner: scripted demo fixture; no API calls",
            "database": str(database),
            "scenarios": scenarios,
            "analytics": pipe.analytics(),
            "audit": pipe.audit(),
            "live_api_validation": "pending",
        }
        write_report(report, out)
        print(
            json.dumps(
                {
                    "scenarios_passed": len(scenarios),
                    "analytics": report["analytics"],
                    "report": str(out / "report.html"),
                },
                indent=2,
            )
        )
    finally:
        pipe.close()


if __name__ == "__main__":
    main()
