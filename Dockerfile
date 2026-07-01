FROM python:3.13-slim

LABEL org.opencontainers.image.title="LM Studio Watch Dog"
LABEL org.opencontainers.image.description="Local web UI and CLI for building LM Studio project context."
LABEL org.opencontainers.image.source="https://github.com/HBaz92/LM-Studio_Watch-Dog"
LABEL org.opencontainers.image.vendor="HBaz92"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Node.js/npm are only needed so the optional GitNexus integration
# (use_gitnexus, invoked via `npx gitnexus ...`) works inside the container.
# The rest of the app runs fine without it if GitNexus is disabled.
#
# GitNexus is installed globally at build time rather than left for `npx` to
# fetch on first run. On npm 11.x, letting npx auto-install gitnexus on demand
# hits a known npm/arborist bug with platform-filtered optionalDependencies in
# native packages: the @ladybugdb/core native addon (lbugjs.node) ends up
# missing or broken, and every GitNexus command then fails at startup with
# "cannot open shared object file" / ERR_DLOPEN_FAILED. A global install
# avoids that code path entirely; `npx gitnexus ...` at runtime just uses the
# already-installed global binary. GITNEXUS_SKIP_OPTIONAL_GRAMMARS=1 skips
# building four rarely-needed Tree-sitter grammars (Dart/Proto/Swift/Kotlin)
# so the build doesn't also need a C++ toolchain (python3/make/g++) in the image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && GITNEXUS_SKIP_OPTIONAL_GRAMMARS=1 npm install -g gitnexus@latest \
    && apt-get purge -y curl gnupg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 appuser

# The bind-mounted project folder is typically owned by a different UID than
# appuser (it belongs to whatever user owns it on the host). Git 2.35+ refuses
# to run inside a repo it doesn't own ("detected dubious ownership") unless
# that path is explicitly marked safe. GitNexus shells out to git, so without
# this it would fail with an ownership error even with git installed.
RUN git config --system --add safe.directory '*'

COPY lm_studio_watchdog ./lm_studio_watchdog
COPY README.md pyproject.toml run.py ./

RUN mkdir -p /app/data /workspace \
    && chown -R appuser:appuser /app /workspace

USER appuser

EXPOSE 8765

VOLUME ["/app/data", "/workspace"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/state', timeout=3).read()"

CMD ["python", "-m", "lm_studio_watchdog", "serve", "--host", "0.0.0.0", "--port", "8765", "--no-browser"]