FROM python:3.13-slim

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY apps ./apps
COPY packages ./packages

RUN uv sync --frozen --no-dev --package younilab-access-control-api

EXPOSE 8000

CMD ["uvicorn", "younilab_access_control_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
