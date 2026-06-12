# AGENTS.md

Local rules for the access control infrastructure package. Extends the root
`AGENTS.md`.

## Local Context

- This package implements PostgreSQL persistence, password hashing, JWT, and
  notification adapters for the access control application ports.
- It must not contain FastAPI routes or product authorization rules.
- Validate with `uv run --package younilab-access-control-infrastructure pytest packages/access-control-infrastructure/tests`.

## Boundaries

- Map storage records to domain models explicitly.
- Keep secrets environment-based and never log credentials or tokens.
- Adapter tests may use SQLite; PostgreSQL-specific behavior requires focused
  integration tests.

## Structure

- Keep PostgreSQL adapters in `persistence/postgres/` and in-memory adapters in
  `persistence/memory.py`.
- Keep password and token implementations separated under `security/`.
