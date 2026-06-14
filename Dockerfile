FROM python:3.13-slim

LABEL org.opencontainers.image.title="LM Studio Watch Dog"
LABEL org.opencontainers.image.description="Local web UI and CLI for building LM Studio project context."
LABEL org.opencontainers.image.source="https://github.com/HBaz92/LM-Studio_Watch-Dog"
LABEL org.opencontainers.image.vendor="HBaz92"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

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
