FROM python:3.13-slim

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY apps ./apps
COPY packages ./packages

RUN uv sync --frozen --no-dev --package younilab-geo-analysis-worker

CMD ["python", "-m", "younilab_geo_analysis_worker.main"]
