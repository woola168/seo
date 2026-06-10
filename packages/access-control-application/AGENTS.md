# AGENTS.md

Local rules for the access control application package. Extends the root
`AGENTS.md`.

## Local Context

- This package owns authentication and authorization use case orchestration,
  repository ports, and stable application contracts.
- It may depend on the access control domain and authorization contracts.
- It must not depend on apps, SQLModel, database drivers, FastAPI, or concrete
  cryptography implementations.
- Validate with `uv run --package younilab-access-control-application pytest packages/access-control-application/tests`.

## Boundaries

- Use cases enforce authorization at the application boundary.
- External capabilities are protocols injected by runtime composition.
- Structured inputs and results use explicit typed models.
