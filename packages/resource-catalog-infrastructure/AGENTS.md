# AGENTS.md

Local rules for resource catalog infrastructure. Extends the root `AGENTS.md`.

## Local Context

- This package implements resource catalog persistence, runtime, and the
  Access Control authorization client.
- Validate with `uv run --package younilab-resource-catalog-infrastructure pytest packages/resource-catalog-infrastructure/tests`.

## Boundaries

- Keep PostgreSQL and HTTP client details out of domain and application code.
- Map persistence records explicitly and fail closed when authorization fails.
