# AGENTS.md

Local rules for the access control domain package. Extends the root `AGENTS.md`.

## Local Context

- This package owns account, role, permission, customer access, task access,
  and authorization policy behavior.
- It must remain independent from FastAPI, databases, JWT libraries, password
  libraries, and infrastructure SDKs.
- Validate with `uv run --package younilab-access-control-domain pytest packages/access-control-domain/tests`.

## Boundaries

- Model invariants and authorization decisions with plain Python.
- Do not add DTOs, repositories, HTTP errors, SQL models, or configuration.

## Structure

- Keep account models in `accounts.py`, role models in `roles.py`, and protected
  resource models in `resources.py`.
- Add deeper DDD directories only when multiple real aggregate, entity, value
  object, or event implementations require them.
