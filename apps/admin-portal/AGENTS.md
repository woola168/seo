# AGENTS.md

Local rules for the SEO access control POC portal. Extends the root `AGENTS.md`.

## Local Context

- This Vue 3 application demonstrates login, capabilities, users, roles, and
  authorization evaluation against `access-control-api`.
- It is a POC for product review and integration testing, not the final SEO
  administration experience.
- Validate with `npm run test --workspace @younilab/admin-portal` and
  `npm run build --workspace @younilab/admin-portal`.

## Boundaries

- Use Vue Composition API with `<script setup lang="ts">`.
- Keep HTTP details in `src/services`, not view components.
- Treat frontend permission checks as presentation only; the API remains the
  authorization authority.
