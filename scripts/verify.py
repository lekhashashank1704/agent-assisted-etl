"""Run local quality gates and preserve a machine-readable command outcome record."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build",
        action="store_true",
        help="Also build sdist/wheel with installed build dependencies",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / "output" / "verification"
    output.mkdir(parents=True, exist_ok=True)
    commands = [
        ["-m", "ruff", "check", "."],
        ["-m", "ruff", "format", "--check", "."],
        ["-m", "mypy"],
        [
            "-m",
            "pytest",
            "--cov",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--junitxml=reports/junit.xml",
        ],
        ["-m", "bandit", "-c", "pyproject.toml", "-r", "src/etl_agents"],
        ["-m", "pip", "check"],
        ["lab/run_lab.py"],
    ]
    if args.build:
        commands.append(["-m", "build", "--no-isolation"])
    results = []
    for index, command in enumerate(commands, 1):
        result = subprocess.run(
            [sys.executable, *command], cwd=root, capture_output=True, text=True, timeout=300
        )
        log = output / f"{index:02d}.log"
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
        results.append(
            {"command": ["python", *command], "exit_code": result.returncode, "log": log.name}
        )
        print(json.dumps(results[-1]), flush=True)
    summary = {
        "python": platform.python_version(),
        "platform": platform.system(),
        "checks": results,
        "live_api": "not run",
        "docker": "not run",
        "hosted_ci": "not run",
    }
    (output / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return int(any(result["exit_code"] for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
