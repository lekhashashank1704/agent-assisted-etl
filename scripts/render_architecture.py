"""Render the reference architecture as matching editable SVG and high-resolution PNG.

Optional dependency: python -m pip install -e ".[diagrams]"
Run from any directory: python scripts/render_architecture.py
"""

from __future__ import annotations

import argparse
import html
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 2800, 2340
NAVY, INK, MUTED, BORDER = "#142D48", "#18324C", "#536A82", "#D8E2ED"
COLORS = {
    "blue": ("#EAF3FF", "#2764C3"),
    "purple": ("#F1ECFF", "#7553BC"),
    "teal": ("#E7F6F2", "#087F73"),
    "amber": ("#FFF4DC", "#AC6B0A"),
    "coral": ("#FFF0ED", "#C25246"),
    "cyan": ("#E8F7FC", "#16799A"),
    "slate": ("#EEF2F7", "#51647C"),
}


class Canvas:
    def __init__(self) -> None:
        self.image = Image.new("RGB", (WIDTH, HEIGHT), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">Agent-Assisted ETL: governed schema reasoning and deterministic execution</title>',
            '<desc id="desc">Four planes: schema planning and approval; deterministic inspection, transformation, quality checks, loading and recovery; one local SQLite database; explicitly proposed enterprise extensions. Only column metadata reaches the AI planner. Current evidence: 77 tests and 11 scripted scenarios. Live API validation pending.</desc>',
            '<rect width="100%" height="100%" fill="white"/>',
        ]
        self.fonts: dict[tuple[int, bool], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}

    def font(self, size: int, bold: bool = False):
        key = (size, bold)
        if key not in self.fonts:
            candidates = [
                "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
                "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
            ]
            for candidate in candidates:
                try:
                    self.fonts[key] = ImageFont.truetype(candidate, size)
                    break
                except OSError:
                    continue
            else:
                self.fonts[key] = ImageFont.load_default(size=size)
        return self.fonts[key]

    def text(self, x, y, value, size=24, color=INK, bold=False):
        self.draw.text((x, y), value, font=self.font(size, bold), fill=color, anchor="ls")
        weight = 700 if bold else 400
        self.parts.append(
            f'<text x="{x}" y="{y}" fill="{color}" font-family="Segoe UI,DejaVu Sans,Arial,sans-serif" font-size="{size}" font-weight="{weight}">{html.escape(value)}</text>'
        )

    def rect(self, x, y, w, h, fill, outline=None, radius=0, stroke=2, dashed=False):
        self.draw.rounded_rectangle(
            (x, y, x + w, y + h),
            radius,
            fill=fill,
            outline=None if dashed else outline,
            width=stroke,
        )
        if dashed and outline:
            points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
            self.line(points, outline, stroke, dashed=True, svg=False)
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{outline or "none"}" stroke-width="{stroke}"'
            + (' stroke-dasharray="11 8"' if dashed else "")
            + "/>"
        )

    def line(self, points, color=INK, width=3, dashed=False, arrow=False, svg=True):
        if dashed:
            for a, b in zip(points, points[1:], strict=False):
                distance = math.dist(a, b)
                for start in range(0, math.ceil(distance), 20):
                    end = min(start + 11, distance)
                    if distance:
                        self.draw.line(
                            [
                                (
                                    a[0] + (b[0] - a[0]) * start / distance,
                                    a[1] + (b[1] - a[1]) * start / distance,
                                ),
                                (
                                    a[0] + (b[0] - a[0]) * end / distance,
                                    a[1] + (b[1] - a[1]) * end / distance,
                                ),
                            ],
                            fill=color,
                            width=width,
                        )
        else:
            self.draw.line(points, fill=color, width=width, joint="curve")
        if svg:
            coords = " ".join(f"{x},{y}" for x, y in points)
            dash = ' stroke-dasharray="11 9"' if dashed else ""
            self.parts.append(
                f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"{dash}/>'
            )
        if arrow:
            x, y = points[-1]
            px, py = points[-2]
            angle = math.atan2(y - py, x - px)
            triangle = [
                (x, y),
                (
                    x - 15 * math.cos(angle) + 7 * math.sin(angle),
                    y - 15 * math.sin(angle) - 7 * math.cos(angle),
                ),
                (
                    x - 15 * math.cos(angle) - 7 * math.sin(angle),
                    y - 15 * math.sin(angle) + 7 * math.cos(angle),
                ),
            ]
            self.draw.polygon(triangle, fill=color)
            if svg:
                self.parts.append(
                    '<polygon points="'
                    + " ".join(f"{a:.1f},{b:.1f}" for a, b in triangle)
                    + f'" fill="{color}"/>'
                )

    def label(self, x, y, value, color=INK, size=22):
        width = self.draw.textlength(value, font=self.font(size, True))
        self.rect(x - 8, y - size - 4, width + 16, size + 13, "white", radius=3)
        self.text(x, y, value, size, color, True)

    def card(self, x, y, w, h, eyebrow, title, lines, tone="teal", proposed=False):
        fill, accent = COLORS[tone]
        self.rect(x + 2, y + 5, w, h, "#EDF1F6", radius=14)
        self.rect(x, y, w, h, fill, accent, radius=14, stroke=2, dashed=proposed)
        if not proposed:
            self.rect(x + 18, y + 19, 5, h - 38, accent, radius=2)
        self.text(x + 38, y + 36, eyebrow, 19, accent, True)
        title_size = 29
        while self.draw.textlength(title, font=self.font(title_size, True)) > w - 70:
            title_size -= 1
        if title_size < 24:
            raise ValueError(f"Title too long: {title}")
        self.text(x + 38, y + 80, title, title_size, INK, True)
        for index, value in enumerate(lines):
            size = 24
            while self.draw.textlength(value, font=self.font(size)) > w - 76:
                size -= 1
            if size < 21:
                raise ValueError(f"Body line too long: {value}")
            baseline = y + 126 + index * 36
            if baseline > y + h - 18:
                raise ValueError(f"Card overflows: {title}")
            self.text(x + 38, baseline, value, size, MUTED)

    def section(self, y, number, title, summary):
        self.line([(60, y - 35), (2740, y - 35)], BORDER, 2)
        self.text(60, y, number, 28, "#117F85", True)
        self.text(115, y, title, 29, INK, True)
        self.text(60, y + 43, summary, 24, MUTED)

    def save(self, output):
        output.mkdir(parents=True, exist_ok=True)
        (output / "architecture.svg").write_text(
            "\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8"
        )
        self.image.save(output / "architecture.png", optimize=True)


