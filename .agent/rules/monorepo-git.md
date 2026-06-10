# Monorepo, Git, and Commit Workflow Rules

This rule enforces directory boundaries, monorepo dependency conventions, Git branch naming, and pull request workflows for development.

## Monorepo Layout & Responsibility

The repository serves as the single source-of-truth for product code, shared contracts, documentation, and deployment configurations.

- **`apps/`**: Contains deployable or runnable applications (e.g., web apps, APIs, workers, CLIs, and jobs).
- **`packages/`**: Contains reusable libraries, domain modules, shared contracts, and independently testable capabilities.
- **`tests/`**: Contains cross-app, cross-package, integration, contract, and end-to-end tests. Local unit tests live near the code they validate.
- **`deploy/`**: Contains deployment and runtime composition files. Do not store secrets here.
- **`tools/`**: Contains repository automation scripts. Do not place business logic here.
- **`docs/architecture/`**: Contains architecture decisions, system design notes, and structure guidance.
- **`docs/architecture/agent-templates/`**: Contains local `AGENTS.md` templates for new apps and packages.

## Monorepo Dependency Rules

- **Cohesive Changes**: A change that touches shared contracts must update affected apps, packages, tests, and documentation in the same commit or pull request.
- **No Cross-App Imports**: Avoid direct imports across apps. Share code exclusively through packages or explicit service contracts.
- **Intentional Public APIs**: Packages must expose intentional public APIs. Apps should not depend on package internals.
- **Acyclic Dependency Flow**: Keep dependency direction explicit and acyclic.

## Git & Commit Guidelines

- **Branch Naming**: Use branch names in `type/description` or `type/issue-id-description` format.
  - Allowed prefixes: `feat/`, `fix/`, `refactor/`, `docs/`, `test/`, `chore/`.
- **Commit Messages**: 
  - Write commit messages in **Traditional Chinese with Taiwan terminology** (繁體中文).
  - Use the **Conventional Commits** format: `type(scope): description`.
  - Example: `feat(core): 新增模型欄位擷取邏輯`
  - Keep each commit focused on one logical change.
- **No Emojis**: Do not use emojis in commit messages, pull request descriptions, or branch names.

## Pull Request Guidelines

- **Comprehensive Descriptions**: Pull request descriptions must include:
  1. Summary of changes.
  2. Motivation for changes.
  3. Validation details (tests run, build logs, etc.).
  4. Risk areas and rollback notes (when relevant).
- **Size Constraint**: Avoid large pull requests. Split by behavior, boundary, or reviewable responsibility.

## Code Review Guidelines

- **Prioritize Correctness**: Review behavior, correctness, and risk before style.
- **High-Risk Domains**: High-risk areas require careful review:
  - Authentication and Authorization
  - Payments
  - Database Migrations
  - Concurrency
  - Production Configurations and Secrets
  - Destructive Operations and External Integrations
- **Test Evidence**: Require clear test evidence for behavior changes. Ask for splitting large diffs before reviewing details.
