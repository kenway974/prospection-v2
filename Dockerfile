FROM python:3.13-slim
RUN pip install --no-cache-dir uv==0.11.32
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-editable
COPY alembic.ini ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable && useradd --create-home app
USER app
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/sante')"
CMD python -m prospection.cli migrate && exec uvicorn prospection.ui.main:app --host 0.0.0.0 \
    --port ${PORT:-8000}
