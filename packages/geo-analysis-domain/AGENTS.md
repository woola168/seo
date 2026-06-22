# AGENTS.md

Local rules for the GEO analysis domain package. Extends the root `AGENTS.md`.

## Local Context

- This package owns GEO analysis orchestration domain behavior.
- It models projects, tracked entities, queries, schedules, and job state.
- It does not own AI responses, mention extraction, citation extraction, sentiment
  analysis, or GEO metric calculations.
- Validate with `uv run --package younilab-geo-analysis-domain pytest packages/geo-analysis-domain/tests`.

## Boundaries

- Keep domain rules in plain Python models.
- Do not depend on FastAPI, SQLModel, databases, SDKs, queues, or other apps.
- Do not import Access Control or Resource Catalog internals.
