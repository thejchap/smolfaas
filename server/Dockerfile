# V8 builder image
# https://v8.dev/docs/build
# https://v8.dev/docs/source-code
# https://v8.dev/docs/release-process
FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS build
# it's the one available in homebrew
ENV V8_VERSION=12.7

# Install dependencies
RUN apt-get update && apt-get install -y \
    git curl python3 python3-pip python3-distutils \
    g++ clang cmake ninja-build build-essential \
    pkg-config && \
    # cleanup - reduce image size
    rm -rf /var/lib/apt/lists/*

# Install depot_tools for fetching V8 source
WORKDIR /depot_tools
RUN git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git . && \
    echo 'export PATH=$PWD:$PATH' >> /etc/profile && \
    echo 'export PATH=$PWD:$PATH' >> ~/.bashrc
ENV PATH="/depot_tools:$PATH"

# Fetch V8 source and sync dependencies
WORKDIR /v8
RUN fetch v8
WORKDIR /v8/v8
RUN git checkout branch-heads/${V8_VERSION}
RUN gclient sync -D

# Build V8
WORKDIR /v8/v8
RUN tools/dev/v8gen.py x64.release.sample -vvv
RUN ninja -C out.gn/x64.release.sample v8_monolith

# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS build-app

# Install dependencies for building app
RUN apt-get update && apt-get install -y \
    g++ clang cmake && \
    # cleanup - reduce image size
    rm -rf /var/lib/apt/lists/*

# Install the project into `/app`
WORKDIR /app

# copy the v8 files to link
COPY --from=build /v8/v8/out.gn/x64.release.sample/ /v8/out
COPY --from=build /v8/v8/include/ /v8/include


# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run the FastAPI application by default
# Uses `fastapi dev` to enable hot-reloading when the `watch` sync occurs
# Uses `--host 0.0.0.0` to allow access from outside the container
CMD ["fastapi", "run", "--host", "0.0.0.0", "src/server"]
