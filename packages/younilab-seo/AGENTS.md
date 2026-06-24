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

## Bounded Context Standard

- Use `younilab_seo.geo_analysis` as the current reference structure for new
  or refactored bounded contexts.
- Put application command/result models in `application/contracts.py`.
- Put repository, publisher, clock, id generator, and external service ports in
  `application/interfaces.py`.
- Put orchestration in `application/use_cases/`, split by workflow rather than
  by transport or infrastructure concern.
- Keep `application/use_cases/__init__.py` as the intentional public export for
  use cases.
- Infrastructure adapters must implement application ports and perform mapping
  between rows, SDK payloads, external messages, and application/domain models.
- API apps must depend on package public application exports, not package
  internals or infrastructure models.
