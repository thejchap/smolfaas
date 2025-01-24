# Use a Python image with uv pre-installed
# https://github.com/astral-sh/uv-docker-example/blob/main/Dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Needed for scikit build core
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake
    # cmake \
    # git \
    # wget g++ clang clang-format lld llvm ninja-build pkg-config

# V8
# https://v8.dev/docs/source-code
# install version
# ENV V8_VERSION=12.7.224.16
# RUN git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
# ENV PATH=$PATH:/app/depot_tools
# RUN mkdir ~/v8
# RUN cd ~/v8
# RUN fetch v8
# WORKDIR /app/v8
# RUN git checkout tags/${V8_VERSION}
# RUN gclient sync
# RUN tools/dev/gm.py arm64.release


# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run the FastAPI application by default
# Uses `fastapi dev` to enable hot-reloading when the `watch` sync occurs
# Uses `--host 0.0.0.0` to allow access from outside the container
# CMD ["fastapi", "run", "--host", "0.0.0.0", "src/server"]
CMD ["sleep", "infinity"]
