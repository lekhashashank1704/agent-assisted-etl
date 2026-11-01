# Deployment guide

## Local execution

Python 3.11+ and a writable local directory are required. Install with `pip install .` for runtime use or `pip install -e ".[dev]"` for development. No external database service is required. Run `etl-agents --db output/warehouse.db run data/clean.csv` to initialize and load the synthetic fixture.

Resource defaults are 10 MiB, 100,000 records, 32 columns and 128 characters per header. The first two can be set with CLI flags; embedded applications can pass SourceLimits. All sources are UTF-8 (with optional BOM). The local file owner is the effective operator security principal.

## Container

```sh
docker build -t agent-assisted-etl:local .
docker run --rm agent-assisted-etl:local
```

The multi-stage image builds wheels, installs without a runtime package-index request and runs as UID/GID 10001. The default command executes the fixture lab and exits. It is a batch job, so no HTTP port or artificial network health endpoint is exposed.

To retain output, mount an existing writable directory at `/app/output` and give UID 10001 permission to write it. For example on a compatible host:

```sh
docker run --rm --mount type=bind,source="$(pwd)/output",target=/app/output agent-assisted-etl:local
```

Create the host output directory first. Mount ownership differs on Linux, macOS and Windows; verify it explicitly. For a custom operation, override the command with `etl-agents --db /app/output/warehouse.db run /app/data/clean.csv`.

## API configuration

Only `--planner live` permits a provider request. Set `OPENAI_API_KEY` in the execution environment using the deployment's secret mechanism. `OPENAI_MODEL` defaults to `gpt-4o-mini`. Env files are not loaded automatically. Never bake secrets into an image or build argument. Only schema names and contract metadata are sent. Source rows remain local.

The planner has a 20-second request timeout and at most two SDK retries for retryable failures. Model access and live structured-output behavior must be verified in the target account; a passing fixture lab is not live validation.

## Operational assumptions

Use a persistent local volume for warehouse/run state. Avoid shared network filesystems unless SQLite locking/durability has been validated for that filesystem. Schedule one writer per warehouse for predictable operations. Add external scheduling, authentication, alerting, backup retention and audit export before operating on real data. The current container definition is not proof of a successful image build; see VALIDATION.md.
