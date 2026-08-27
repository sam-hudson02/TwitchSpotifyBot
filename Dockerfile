FROM python:3.14-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Node.js is only needed at build time, to run the Prisma CLI (`generate`)
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /Sbotify

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY prisma prisma
COPY src src
RUN uv run prisma generate


FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PATH="/Sbotify/.venv/bin:$PATH"

# libatomic1 is needed by the Prisma query engine on some architectures
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /Sbotify

# the venv (with the generated Prisma client) and the query engine binary; no
# Node.js, migrations are applied at runtime by src/migrate.py
COPY --from=builder /Sbotify/.venv /Sbotify/.venv
COPY --from=builder /root/.cache/prisma-python /root/.cache/prisma-python
COPY src src
COPY prisma prisma
COPY entrypoint.sh /entrypoint.sh

RUN mkdir -p data secret && chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
