# Verification evidence

Recorded 2026-11-01. Local environment: Windows, Python 3.14.8, application 0.2.0, OpenAI SDK 2.54.0, pytest 9.2.0. This record describes checks actually performed; it is not a production or compliance attestation.

| Gate | Observed result |
|---|---|
| Behavioral tests | **77 passed in 44.14 seconds**, no warnings |
| Application coverage | **98.62%**, with branch measurement; 85% threshold passed |
| Ruff lint | Passed |
| Ruff formatting | Passed |
| Mypy | Passed, 9 application modules checked |
| Bandit | No findings in application source |
| Dependency consistency | `pip check` passed |
| Advisory audit | **59 exact package versions scanned; no known vulnerabilities reported** |
| Scripted lab | **11 expected scenario outcomes passed** |
| Source and wheel build | Both distributions built successfully |
| Built wheel smoke | Isolated interpreter imported wheel code, loaded clean fixture and passed health check |
| HTML/JSON evidence | Tables, audit count and warehouse totals agree with SQLite |
| Verified backup | Preservation and refusal-to-overwrite behavior passed in tests |
| CLI | Direct JSON-interface and subprocess operational checks passed |

The advisory result is a point-in-time query of the versions in requirements/constraints.txt. It does not guarantee absence of vulnerabilities or cover newly resolved versions. Static analysis likewise does not prove security.

## Reproduction

```sh
python -m pip install -e ".[dev]"
python scripts/verify.py --build
python -m pip_audit -r requirements/constraints.txt --no-deps --disable-pip --strict --progress-spinner off
```

The verification runner saves command results and logs under output/verification/. The full lab saves output/lab/report.html and results.json. These generated outputs remain ignored by git. CI definitions independently cover the supported Python/platform matrix.

## Remaining validation boundaries

- Live OpenAI API: pending. No paid API calls were made; requests, refusals and retry behavior were mocked.
- Docker image: definition supplied; no local Docker build/run evidence.
- Hosted GitHub Actions: definitions supplied; successful hosted execution must be confirmed after upload.
- Python 3.11-3.13 and Linux: defined in CI; only Windows/Python 3.14.8 was exercised locally.
- Load, restore-time and availability objectives: not measured. No production deployment or measured business impact is claimed.
