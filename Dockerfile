FROM python:3.14-alpine AS builder

ENV PIP_NO_CACHE_DIR=1 \
    CMAKE_POLICY_VERSION_MINIMUM=3.5

# Build dependencies for native extensions (matrix-nio[e2e], lxml, nh3, etc.).
# CMAKE_POLICY_VERSION_MINIMUM keeps python-olm build-compatible with CMake 4 on Alpine 3.23.
RUN apk add --no-cache \
    build-base \
    cargo \
    cmake \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    olm-dev \
    openssl-dev \
    uv \
    zlib-dev

WORKDIR /app

# Isolated virtualenv to copy into runtime stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies first (cached layer)
COPY pyproject.toml README.md LICENSE ./
RUN mkdir -p squidbot && touch squidbot/__init__.py && \
    uv pip install --python /opt/venv/bin/python --no-cache . && \
    rm -rf squidbot

# Copy source and install package
COPY squidbot/ squidbot/
# Dependencies are already installed in the previous layer; install local package only.
RUN uv pip install --python /opt/venv/bin/python --no-cache --no-deps .


FROM python:3.14-alpine

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Runtime libraries for compiled wheels/extensions
RUN apk add --no-cache \
    libffi \
    libstdc++ \
    libxml2 \
    libxslt \
    olm \
    openssl \
    zlib

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Create config directory
RUN mkdir -p /root/.squidbot

# Gateway default port
EXPOSE 18790

ENTRYPOINT ["squidbot"]
CMD ["status"]
