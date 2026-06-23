# AGENTS.md

Local rules for the GEO tracking FastAPI application. Extends the root
`AGENTS.md`.

## Local Context

- This app exposes Query Research and run request MVP endpoints for GEO tracking.
- Current MVP uses dummy data and in-memory request handling; no persistence schema is owned here yet.
- Validate with `uv run --package younilab-geo-tracking-api pytest apps/geo-tracking-api/tests`.

## Boundaries

- Keep routes thin and map requests to application use cases.
- Do not persist secrets or print Vertex AI credentials.
