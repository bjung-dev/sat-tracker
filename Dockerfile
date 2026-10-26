# Recipe for building the sat-tracker container image.
# Build:  docker build -t sat-tracker:dev .
# Run:    docker run --rm -p 8000:8000 sat-tracker:dev

# ---------- Stage 1: "builder" installs the app and its libraries ----------
FROM python:3.12-slim AS builder

# Borrow the uv program from uv's official image (pinned to the version we use).
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv

# Precompile Python files for faster startup; copy (not link) files into the
# venv so it can be moved to the next stage; never download a different Python.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install the libraries FIRST, using only the dependency files. Docker caches
# each step, so as long as these two files don't change, rebuilding after a
# code edit skips this slow step entirely.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Now copy our own code and install it into the virtual environment.
COPY README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

# ---------- Stage 2: the small image we actually ship ----------
# Starts fresh, so build tools (uv, caches, source files) are left behind.
FROM python:3.12-slim

# Run as an ordinary user, not root: if someone ever broke into the app,
# they'd have far less power inside the container.
RUN useradd --create-home --uid 10001 app

WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# HOST=0.0.0.0 makes the server accept connections from outside the
# container (127.0.0.1 would only accept them from inside it).
ENV PATH="/app/.venv/bin:$PATH" \
    HOST=0.0.0.0 \
    PORT=8000 \
    PYTHONUNBUFFERED=1

USER 10001
EXPOSE 8000
CMD ["sat-tracker"]
