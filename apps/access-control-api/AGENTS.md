# AGENTS.md

Local rules for the SEO access control FastAPI application. Extends the root
`AGENTS.md`.

## Local Context

- This app exposes authentication, account administration, role management,
  resource grants, and authorization decision HTTP APIs.
- Keep route handlers thin. Authorization and account rules belong in the
  application and domain packages.
- Depend only on intentional package APIs. Do not import package internals.
- Validate with `uv run --package younilab-access-control-api pytest apps/access-control-api/tests`.

## Boundaries

- Presentation maps HTTP requests and RFC 7807 errors.
- Runtime composition selects infrastructure adapters.
- Do not place persistence models, password hashing, token signing, or domain
  rules in this app.
