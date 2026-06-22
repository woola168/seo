# AGENTS.md

Local rules for GEO analysis infrastructure. Extends the root `AGENTS.md`.

## Local Context

- This package implements GEO analysis infrastructure adapters.
- Phase 1 includes PostgreSQL row models and persistence mapping structure.
- Concrete message broker publishers are intentionally deferred until the queue
  backend is selected.
- Validate with `uv run --package younilab-geo-analysis-infrastructure pytest packages/geo-analysis-infrastructure/tests`.

## Boundaries

- Depend on GEO application ports and domain models, not app internals.
- Keep PostgreSQL, SQLModel, and future SDK-specific details out of domain and
  application packages.
- Do not implement actual AI runner behavior or parse AI response content here.
