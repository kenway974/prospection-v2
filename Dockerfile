FROM python:3.15-slim
# pg_dump et pg_restore pour la sauvegarde quotidienne (C91) ; un client récent lit aussi
# les serveurs plus anciens.
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.11.32
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-editable
# Chromium sans interface, pour lire les sites affichés par JavaScript (C166)
RUN playwright install --with-deps --only-shell chromium && rm -rf /var/lib/apt/lists/*
COPY alembic.ini ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable && useradd --create-home app
USER app
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/sante')"
CMD python -m prospection.cli migrate && exec uvicorn prospection.ui.main:app --host 0.0.0.0 \
    --port ${PORT:-8000}
