# AGENTS.md

Local rules for the GEO tracking infrastructure package. Extends the root
`AGENTS.md`.

## Local Context

- This package owns runtime adapters for GEO tracking, including dummy and Vertex AI providers.
- Keep external SDK calls, runtime settings, clocks, and ID generation here.
- Validate through request-level API tests unless an adapter-specific test is needed.

## Boundaries

- Do not import FastAPI routes or app internals.
- Do not print, log, or commit Vertex AI credentials.
