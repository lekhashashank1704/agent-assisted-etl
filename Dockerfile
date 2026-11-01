FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.11-slim AS runtime
LABEL org.opencontainers.image.title="Agent-Assisted ETL" \
      org.opencontainers.image.description="Governed schema planning with deterministic execution" \
      org.opencontainers.image.source="https://github.com/lekhashashank1704/agent-assisted-etl" \
      org.opencontainers.image.licenses="MIT"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels etl-agents \
    && rm -rf /wheels \
    && groupadd --gid 10001 etl \
    && useradd --uid 10001 --gid etl --no-create-home etl \
    && mkdir /app/output \
    && chown etl:etl /app/output
COPY --chown=etl:etl data ./data
COPY --chown=etl:etl lab ./lab
USER 10001:10001
CMD ["python", "lab/run_lab.py"]
