# AGENTS.md

Local rules for the GEO Analysis scheduler. Extends the root `AGENTS.md`.

## Local Context

- This app materializes fixed-time daily GEO jobs and dispatches due work.
- Validate with `uv run --package younilab-geo-analysis-scheduler pytest apps/geo-analysis-scheduler/tests`.

## Boundaries

- Keep scheduling policy in GEO Analysis application use cases.
- Keep PostgreSQL and RabbitMQ details in package infrastructure adapters.
- Do not call AI providers or import another app's internals.
- Build runtime dependencies in `composition.py`; keep polling in `scheduler.py`.
