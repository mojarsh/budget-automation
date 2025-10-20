# --- STAGE 1: Build Stage (Optimized and Finalized) ---
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

# 1. OPTIMIZATION: Install build tools first for caching.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libatlas-base-dev \
    libopenblas-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Copy all files needed for the install process.
COPY pyproject.toml .
COPY uv.lock .
COPY README.md .
COPY src/ src/

# 3. Create Venv and Install Project
# Use 'uv venv && uv pip install .' combined into a single RUN command 
# for atomic execution, ensuring the venv exists before install.
# If 'uv' is not on the global path, we run it directly from the venv.

# Using a shell to ensure both commands execute cleanly:
RUN /bin/bash -c "uv venv && \
    source .venv/bin/activate && \
    uv pip install ."
# --- STAGE 2: Production Stage (Remains the same) ---
FROM python:3.14-slim AS production

WORKDIR /app

# Copy the application source code (Needed for runtime)
COPY src/ src/
COPY pyproject.toml .
COPY logging_config.json .

# Copy the virtual environment from the build stage
COPY --from=builder /app/.venv /app/.venv

# Ensure the virtual environment's bin directory is on the PATH
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "src/main.py"]
