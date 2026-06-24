# AGENTS.md

Local rules for the SEO Python package. Extends the root `AGENTS.md`.

## Local Context

- This package owns SEO back-office Python bounded contexts.
- Keep Access Control, Resource Catalog, and GEO Analysis separated under their
  own namespace directories.
- Validate with `uv run --package younilab-seo pytest packages/younilab-seo/tests`.

## Boundaries

- Keep domain rules independent from FastAPI, databases, SDKs, queues, and
  infrastructure adapters.
- Put use case orchestration and ports in each bounded context application
  layer.
- Put persistence, security, runtime, queue, and external-system adapters in
  each bounded context infrastructure layer.
- Share only stable cross-context building blocks through `younilab_seo.shared`.
- Do not import API app modules from this package.

## Structure

- Use `younilab_seo.access_control` for authentication, accounts, roles,
  permissions, protected resources, and authorization contracts.
- Use `younilab_seo.resource_catalog` for customer and SEO task master data.
- Use `younilab_seo.geo_analysis` for GEO orchestration planning, dispatch, and
  job state.
- Add shared abstractions only when they remove real duplication across at
  least two bounded contexts.
