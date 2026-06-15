# AGENTS.md

Local rules for the resource catalog application package. Extends the root
`AGENTS.md`.

## Local Context

- This package orchestrates customer and SEO task CRUD.
- It depends only on the resource catalog domain.
- Validate with `uv run --package younilab-resource-catalog-application pytest packages/resource-catalog-application/tests`.

## Boundaries

- Define repository, clock, ID, and authorization ports here.
- Do not depend on FastAPI, SQLModel, HTTP clients, or concrete persistence.
