# AGENTS.md

Local rules for the GEO tracking domain package. Extends the root `AGENTS.md`.

## Local Context

- This package owns GEO query, topic, market, provider, and run result domain concepts.
- It must remain independent from HTTP, databases, SDKs, queues, and provider details.
- Validate with `uv run --package younilab-geo-tracking-domain pytest packages/geo-tracking-domain/tests`.

## Boundaries

- Keep query and run invariants in plain Python domain models.
- Do not add DTOs, repositories, SQL models, FastAPI, or Vertex AI dependencies here.
