"""Accessible static lab reporting. All untrusted strings are HTML-escaped."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

STYLE = """
:root { color-scheme: light; font-family: system-ui, sans-serif; color: #163047; background: #f1f5f8; }
body { max-width: 1180px; margin: 0 auto; padding: 36px 24px; line-height: 1.5; }
header, section { background: white; border: 1px solid #dce4ec; border-radius: 10px; padding: 24px; margin-bottom: 20px; }
h1 { font-size: 30px; line-height: 1.2; margin-top: 4px; } h2 { font-size: 21px; }
.eyebrow { color: #35718c; text-transform: uppercase; letter-spacing: .08em; font-size: 12px; font-weight: 700; }
.summary { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 20px; }
.metric { background: #edf5f8; padding: 14px 18px; border-radius: 6px; min-width: 130px; }
.metric strong { display: block; font-size: 26px; }
table { border-collapse: collapse; width: 100%; font-size: 14px; } th, td { text-align: left; padding: 11px 9px; border-bottom: 1px solid #e2e9ef; vertical-align: top; }
th { color: #496274; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
.numeric { text-align: right; } .scroll { overflow-x: auto; }
code, pre { font: 12px ui-monospace, monospace; } pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f4f7fa; padding: 12px; }
.notice { border-left: 4px solid #cf9b33; padding-left: 14px; } .muted { color: #526b7c; }
summary { cursor: pointer; } a { color: #12628a; } footer { font-size: 12px; color: #526b7c; }
"""


def escaped(value: Any) -> str:
    return html.escape(str(value), quote=True)


def write_report(report: dict[str, Any], output: Path) -> None:
    scenarios = report["scenarios"]
    rows = []
    for scenario in scenarios:
        cells = [escaped(scenario["scenario"]), escaped(scenario["status"])]
        cells += [
            str(scenario.get(key, 0)) for key in ("loaded", "skipped", "invalid", "quarantined")
        ]
        rows.append("<tr>" + "".join("<td>" + cell + "</td>" for cell in cells) + "</tr>")
    analytics = "".join(
        "<tr><td>"
        + escaped(row["status"])
        + "</td><td class='numeric'>"
        + str(row["orders"])
        + "</td><td class='numeric'>"
        + str(row["total_cents"])
        + "</td></tr>"
        for row in report["analytics"]
    )
    audit = []
    for event in report["audit"]:
        audit.append(
            "<tr><td>"
            + str(event["id"])
            + "</td><td><code>"
            + escaped(event["run_id"])
            + "</code></td><td>"
            + escaped(event["event"])
            + "</td><td><details><summary>Event detail</summary><pre>"
            + escaped(event["detail"])
            + "</pre></details></td></tr>"
        )
    total_orders = sum(row["orders"] for row in report["analytics"])
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent-Assisted ETL | Verification report</title><style>{STYLE}</style></head><body>
<header><p class="eyebrow">Execution evidence / synthetic orders</p>
<h1>Agent-Assisted ETL: Schema Drift, Approvals &amp; Recovery</h1>
<p class="muted">Deterministic execution, governed schema mapping and transactional recovery.</p>
<p class="notice">Planner: explicit scripted demo fixture. No API calls. Live API validation remains pending.</p>
<div class="summary"><div class="metric"><strong>{len(scenarios)}</strong>scenario checks</div><div class="metric"><strong>{total_orders}</strong>warehouse orders</div><div class="metric"><strong>{len(report["audit"])}</strong>audit events</div></div></header>
<section><h2>Scenario outcomes</h2><p>Failed and quarantined outcomes below are expected control checks; the script verifies each expectation.</p>
<div class="scroll"><table><thead><tr><th>Scenario</th><th>Outcome</th><th>Inserted</th><th>Skipped</th><th>Invalid</th><th>Quarantined</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>
<section><h2>Deterministic warehouse analytics</h2><table><thead><tr><th>Status</th><th class="numeric">Orders</th><th class="numeric">Total cents</th></tr></thead><tbody>{analytics}</tbody></table><p class="muted">A pending NULL amount contributes zero to the aggregate; money is stored as integer cents.</p></section>
<section><h2>Audit trail</h2><p>Events correlate to durable run IDs. Expand event detail for the saved decision or outcome.</p><div class="scroll"><table><thead><tr><th>ID</th><th>Run ID</th><th>Event</th><th>Evidence</th></tr></thead><tbody>{"".join(audit)}</tbody></table></div></section>
<footer>Reference implementation. Synthetic data only. <a href="results.json">Download JSON evidence</a>. Hosted CI and production readiness require separate verification.</footer></body></html>"""
    (output / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "report.html").write_text(page, encoding="utf-8")