def render(output: Path) -> None:
    c = Canvas()
    c.rect(0, 0, WIDTH, 240, NAVY)
    c.rect(60, 44, 8, 62, "#50D5C0", radius=4)
    c.text(88, 91, "AGENT-ASSISTED ETL", 55, "#FFFFFF", True)
    c.text(
        60,
        140,
        "Enterprise reference architecture | Governed schema decisions + deterministic execution",
        30,
        "#D7E8F5",
    )
    c.rect(60, 166, 290, 35, "#1F5362", radius=17)
    c.text(77, 191, "SOLID = IMPLEMENTED", 19, "#C0F5E9", True)
    c.rect(375, 166, 390, 35, "#3D4660", radius=17)
    c.text(393, 191, "DASHED BOX = PROPOSED", 19, "#E6E7F2", True)
    c.text(
        805,
        191,
        "AI proposes. Operators approve. Deterministic code executes.",
        23,
        "#FFFFFF",
        True,
    )
    c.text(
        60,
        225,
        "OpenAI adapter implemented; live API validation pending. The lab explicitly selects a scripted demo planner.",
        22,
        "#BFD1E0",
    )

    c.section(
        288,
        "01",
        "DECISION & CONTROL PLANE",
        "The schema-planning agent is a bounded reasoning component: it proposes mappings and has no warehouse write authority.",
    )
    c.card(
        80,
        410,
        420,
        270,
        "HUMAN CONTROL",
        "Operator / CLI",
        [
            "Run, review, approve, resume",
            "Review column semantics",
            "Approve one exact proposal",
            "Operator label is attribution",
        ],
        "blue",
    )
    c.card(
        600,
        410,
        570,
        270,
        "AI REASONING / METADATA ONLY",
        "Schema-planning agent",
        [
            "OpenAI Responses API adapter",
            "Column names + contract only",
            "Structured mapping; no source rows",
            "Demo mode: explicit fixture",
        ],
        "purple",
    )
    c.card(
        1270,
        410,
        570,
        270,
        "LOCAL POLICY ENFORCEMENT",
        "Proposal validation",
        [
            "Complete one-to-one mapping",
            "Preserve known fields and aliases",
            "Reject collisions or invented fields",
            "Invalid / refused / failed -> block",
        ],
        "teal",
    )
    c.card(
        1940,
        410,
        780,
        270,
        "PAUSE / REVIEW / SEPARATE RESUME",
        "Approval & resume gate",
        [
            "Save proposal; end run as awaiting_approval",
            "Bind input hash, contract, proposal and options",
            "Resume re-inspects input and verifies approval",
            "Reject modified, stale or consumed approval",
        ],
        "amber",
    )
    c.line([(500, 540), (550, 540), (550, 372), (2330, 372), (2330, 410)], "#167EA3", 3, arrow=True)
    c.label(930, 359, "Operator reviews and approves the saved proposal", COLORS["blue"][1])
    c.line([(1170, 545), (1270, 545)], COLORS["purple"][1], 4, arrow=True)
    c.label(1188, 527, "JSON", COLORS["purple"][1], 20)
    c.line([(1840, 545), (1940, 545)], COLORS["teal"][1], 4, arrow=True)

    c.section(
        770,
        "02",
        "DETERMINISTIC DATA PLANE",
        "One Python process. Fixed transformations and SQL. No model-generated code executes.",
    )
    c.card(
        80,
        900,
        420,
        260,
        "SOURCE CONTRACT",
        "CSV source",
        [
            "Synthetic orders; UTF-8",
            "Defaults: 10 MiB / 100k rows",
            "Required five-field contract",
            "Bounded local byte snapshot",
        ],
        "blue",
    )
    c.card(
        600,
        900,
        570,
        260,
        "SOURCE INSPECTION",
        "Inspect & resolve schema",
        [
            "Read CSV shape and headers",
            "Create run ID and input SHA-256",
            "Built-in customer alias: cust_id",
            "Unknown schema -> request proposal",
        ],
        "blue",
    )
    c.card(
        1270,
        900,
        570,
        260,
        "BUSINESS RULES IN CODE",
        "Transform & quality gate",
        [
            "Fixed ID, status and null rules",
            "Explicit zones -> UTC; integer cents",
            "Known or approved mappings only",
            "Eligible batches load valid rows",
        ],
        "teal",
    )
    c.card(
        1940,
        900,
        780,
        260,
        "ATOMIC ORDER-LOAD TRANSACTION",
        "Transactional loader",
        [
            "BEGIN IMMEDIATE; recheck approval under lock",
            "Commit orders + approval use + success events",
            "Skip identical orders; conflicting facts block",
            "Any failure rolls back the entire order load",
        ],
        "teal",
    )
    c.line([(500, 1030), (600, 1030)], COLORS["blue"][1], 4, arrow=True)
    c.line([(1170, 1030), (1270, 1030)], COLORS["blue"][1], 4, arrow=True)
    c.label(1180, 1007, "Known", COLORS["blue"][1], 20)
    c.line([(1840, 1030), (1940, 1030)], COLORS["teal"][1], 4, arrow=True)
    c.label(1850, 997, "Valid rows", COLORS["teal"][1], 18)
    c.line(
        [(885, 900), (885, 866), (1230, 866), (1230, 710), (885, 710), (885, 680)],
        COLORS["purple"][1],
        3,
        arrow=True,
    )
    c.label(918, 854, "Unknown schema", COLORS["purple"][1])
    c.line([(2330, 680), (2330, 846), (1555, 846), (1555, 900)], COLORS["amber"][1], 4, arrow=True)
    c.label(1660, 831, "Approved resume: exact input and options", COLORS["amber"][1])

    c.card(
        600,
        1280,
        570,
        260,
        "REJECTED RECORDS / FAIL CLOSED",
        "Quarantine & block",
        [
            ">20% invalid or empty: reject batch",
            "Otherwise retain invalid rows only",
            "Keep record numbers and reasons",
            "Whole rejection: no load / approval use",
        ],
        "coral",
    )
    c.card(
        1270,
        1280,
        570,
        260,
        "CONTROLLED RECOVERY",
        "Rollback & explicit rerun",
        [
            "Orders and approval use roll back",
            "Validation evidence remains durable",
            "Resolve cause, then start a new run",
            "No automatic business-rule relaxation",
        ],
        "amber",
    )
    c.card(
        1940,
        1280,
        780,
        260,
        "READ / REPORT / EXPLICIT QUERY",
        "Analytics & evidence",
        [
            "Static SQL aggregates on committed orders",
            "HTML / JSON reports from the scripted lab",
            "Correlated run, approval and outcome events",
            "Order-level idempotency; attempts remain visible",
        ],
        "cyan",
    )
    c.line(
        [(1555, 1160), (1555, 1220), (885, 1220), (885, 1280)], COLORS["coral"][1], 4, arrow=True
    )
    c.label(1000, 1205, "Invalid-row policy", COLORS["coral"][1])
    c.line(
        [(2100, 1160), (2100, 1236), (1555, 1236), (1555, 1280)], COLORS["amber"][1], 4, arrow=True
    )
    c.label(1665, 1221, "Load failure", COLORS["amber"][1])
    c.line([(2510, 1160), (2510, 1280)], COLORS["cyan"][1], 4, arrow=True)
    c.label(2530, 1201, "Separate", COLORS["cyan"][1], 20)
    c.label(2530, 1230, "query", COLORS["cyan"][1], 20)
    c.line(
        [(1555, 1540), (1555, 1562), (550, 1562), (550, 980), (600, 980)],
        "#768AA2",
        3,
        dashed=True,
        arrow=True,
    )
    c.text(80, 1360, "Recovery starts", 23, COLORS["amber"][1], True)
    c.text(80, 1395, "a fresh validated run", 23, COLORS["amber"][1], True)
    c.text(80, 1460, "API adapter limits", 22, INK, True)
    c.text(80, 1495, "20s request timeout", 22, MUTED)
    c.text(80, 1530, "2 retries / 3 attempts maximum", 22, MUTED)

    c.section(
        1635,
        "03",
        "PERSISTENCE & TRACEABILITY",
        "One SQLite database holds all logical tables. Local audit records are persistent, but are not immutable or authenticated.",
    )
    c.rect(80, 1720, 2640, 155, "#EEF4FC", COLORS["blue"][1], radius=14)
    c.text(112, 1764, "LOCAL SQLITE STORE", 28, INK, True)
    c.text(
        112,
        1806,
        "orders: canonical facts   |   runs: hashes + outcomes   |   proposals: mappings + approvals   |   quarantine: rejected rows   |   audit: decision trail",
        25,
        MUTED,
    )
    c.text(
        112,
        1848,
        "Quality / quarantine evidence persists before loading. Order writes, approval consumption and success evidence commit atomically.",
        23,
        COLORS["blue"][1],
    )
    c.text(
        80,
        1915,
        "CODE ANCHORS  pipeline.py  /  planner.py  /  contract.py  /  storage.py  /  cli.py  /  lab/run_lab.py",
        23,
        MUTED,
    )

    c.section(
        1995,
        "04",
        "PROPOSED ENTERPRISE EXTENSIONS",
        "Future hardening capabilities below are not implemented or validated by the current reference project.",
    )
    c.card(
        80,
        2080,
        826,
        185,
        "PROPOSED / NOT IMPLEMENTED",
        "Identity & governance",
        ["SSO / RBAC; authenticated reviewers", "Secrets manager; independent approval roles"],
        "slate",
        True,
    )
    c.card(
        990,
        2080,
        826,
        185,
        "PROPOSED / NOT IMPLEMENTED",
        "Durable execution & scale",
        ["Scheduler / queue; streaming connectors", "Distributed warehouse; replay coordination"],
        "slate",
        True,
    )
    c.card(
        1900,
        2080,
        820,
        185,
        "PROPOSED / NOT IMPLEMENTED",
        "Operations & assurance",
        [
            "External immutable audit; alerting and tracing",
            "Signed image provenance; staged rollout",
        ],
        "slate",
        True,
    )
    c.text(
        60,
        2315,
        "VERIFIED REFERENCE SCOPE   77 tests  /  11 scripted scenarios  /  mocked provider verification  /  live API validation pending",
        24,
        INK,
        True,
    )
    c.save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).resolve().parents[1] / "docs" / "assets"
    )
    args = parser.parse_args()
    render(args.output)
    print(f"Created {args.output / 'architecture.svg'} and {args.output / 'architecture.png'}")


if __name__ == "__main__":
    main()
