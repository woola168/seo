# AGENTS.md

Local rules for the resource catalog domain package. Extends the root
`AGENTS.md`.

## Local Context

- This package owns customer and SEO task master-data behavior.
- It must remain independent from HTTP, databases, and access-control details.
- Validate with `uv run --package younilab-resource-catalog-domain pytest packages/resource-catalog-domain/tests`.

## Boundaries

- Keep customer and task invariants in plain Python domain models.
- Do not add DTOs, repositories, SQL models, or framework dependencies.
