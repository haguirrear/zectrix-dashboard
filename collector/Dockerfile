# The collector as a run-once container, for the VPS (server/larapaper/compose.prod.yml, service
# "collector"). It collects, POSTs to LaraPaper and exits; a systemd timer starts it
# (host/vps/). Your PC runs the collector with uv directly and doesn't use this image.
FROM python:3.12-slim

# tzdata: the TZ setting (zoneinfo) needs the time zone database.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PYTHONUNBUFFERED=1

WORKDIR /app
# Dependencies first (cached layer), exactly as pinned in uv.lock.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

# Unprivileged; nothing is written to disk.
USER 65534:65534
ENTRYPOINT ["/opt/venv/bin/zectrix-collect"]
CMD ["--only", "weather,github"]
