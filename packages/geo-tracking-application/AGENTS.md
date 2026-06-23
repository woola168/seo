# AGENTS.md

Local rules for the GEO tracking application package. Extends the root `AGENTS.md`.

## Local Context

- This package orchestrates Query Research and run request use cases.
- Keep provider calls behind application interfaces.
- Validate with `uv run --package younilab-geo-tracking-application pytest packages/geo-tracking-application/tests`.

## Boundaries

- Depend only on the GEO tracking domain package and explicit provider interfaces.
- Do not import FastAPI, Vertex AI SDKs, persistence models, or app internals.
