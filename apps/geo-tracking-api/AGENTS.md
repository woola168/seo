# AGENTS.md

Local rules for the GEO Tracking FastAPI application. Extends the root
`AGENTS.md`.

## Local Context

- This app exposes GEO tracking execution and provider-facing APIs.
- Routes should stay thin and delegate behavior to application use cases as
  tracking behavior is added.
- Validate with `uv run --package younilab-geo-tracking-api pytest apps/geo-tracking-api/tests`.

## Boundaries

- Do not store GEO Analysis setup or report state in this app.
- Do not import other app internals. Shared behavior belongs in `packages/`.
- Keep provider integration, queue consumption, and persistence behind
  application or infrastructure ports when they are introduced.
