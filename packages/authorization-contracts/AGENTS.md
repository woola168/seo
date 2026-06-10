# AGENTS.md

Local rules for shared authorization contracts. Extends the root `AGENTS.md`.

## Local Context

- This package exposes stable authorization request and response schemas for
  the access control API and future SEO APIs.
- Keep dependencies minimal and avoid domain, persistence, or FastAPI imports.
- Validate with `uv run --package younilab-authorization-contracts pytest packages/authorization-contracts/tests`.
