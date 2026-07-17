# AGENTS.md

Local rules for the provider request audit package. Extends the root
`AGENTS.md`.

## Local Context

- This package records one durable audit row for every outbound provider request.
- Keep contracts provider-neutral so AI and SERP adapters can share them.
- Validate with `uv run --package younilab-provider-request-audit pytest packages/provider-request-audit/tests`.

## Boundaries

- Do not depend on GEO application or provider SDK packages.
- Do not store prompts, responses, credentials, or full exception messages.
- A recorder start failure must prevent the provider request.
