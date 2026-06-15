# AGENTS.md

Local rules for the Resource Catalog FastAPI application. Extends the root
`AGENTS.md`.

## Local Context

- This app exposes customer and SEO task master-data APIs.
- Keep routes thin and authorize every endpoint through the application port.
- Validate with `uv run --package younilab-resource-catalog-api pytest apps/resource-catalog-api/tests`.

## Boundaries

- Depend only on intentional resource catalog package APIs.
- Do not import Access Control app internals or its persistence models.
