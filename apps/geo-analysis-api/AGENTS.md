# AGENTS.md

Local rules for the GEO Analysis FastAPI application. Extends the root
`AGENTS.md`.

## Local Context

- This app exposes GEO setup CRUD, schedule/job orchestration, and external
  runner callback APIs.
- Routes should stay thin and delegate behavior to the application package.
- Validate with `uv run --package younilab-geo-analysis-api pytest apps/geo-analysis-api/tests`.

## Boundaries

- Depend only on intentional GEO package APIs.
- Do not import Access Control or Resource Catalog app internals.
- Do not implement AI runner calls, raw AI response storage, response parsing,
  or GEO metric calculations in this app.

## Reference Structure

- Treat this app as the service architecture standard for future API work.
- Keep HTTP routes under `presentation/http/`; routes should map DTOs, call
  application use cases, and map responses or Problem Details.
- Build runtime dependencies in `presentation/http/composition.py`; avoid
  constructing repositories, queues, SDK clients, or clocks in route modules.
- Store test-only in-memory fakes in the API app only when they support HTTP
  tests; production adapters belong in the package infrastructure layer.
