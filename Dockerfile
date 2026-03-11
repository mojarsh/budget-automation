# --- Build stage ---
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
COPY src/ src/

RUN uv sync --no-dev --frozen

# --- Production stage ---
FROM python:3.14-slim AS production

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY src/ src/
COPY logging_config.json .

# Ensure the virtual environment's bin directory is on the PATH
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "src/main.py"]
