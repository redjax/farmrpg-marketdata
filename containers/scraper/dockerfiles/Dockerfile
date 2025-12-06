## Base layer
ARG UV_BASE=${UV_IMAGE_VER:-0.9.16}
ARG PYTHON_BASE=${PYTHON_IMG_VER:-3.14-slim}

FROM ghcr.io/astral-sh/uv:${UV_BASE} AS uv
FROM python:${PYTHON_BASE} AS base

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        gcc \
        iputils-ping \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

## Stage layer: Copy files into the container for more efficient caching
FROM base AS stage

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./

COPY src /app/src
COPY scripts /app/scripts

FROM base AS build

COPY --from=stage /app /app
COPY --from=uv /uv /usr/bin/uv

WORKDIR /app

RUN uv sync --all-extras \
    && uv build \
    && uv pip install -e .

FROM python:${PYTHON_BASE} AS runtime

COPY --from=build /app /app
COPY --from=uv /uv /usr/bin/uv

COPY --from=build /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

WORKDIR /app

CMD ["uv", "run", "scripts/market/scheduled_scrape.py"]
