FROM python:3.14-slim

# unbuffered stdout/stderr so logs reach `docker logs` in real time
ENV PYTHONUNBUFFERED=1

# Bring in the uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Node.js is required by prisma-client-py to fetch/run the Prisma CLI
# (used by both `prisma generate` at build time and `prisma migrate deploy`
# at runtime).
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /Sbotify

# Install dependencies first (cached unless the lockfile changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# App source + Prisma schema/migrations
COPY src src
COPY prisma prisma

# Generate the Prisma client into the venv
RUN uv run prisma generate

RUN mkdir -p data secret

CMD ["sh", "-c", "uv run prisma migrate deploy && uv run python src/server.py"]
