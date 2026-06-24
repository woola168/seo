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
