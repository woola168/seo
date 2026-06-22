# AGENTS.md

Local rules for the GEO analysis application package. Extends the root
`AGENTS.md`.

## Local Context

- This package orchestrates GEO setup, query scheduling, job dispatch, and
  external runner callback handling.
- It defines application ports and stable contracts for message publishing and
  persistence.
- Validate with `uv run --package younilab-geo-analysis-application pytest packages/geo-analysis-application/tests`.

## Boundaries

- Depend only on `younilab-geo-analysis-domain`.
- Do not depend on FastAPI, SQLModel, concrete persistence, cloud SDKs, queue
  SDKs, or app internals.
- Keep publisher behavior behind protocol ports. Do not implement a concrete
  message broker adapter here.
